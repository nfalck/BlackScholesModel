class OptionPosition:
    """
    Represents a single option position in a portfolio.

    Quantity determines the direction of a position (positive for long, negative for short).

    The multiplier represents # of underlying shares represented by one option contract.
    """
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

        # Validation checks
        if self.otype not in ("call", "put"):
            raise ValueError("otype must be 'call' or 'put'")

        if self.strike <= 0:
            raise ValueError("strike must be positive")

        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")

    def underlying_units(self) -> int:
        """
        Return the total number of underlying units represented by the position.
        Returns:
            int: Quantity multiplied by the contract multiplier.
        """
        return self.quantity * self.multiplier

    def position_value(self, option_price: float) -> float:
        """
        Calculate the signed market value of the option position.
        Args:
            option_price (float): Price of one option unit.

        Returns:
            float: Position value after accounting for quantity and contract multiplier.
        """
        return option_price * self.quantity * self.multiplier

    def position_greeks(self, greeks: dict) -> dict:
        """
        Scale single-option reporting Greeks to position-level Greeks.
        Args:
            greeks (dict): Reporting Greeks for one option unit.

        Returns:
            dict: Greeks for the entire position.

        """
        scale = self.quantity * self.multiplier

        return {
            "Delta": greeks["Delta"] * scale,
            "Gamma": greeks["Gamma"] * scale,
            "Vega": greeks["Vega"] * scale,
            "Theta": greeks["Theta"] * scale,
            "Rho": greeks["Rho"] * scale,
        }

