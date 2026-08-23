import datetime as dt
import pandas as pd
import yfinance as yf
import math
from blackscholes import BlackScholes
from implied_vol import implied_vol_newton
from market_data import get_risk_free_rate
import matplotlib.pyplot as plt



def get_expiries(ticker: str) -> list[str]:
    """
    Retrieve available option expiration dates for a ticker.
    Args:
        ticker (str): Underlying ticker symbol.

    Returns:
        list[str]: Available option expiration dates.
    """
    ticker = ticker.strip().upper()

    stock = yf.Ticker(ticker)

    expiries = list(stock.options)

    if not expiries:
        raise ValueError(f"No option expirations found for ticker: {ticker}")

    return expiries

def time_to_expiry(expiry: str) -> float:
    """
    Convert an expiration date into time to expiry in years.
    Args:
        expiry (str): Expiration date in YYYY-MM-DD format.

    Returns:
        float: Time to expiry in years.

    """
    expiry_date = dt.date.fromisoformat(expiry)
    today = dt.date.today()
    days = (expiry_date - today).days

    if days <= 0:
        raise ValueError(f"Expiration {expiry} has already passed.")

    return days / 365.0

def get_option_chain(ticker: str, expiry: str) -> pd.DataFrame:
    """
    Retrieve calls and puts for one expiration date.
    Args:
        ticker (str): Underlying ticker symbol.
        expiry (str): Expiration date in YYYY-MM-DD format.

    Returns:
        pd.DataFrame: Combined call/put option chain.

    """
    ticker = ticker.strip().upper()

    stock = yf.Ticker(ticker)

    available_expiries = list(stock.options)

    if expiry not in available_expiries:
        raise ValueError(f"Expiration {expiry} not available for {ticker}.")

    # Retrieve option chain from Yahoo Finance
    chain = stock.option_chain(expiry)
    calls = chain.calls.copy()
    puts = chain.puts.copy()

    # Add option type
    calls["otype"] = "call"
    puts["otype"] = "put"

    # Combine calls and puts
    options = pd.concat([calls,puts], ignore_index=True)

    # Add identifying information
    options["ticker"] = ticker
    options["expiry"] = expiry

    # Calculate time to expiry
    T = time_to_expiry(expiry)

    options["T"] = T

    # Retrieve current underlying price
    price_data = stock.history(period="1d")
    if price_data.empty:
        raise ValueError(f"Could not retrieve underlying price for {ticker}.")

    spot = float(price_data["Close"].iloc[-1])

    options["spot"] = spot

    # Mid price between bid and ask
    options["mid"] = (options["bid"] + options["ask"]) / 2

    # Moneyness measures
    options["moneyness"] = (options["strike"] / spot)

    options["log_moneyness"] = (options["strike"] / spot).apply(math.log)

    # Keep only useful columns
    columns = [
        "ticker",
        "expiry",
        "otype",
        "contractSymbol",
        "strike",
        "spot",
        "bid",
        "ask",
        "mid",
        "lastPrice",
        "volume",
        "openInterest",
        "impliedVolatility",
        "T",
        "moneyness",
        "log_moneyness"
    ]
    options = options[columns]

    return options

def clean_option_chain(options: pd.DataFrame, max_bid_ask_pct: float = 0.50, min_open_interest: int = 0) -> pd.DataFrame:
    """
    Clean an option chain before implied vol analysis.
    Removes options with invalid prices and optionally filters contracts with very wide bid-ask spreads
    or insufficient open interest.
    Args:
        options (pd.DataFrame): Raw option chain.
        max_bid_ask_pct (float): Maximum bid-ask spread as a fraction of mid price.
        min_open_interest (int): Minimum required open interest.

    Returns:
        pd.DataFrame: Cleaned option chain.

    """
    df = options.copy()

    # Remove missing bid,ask,strike values
    df = df.dropna(subset=["strike","bid","ask","mid"])

    # Price validation
    df = df[
        (df["strike"] > 0)
        & (df["bid"] >= 0)
        & (df["ask"] > 0)
        & (df["mid"] > 0)
        ]

    # Ask should not be below bid
    df = df[df["ask"] >= df["bid"]]

    # Calculate bid-ask spread
    df["bid_ask_spread"] = (df["ask"] - df["bid"])

    # Calculate spread relative to mid price
    df["bid_ask_pct"] = (df["bid_ask_spread"] / df["mid"])

    # Remove very wide spreads
    df = df[df["bid_ask_pct"] <= max_bid_ask_pct]

    # Fix NaN of open interest
    df["openInterest"] = (df["openInterest"].fillna(0))

    # Remove contracts with less than minimum open interest
    df = df[df["openInterest"] >= min_open_interest]

    return df.reset_index(drop=True)

