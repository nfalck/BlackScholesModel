from scipy.stats import norm
import datetime as dt
import math
from typing import Optional


class BlackScholes:
    def __init__(self, ticker: str, expiry: str):
        # Initialized Variables
        self.ticker = ticker.strip().upper()
        self.expiry = expiry

    def time_to_expiration(self) -> float:
        """
        Convert date_string to date and calculate time to expiry in years
        Return:
        T (float): time to expiry in years
        """
        expiry_date = dt.date.fromisoformat(self.expiry)  # convert date_string to date
        today = dt.date.today()
        T = ((expiry_date - today).days) / 365.0
        return T

    def d1_and_d2(self, S: float, K: float, T: float, r: float, vol: float) -> tuple[float, float]:
        """
        Calculate d1 and d2
        Args:
        S (float): underlying price
        K (float): strike price
        T (float): time to expiration in years
        r (float): risk-free rate
        vol (float): volatility
        Return:
        d1, d2 (tuple [float, float]): intermediate variables for calculating option prices and Greeks
        """
        d1 = (math.log(S/K) + (r+0.5*vol**2)*T) / (vol*math.sqrt(T))
        d2 = d1 - (vol*math.sqrt(T))
        return d1, d2

    def call_and_put_price(self, S: float, K: float, T: float, r: float, vol: float) -> dict:
        """
        Calculate the Black Scholes theoretical prices of a European call and put option
        Args:
        S (float): underlying price
        K (float): strike price
        T (float): time to expiration in years
        r (float): risk-free rate
        vol (float): volatility
        Return:
            dict:
                call (float): Black Scholes call price
                put (float): Black Scholes put price
        """
        d1, d2 = self.d1_and_d2(S, K, T, r, vol)
        C = (S * norm.cdf(d1)) - (K * math.exp(-r * T) * norm.cdf(d2))  # call price
        P = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)  # put price
        return {
            "call": C, "put": P
        }

    def greeks(self, S: float, K: float, T: float, r: float, vol: float) -> dict:
        """
        Calculate option Greeks for a European call and put option
        Args:
        S (float): underlying price
        K (float): strike price
        T (float): time to expiration in years
        r (float): risk-free rate
        vol (float): volatility
        Return:
            dict:
                call (dict): Greeks for the call option
                    Delta (float): Rate of change of option value to underlying price
                    Gamma (float): Rate of change in delta to changes in underlying price
                    Vega (float): Sensitivity to Volatility
                    Theta (float): Sensitivity to time
                    Rho (float): Sensitivity to interest rate
                put (dict): Greeks for the put option
                    Delta (float): Rate of change of option value to underlying price
                    Gamma (float): Rate of change in delta to changes in underlying price
                    Vega (float): Sensitivity to Volatility
                    Theta (float): Sensitivity to time
                    Rho (float): Sensitivity to interest rate

        """
        d1, d2 = self.d1_and_d2(S, K, T, r, vol)
        # Delta - Rate of change of theoretical option value with respect to underlying price
        # Measures impact of a change in the price of underlying asset
        delta_call = norm.cdf(d1)
        delta_put = -norm.cdf(-d1)

        # Gamma - Rate of change in delta with respect to changes in underlying price
        gamma = (norm.pdf(d1))/(S*vol*math.sqrt(T))

        # Vega - Sensitivity to vol, derivative of option value with regards to volatility of underlying asset
        # Measures impact of a change in volatility
        vega = S * norm.pdf(d1) * math.sqrt(T)

        # Theta - Sensitivity of value of derivative to the passage of time, time decay
        # Measures impact of a change in time remaining
        theta_call = -(S * norm.pdf(d1) * vol) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)
        theta_put = -(S * norm.pdf(d1) * vol) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)

        # Rho - Sensitivity to the interest rate
        rho_call = K * T * math.exp(-r * T) * norm.cdf(d2)
        rho_put = -K * T * math.exp(-r * T) * norm.cdf(-d2)

        return {"call": {"Delta": delta_call, "Gamma": gamma, "Vega": vega, "Theta": theta_call, "Rho": rho_call}, "put": {"Delta": delta_put, "Gamma": gamma, "Vega": vega, "Theta": theta_put, "Rho": rho_put}}

    def reporting_greeks(self, S: float, K: float, T: float, r:float, vol:float) -> dict:
        """
            Convert raw Black Scholes Greeks into practical reporting units.
            Args:
            S (float): underlying price
            K (float): strike price
            T (float): time to expiration in years
            r (float): risk-free rate
            vol (float): volatility
            Return:
                dict:
                    call (dict): Greeks for the call option
                        Delta (float): Rate of change of option value to underlying price
                        Gamma (float): Rate of change in delta to changes in underlying price
                        Vega (float): Change in option value for 1 percentage-point change in volatility
                        Theta (float): Change in option value per day due to passage of time
                        Rho (float): Change in option value for 1 percentage-point change in the risk-free rate
                    put (dict): Greeks for the put option
                        Delta (float): Rate of change of option value to underlying price
                        Gamma (float): Rate of change in delta to changes in underlying price
                        Vega (float): Change in option value for 1 percentage-point change in volatility
                        Theta (float): Change in option value per day due to passage of time
                        Rho (float): Change in option value for 1 percentage-point change in the risk-free rate

        """
        raw = self.greeks(S,K,T,r,vol)
        result = {}
        for otype in ("call", "put"):
            result[otype] = {
                "Delta": raw[otype]["Delta"],
                "Gamma": raw[otype]["Gamma"],
                "Vega": raw[otype]["Vega"] / 100,
                "Theta": raw[otype]["Theta"] / 365,
                "Rho": raw[otype]["Rho"] / 100
            }
        return result

    def quote(self, S: float, T: float, r: float, K: float, vol: float) -> dict:
        """
        Call functions to calculate option prices and Greeks using Black Scholes and bundle
        all inputs and outputs in a quote for easy access.
        Args:
        S (float): underlying price
        T (float): time to expiration in years
        r (float): risk-free rate
        K (float): strike price
        vol (float): volatility
        Return:
            dict:
            ticker (str): ticker
            expiry (str): expiration date (YYYY-MM-DD)
            S (float): underlying price
            T (float): time to expiration in years
            r (float): risk-free rate
            K (float): strike price
            vol (float): volatility
            prices (dict): theoretical option prices
                call (float): Black Scholes price of the European call
                put (float): Black Scholes price of the European put
            greeks (dict): mathematically calculated option Greeks
                call (dict): Greeks for the call option
                put (dict): Greeks for the put option
            reporting_greeks (dict): greeks + reformatted vega, theta and rho for reporting
                call (dict): Reporting Greeks for the call option
                put (dict): Reporting Greeks for the put option
        """
        prices = self.call_and_put_price(S, K, T, r, vol)
        raw_greeks = self.greeks(S, K, T, r, vol)
        reporting_greeks = self.reporting_greeks(S, K, T, r, vol)
        return {"ticker": self.ticker, "expiry": self.expiry, "S": S, "T": T, "r": r, "K": K, "vol": vol,
            "prices": prices, "greeks": raw_greeks, "reporting_greeks": reporting_greeks}