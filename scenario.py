def run_scenario(
        portfolio,
        spot_prices: dict,
        rates_by_expiry: dict,
        vols_by_contract: dict,
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
        spot_prices (dict): Current underlying prices of each ticker.
        rates_by_expiry (dict): Risk-free rates for each expiration.
        vols_by_contract (dict): Market implied volatilities for each contract.
        spot_change (float): Relative percentage change to spot.
        vol_change (float): Absolute change in volatility.
        rate_change (float): Absolute change in interest rates.
        days_forward (int): Number of calendar days to roll the portfolio forward.

    Returns:
        dict: Base and stressed market conditions, portfolio values, and resulting scenario P&L.
    """

    if days_forward < 0:
        raise ValueError("days_forward cannot be negative.")

    # Value the portfolio under current market conditions (today)
    base_results = portfolio.evaluate(spot_prices=spot_prices, rates_by_expiry=rates_by_expiry, vols_by_contract=vols_by_contract, days_forward=0)

    base_summary = portfolio.risk_summary(base_results)

    # Apply the specified market shocks
    # Spot shock is relative, the latter shocks are absolute
    stressed_spot_prices = {
        ticker: price * (1 + spot_change)
        for ticker, price in spot_prices.items()
    }
    stressed_vols = {
        contract: base_vol + vol_change
        for contract, base_vol
        in vols_by_contract.items()
    }

    invalid_vols = {
        contract: vols_by_contract
        for contract, vol in stressed_vols.items()
        if vol <= 0
    }

    if invalid_vols:
        raise ValueError(f"Scenario produces non-positive IV: {invalid_vols}")

    stressed_rates = {
        expiry: rate + rate_change
        for expiry, rate in rates_by_expiry.items()
    }

    # Fully reprice every position using stressed market conditions and passage of time
    stressed_results = portfolio.evaluate(
        spot_prices=stressed_spot_prices,
        rates_by_expiry=stressed_rates,
        vols_by_contract=stressed_vols,
        days_forward=days_forward
    )

    stressed_summary = portfolio.risk_summary(stressed_results)

    pnl = (stressed_summary["Position Value"] - base_summary["Position Value"])

    return {
        "Base Value": base_summary["Position Value"],
        "Stressed Value": stressed_summary["Position Value"],
        "PnL": pnl,
        "Base Spots": spot_prices,
        "Stressed Spots": stressed_spot_prices,
        "Base Vols": vols_by_contract,
        "Stressed Vols": stressed_vols,
        "Base Rates": rates_by_expiry,
        "Stressed Rates": stressed_rates,
        "Days Forward": days_forward
    }
