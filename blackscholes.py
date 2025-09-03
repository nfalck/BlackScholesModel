import yfinance as yf
from scipy.stats import norm
import datetime as dt
import math
from typing import Optional
import pandas as pd

class BlackScholes:
    def __init__(self, ticker: str, expiry: str, r_override: Optional[float] = None):
        self.ticker = ticker.strip().upper()
        self.expiry = expiry
        self.r_override = r_override
        self._chains_cache: dict[str, pd.DataFrame] = {}

    def time_to_expiration(self) -> float:
        expiry_date = dt.date.fromisoformat(self.expiry)
        today = dt.date.today()
        T = ((expiry_date - today).days) / 365.0
        return T

    def get_risk_free_rate(self, T: float) -> float:
        if T <= 0.25:
            rf_ticker = "^IRX"  # 13W T-bill (~3M)
        elif T <= 2:
            rf_ticker = "^FVX"  # 5Y
        elif T <= 10:
            rf_ticker = "^TNX"  # 10Y
        else:
            rf_ticker = "^TYX"  # 30Y
        data = yf.Ticker(rf_ticker).history(period="1d")
        if data.empty:
            r = 0.02
        else:
            r = float(data["Close"].iloc[-1]) / 100.0
        return r

    def get_underlying_price(self, ticker:str) -> float:
        underlying_price = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        return underlying_price

    def d1_and_d2(self, S: float, K: float, T: float, r: float, vol: float):
        d1 = (math.log(S/K) + (r+0.5*vol**2)*T) / (vol*math.sqrt(T))
        d2 = d1 - (vol*math.sqrt(T))
        return d1, d2

    def call_and_put_price(self, S: float, K: float, T: float, r: float, vol: float) -> dict:
        d1, d2 = self.d1_and_d2(S, K, T, r, vol)
        C = (S * norm.cdf(d1)) - (K * math.exp(-r * T) * norm.cdf(d2))
        P = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return {
            "call": C, "put": P
        }

    def greeks(self, S: float, K: float, T: float, r: float, vol: float) -> dict:
        d1, d2 = self.d1_and_d2(S, K, T, r, vol)
        # delta - rate of change of theoretical option value with respect to underlying price
        delta_call = norm.cdf(d1)
        delta_put = -norm.cdf(-d1)

        # gamma - rate of change in delta with respect to changes in underlying price
        gamma = (norm.pdf(d1))/(S*vol*math.sqrt(T))

        # vega - sensitivity to vol, derivative of option value with regards to volatility of underlying asset
        vega = S * norm.pdf(d1) * math.sqrt(T)

        # theta - sensitivity of value of derivative to the passage of time, time decay
        theta_call = -(S * norm.pdf(d1) * vol) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)
        theta_put = -(S * norm.pdf(d1) * vol) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)

        # rho - sensitivity to the interest rate
        rho_call = K * T * math.exp(-r * T) * norm.cdf(d2)
        rho_put = -K * T * math.exp(-r * T) * norm.cdf(-d2)

        return {"call": {"Delta": delta_call, "Gamma": gamma, "Vega": vega, "Theta": theta_call, "Rho": rho_call}, "put": {"Delta": delta_put, "Gamma": gamma, "Vega": vega, "Theta": theta_put, "Rho": rho_put}}

    # quote
    def quote(self, S: float, T: float, r: float, K: float, vol: float) -> dict:
        prices = self.call_and_put_price(S, K, T, r, vol)
        greeks = self.greeks(S, K, T, r, vol)
        return {"ticker": self.ticker, "expiry": self.expiry, "S": S, "T": T, "r": r, "K": K, "vol": vol,
            "prices": prices, "greeks": greeks}