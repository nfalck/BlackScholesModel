def greek_pnl_approximation(
        evaluated_positions: list[dict],
        spot_prices: dict,
        spot_change: float = 0.0,
        vol_change: float = 0.0,
        rate_change: float = 0.0,
        days_forward: int = 0
):
    """
    Approximate portfolio P&L using reporting Greeks.

    Args:
        evaluated_positions (list[dict]): Position-level results returned by OptionPortfolio.evaluate().
        spot_prices (dict): Current underlying prices for each ticker.
        spot_change (float): Relative percentage shock applied to each underlying.
        vol_change (float): Absolute volatility shock.
        rate_change (float): Absolute interest rate shock.
        days_forward (int): Number of calendar days to roll the portfolio forward.

    Returns:
        dict: P&L contributions of each Greek including total approximated P&L

    """
    if days_forward < 0:
        raise ValueError("days_forward cannot be negative.")

    delta_pnl = 0.0
    gamma_pnl = 0.0
    vega_pnl = 0.0
    theta_pnl = 0.0
    rho_pnl = 0.0

    # Reporting Vega is per 1 volatility point
    vol_points = vol_change * 100

    # Reporting Rho is per 1 percentage-point rate move
    rate_points = rate_change * 100

    for position in evaluated_positions:
        ticker = position["Ticker"]

        if ticker not in spot_prices:
            raise ValueError(f"Missing spot price for ticker: {ticker}")

        S = spot_prices[ticker]

        # Convert percentage spot shock into dollar move
        dS = S * spot_change

        delta_pnl += position["Delta"] * dS

        gamma_pnl += (0.5 * position["Gamma"] * (dS ** 2))

        vega_pnl += (position["Vega"] * vol_points)

        rho_pnl = (position["Rho"] * rate_points)

        theta_pnl = (position["Theta"] * days_forward)

    total_pnl = (delta_pnl + gamma_pnl + vega_pnl + rho_pnl + theta_pnl)

    return {
        "Delta PnL": delta_pnl,
        "Gamma PnL": gamma_pnl,
        "Vega PnL": vega_pnl,
        "Rho PnL": rho_pnl,
        "Theta PnL": theta_pnl,
        "Total PnL": total_pnl
    }
