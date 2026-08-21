def run_scenario(
        portfolio,
        S: float,
        r: float,
        vol: float,
        spot_change: float = 0.0,
        vol_change: float = 0.0,
        rate_change: float = 0.0,
        days_forward: int = 0
) -> dict:
    """
    Run a market-risk scenario using full portfolio repricing.

    The portfolio is first valued under current market conditions.
    Market shocks are then applied to spot, volatility and interest rates,
    and the entire portfolio is repriced.

    Scenario P&L = stressed portfolio value - base portfolio value
    Args:
        portfolio (OptionPortfolio): OptionPortfolio to stress.
        S (float): Current underlying price.
        r (float): Current risk-free rate as a decimal.
        vol (float): Current volatility as a decimal.
        spot_change (float): Relative percentage change to spot.
        vol_change (float): Absolute change in volatility.
        rate_change (float): Absolute change in interest rates.

    Returns:
        dict: Base and stressed market conditions, portfolio values, and resulting scenario P&L.
    """

    if days_forward < 0:
        raise ValueError("days_forward cannot be negative.")

    # Value the portfolio under current market conditions (today)
    base_results = portfolio.evaluate(S=S, r=r, vol=vol, days_forward=0)

    base_summary = portfolio.risk_summary(base_results)

    # Apply the specified market shocks
    # Spot shock is relative, the latter shocks are absolute
    stressed_S = S * (1+spot_change)
    stressed_vol = vol + vol_change
    stressed_r = r + rate_change

    # Fully reprice every position using stressed market conditions and passage of time
    stressed_results = portfolio.evaluate(
        S=stressed_S,
        r=stressed_r,
        vol=stressed_vol,
        days_forward=days_forward
    )

    stressed_summary = portfolio.risk_summary(stressed_results)

    pnl = (stressed_summary["Position Value"] - base_summary["Position Value"])

    return {
        "Base Value": base_summary["Position Value"],
        "Stressed Value": stressed_summary["Position Value"],
        "PnL": pnl,
        "Base Spot": S,
        "Stressed Spot": stressed_S,
        "Base Vol": vol,
        "Stressed Vol": stressed_vol,
        "Base Rate": r,
        "Stressed Rate": stressed_r,
        "Days Forward": days_forward
    }
