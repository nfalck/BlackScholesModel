class OptionPosition:
    def __init__(
            self,
            ticker: str,
            otype: str,
            strike: float,
            expiry: str,
            quantity: int,
            multiplier: int = 100
    ):
        self.ticker = ticker.strip().upper()
        self.otype = otype.strip().lower()
        self.strike = strike
        self.expiry = expiry
        self.quantity = quantity
        self.multiplier = multiplier

        if self.otype not in ("call", "put"):
            raise ValueError("otype must be 'call' or 'put'")

        if self.strike <= 0:
            raise ValueError("strike must be positive")

        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")

    def underlying_units(self) -> int:
        return self.quantity * self.multiplier

    def position_value(self, option_price: float) -> float:
        return option_price * self.quantity * self.multiplier

    def position_greeks(self, greeks: dict) -> dict:
        scale = self.quantity * self.multiplier

        return {
            "Delta": greeks["Delta"] * scale,
            "Gamma": greeks["Gamma"] * scale,
            "Vega": greeks["Vega"] * scale,
            "Theta": greeks["Theta"] * scale,
            "Rho": greeks["Rho"] * scale,
        }

