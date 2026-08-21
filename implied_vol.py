from blackscholes import BlackScholes


# Implied Volatility Calculation
def implied_vol_newton(bs: BlackScholes, otype: str, market_price: float, S: float, K: float, T: float, r: float,
                       initial_vol: float = 0.25, tol: float = 1e-8) -> float:
    """
    Calculates the implied volatility using the Newton Raphson Method
    Args:
    otype (str): Option type, if it is call or put

    Returns:
    implied_vol (float): The calculated implied volatility
    """
    max_iter = 100  # max iterations to find IV, in case we do not find a convergence
    old_vol = initial_vol  # initial guess
    otype = otype.lower()

    for i in range(max_iter):
        bs_results = bs.quote(S=S, T=T, r=r, K=K, vol=old_vol)
        theoretical_price = bs_results["prices"][otype]
        Cprime = bs_results["greeks"][otype]["Vega"]

        # safety check for vega
        if abs(Cprime) < 1e-12:
            raise ValueError("Vega too close to zero for Newton-Raphson.")

        C = theoretical_price - market_price

        new_vol = old_vol - (C / Cprime)

        # safety check for new_vol
        if new_vol <= 0:
            raise ValueError("Newton-Raphson produced non-positive volatility.")

        new_bs_results = bs.quote(S=S, T=T, r=r, K=K, vol=new_vol)

        # continue iterating until difference between the volatilities or prices are less than tolerance
        if (
                abs(old_vol - new_vol) < tol
                or abs(new_bs_results["prices"][otype] - market_price) < tol
        ):
            return new_vol

        old_vol = new_vol

        return old_vol
