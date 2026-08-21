def greek_pnl_approximation(
        portfolio_greeks: dict,
        S: float,
        spot_change: float = 0.0,
        vol_change: float = 0.0,
        rate_change: float = 0.0,
        days_forward: int = 0
):
    """
    Approximate portfolio P&L using reporting Greeks.
    """
    delta = portfolio_greeks["Delta"]
    gamma = portfolio_greeks["Gamma"]
    vega = portfolio_greeks["Vega"]
    rho = portfolio_greeks["Rho"]
    theta = portfolio_greeks["Theta"]

    # Convert percentage spot shock into dollar move
    dS = S * spot_change

    # Reporting Vega is per 1 volatility point
    vol_points = vol_change * 100

    # Reporting Rho is per 1 percentage-point rate move
    rate_points = rate_change * 100

    delta_pnl = delta * dS

    gamma_pnl = 0.5 * gamma * (dS ** 2)

    vega_pnl = vega * vol_points

    rho_pnl = rho * rate_points

    theta_pnl = theta * days_forward

    total_pnl = (delta_pnl + gamma_pnl + vega_pnl + rho_pnl + theta_pnl)

    return {
        "Delta PnL": delta_pnl,
        "Gamma PnL": gamma_pnl,
        "Vega PnL": vega_pnl,
        "Rho PnL": rho_pnl,
        "Theta PnL": theta_pnl,
        "Total PnL": total_pnl
    }