def add_calculated_iv(options: pd.DataFrame, r: float, initial_vol: float = 0.25) -> pd.DataFrame:
    """
    Calculate implied vol for each option using the contract's mid-market price.
    Args:
        options (pd.DataFrame): Cleaned option chain.
        r (float): Risk-free rate as a decimal.
        initial_vol (float): Initial vol guess for Newton-Raphson.

    Returns:
        pd.DataFrame: Option chain with a calculated_iv column.

    """
    df = options.copy()

    calculated_ivs = []

    for i, row in df.iterrows():
        try:
            bs = BlackScholes(ticker=row["ticker"], expiry=row["expiry"])

            iv = implied_vol_newton(
                bs=bs,
                otype=row["otype"],
                market_price=float(row["mid"]),
                S=float(row["spot"]),
                K=float(row["strike"]),
                T=float(row["T"]),
                r=r,
                initial_vol=initial_vol
            )

            calculated_ivs.append(iv)

        except Exception:
            # Some contracts may fail to converge --> set as missing
            calculated_ivs.append(float("nan"))
    df["calculated_iv"] = calculated_ivs

    return df

def plot_vol_smile_strike(options: pd.DataFrame) -> None:
    """
    Plot calculated implied vol against strike for calls and puts.
    Args:
        options (pd.DataFrame): Option chain containing calculated implied vol values.
    """
    plot_df = options[
        (options["moneyness"] >= 0.90)
        & (options["moneyness"] <= 1.10)
        ].copy()

    calls = plot_df[options["otype"] == "call"].sort_values("strike")
    puts = plot_df[options["otype"] == "put"].sort_values("strike")

    fig, ax = plt.subplots(figsize=(9,5))

    ax.plot(
        calls["strike"],
        calls["calculated_iv"] * 100,
        marker="o",
        label="Calls"
    )

    ax.plot(
        puts["strike"],
        puts["calculated_iv"] * 100,
        marker="o",
        label="Puts"
    )

    if options["ticker"].nunique() != 1:
        raise ValueError(
            "Volatility smile must contain exactly one ticker."
        )

    if options["expiry"].nunique() != 1:
        raise ValueError(
            "Volatility smile must contain exactly one expiry."
        )

    ticker = options["ticker"].iloc[0]
    expiry = options["expiry"].iloc[0]

    ax.set_title(f"Implied Volatility Smile: {ticker} {expiry}")

    ax.set_xlabel("Strike")
    ax.set_ylabel("Implied Volatility (%)")

    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.show()

