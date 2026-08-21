from blackscholes import BlackScholes

def run_scenario(
        portfolio,
        S: float,
        r: float,
        vol: float,
        spot_change: float = 0.0,
        vol_change: float = 0.0,
        rate_change: float = 0.0
) -> dict:
    base_results = portfolio.evaluate(S=S, r=r, vol=vol)

    base_summary = portfolio.risk_summary(base_results)

    stressed_S = S * (1+spot_change)
    stressed_vol = vol + vol_change
    stressed_r = r + rate_change

    stressed_results = portfolio.evaluate(
        S=stressed_S,
        r=stressed_r,
        vol=stressed_vol
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
    }
