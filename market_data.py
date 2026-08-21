import yfinance as yf


def get_underlying_price(ticker: str) -> float:
    """
    Retrieve the live underlying price from Yahoo Finance
    Args:
    ticker (str): ticker
    Return:
    underlying_price (float): latest closing price
    """
    ticker = ticker.strip().upper()
    data = yf.Ticker(ticker).history(period="1d")
    if data.empty:
        raise ValueError(f"No market data found for ticker: {ticker}")
    underlying_price = data["Close"].iloc[-1]
    return float(underlying_price)


def get_risk_free_rate(T: float) -> float:
    """
    Retrieve live risk-free rate from Yahoo Finance depending on time to expiration
    Args:
    T (float): time to expiry in years
    Return:
    r (float): risk-free rate
    """
    if T <= 0:
        raise ValueError("Time to expiration must be positive.")
    if T <= 0.25:
        rf_ticker = "^IRX"  # 13W
    elif T <= 2:
        rf_ticker = "^FVX"  # 5Y
    elif T <= 10:
        rf_ticker = "^TNX"  # 10Y
    else:
        rf_ticker = "^TYX"  # 30Y

    data = yf.Ticker(rf_ticker).history(period="1d")

    if data.empty:
        raise ValueError(f"Could not retrieve risk-free rate from {rf_ticker}")
    else:
        r = float(data["Close"].iloc[-1]) / 100.0
    return r