def plot_vol_smile_moneyness(options: pd.DataFrame) -> None:
    """
    Plot calculated implied vol against moneyness for calls and puts.
    Args:
        options (pd.DataFrame): Option chain containing calculated implied vol values.
    """
    plot_df = options[
        (options["moneyness"] >= 0.90)
        & (options["moneyness"] <= 1.10)
        ].copy()

    calls = plot_df[options["otype"] == "call"].sort_values("moneyness")
    puts = plot_df[options["otype"] == "put"].sort_values("moneyness")

    fig, ax = plt.subplots(figsize=(9,5))

    ax.plot(
        calls["moneyness"],
        calls["calculated_iv"] * 100,
        marker="o",
        label="Calls"
    )

    ax.plot(
        puts["moneyness"],
        puts["calculated_iv"] * 100,
        marker="o",
        label="Puts"
    )

    if options["ticker"].nunique() != 1:
        raise ValueError(
            "Volatility smile must contain exactly one ticker."
        )

    if options["expiry"].nunique() != 1:
        raise ValueError(
            "Volatility smile must contain exactly one expiry."
        )

    ticker = options["ticker"].iloc[0]
    expiry = options["expiry"].iloc[0]

    ax.set_title(f"Implied Volatility vs Moneyness: {ticker} {expiry}")

    ax.set_xlabel("Moneyness (K / S)")
    ax.set_ylabel("Implied Volatility (%)")

    # ATM reference line
    ax.axvline(1.0, linestyle="--", label="ATM")

    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def calculate_skew_metrics(options: pd.DataFrame) -> dict:
    """
    Calculate simple volatility skew metrics using calculated IV.
    Args:
        options (pd.DataFrame): Option chain containing moneyness and calculated IV.

    Returns:
        dict: ATM IV, downside IV, upside IV, downside skew and upside skew.

    """
    df = options.dropna(subset=["moneyness", "calculated_iv"]).copy()

    if df.empty:
        raise ValueError("No valid IV observations available.")

    # Find observations nearest to target moneyness levels
    atm_row = df.iloc[(df["moneyness"]-1.00).abs().argmin()]

    downside_row = df.iloc[(df["moneyness"]-0.90).abs().argmin()]

    upside_row = df.iloc[(df["moneyness"]-1.10).abs().argmin()]

    atm_iv = float(atm_row["calculated_iv"])
    downside_iv = float(downside_row["calculated_iv"])
    upside_iv = float(upside_row["calculated_iv"])

    downside_skew = downside_iv - atm_iv
    upside_skew = upside_iv - atm_iv

    return {
        "ATM IV": atm_iv,
        "Downside IV": downside_iv,
        "Upside IV": upside_iv,
        "Downside Skew": downside_skew,
        "Upside Skew": upside_skew,
        "ATM Moneyness": float(atm_row["moneyness"]),
        "Downside Moneyness": float(downside_row["moneyness"]),
        "Upside Moneyness": float(upside_row["moneyness"])
    }

if __name__ == "__main__":

    ticker = "AAPL"

    expiries = get_expiries(ticker)

    expiry = expiries[5]

    chain = get_option_chain(
        ticker=ticker,
        expiry=expiry
    )

    cleaned = clean_option_chain(
        chain,
        max_bid_ask_pct=0.50,
        min_open_interest=1
    )

    # Get maturity
    T = time_to_expiry(expiry)

    # Get market-based rate for this expiry
    r = get_risk_free_rate(T)

    print(f"Expiry: {expiry}")
    print(f"T: {T:.4f} years")
    print(f"Risk-free rate: {r:.4%}")

    iv_chain = add_calculated_iv(
        options=cleaned,
        r=r,
        initial_vol=0.25
    )

    # Remove contracts where solver failed
    iv_chain = iv_chain.dropna(
        subset=["calculated_iv"]
    )

    # Remove obviously unreasonable outputs
    iv_chain = iv_chain[
        (iv_chain["calculated_iv"] > 0)
        & (iv_chain["calculated_iv"] < 5.0)
    ].reset_index(drop=True)

    # Compare your IV with Yahoo's IV
    iv_chain["iv_difference"] = (
        iv_chain["calculated_iv"]
        - iv_chain["impliedVolatility"]
    )

    print(
        iv_chain[
            [
                "otype",
                "strike",
                "mid",
                "impliedVolatility",
                "calculated_iv",
                "iv_difference",
                "moneyness"
            ]
        ].head(30)
    )

    plot_vol_smile_strike(iv_chain)

    plot_vol_smile_moneyness(iv_chain)

    skew = calculate_skew_metrics(iv_chain)

    print("\nVOLATILITY SKEW")
    print("----------------")

    print(
        f"ATM IV: "
        f"{skew['ATM IV']:.2%}"
    )

    print(
        f"Downside IV: "
        f"{skew['Downside IV']:.2%}"
    )

    print(
        f"Upside IV: "
        f"{skew['Upside IV']:.2%}"
    )

    print(
        f"Downside Skew: "
        f"{skew['Downside Skew'] * 100:+.2f} vol pts"
    )

    print(
        f"Upside Skew: "
        f"{skew['Upside Skew'] * 100:+.2f} vol pts"
    )