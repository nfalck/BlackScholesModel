from option_position import OptionPosition
from blackscholes import BlackScholes

class OptionPortfolio:
    """
    Represents a portfolio of option positions.

    Provides functionality to evaluate individual positions using Black Scholes
    and aggregate their values and Greeks into portfolio-level risk measures.
    """
    def __init__(self, positions: list[OptionPosition] | None = None):
        # Allow creation of either an empty portfolio or one with initial list of positions
        self.positions = positions if positions is not None else []

    def add_position(self, position: OptionPosition) -> None:
        """
        Add an option position to the portfolio.
        Args:
            position (OptionPosition): Position to add.
        """
        self.positions.append(position)

    def evaluate(self, S: float, r: float, vol: float) -> list[dict]:
        """
        Price every option position and calculate position-level risk.
        Args:
            S (float): Current underlying price.
            r (float): Risk-free rate as a decimal.
            vol (float): Volatility as a decimal.

        Returns:
            list[dict]: Pricing and Greeks results for each position.
        """
        results = []

        # Evaluate each option position individually
        for position in self.positions:
            bs = BlackScholes(
                ticker=position.ticker,
                expiry=position.expiry
            )

            # Calculate time to expiry
            T = bs.time_to_expiration()

            # Price the option and calculate its Greeks
            out = bs.quote(S=S, K=position.strike, T=T, r=r, vol=vol)

            # Select call or put results depending on the position
            option_price = out["prices"][position.otype]
            reporting_greeks = out["reporting_greeks"][position.otype]

            # Convert single-option results to position-level results
            position_value = position.position_value(option_price)
            position_risk = position.position_greeks(reporting_greeks)

            results.append(
                {
                    "Ticker": position.ticker,
                    "Type": position.otype,
                    "Strike": position.strike,
                    "Expiry": position.expiry,
                    "Quantity": position.quantity,
                    "Multiplier": position.multiplier,
                    "Price": option_price,
                    "Position Value": position_value,
                    "Delta": position_risk["Delta"],
                    "Gamma": position_risk["Gamma"],
                    "Vega": position_risk["Vega"],
                    "Theta": position_risk["Theta"],
                    "Rho": position_risk["Rho"]
                }
            )

        return results

    def risk_summary(self, evaluated_positions: list[dict]) -> dict:
        """
        Aggregate position-level values and Greeks.
        Args:
            evaluated_positions (list[dict]): Position results produced by evaluate().

        Returns:
            dict: Net portfolio value and portfolio-level Greeks.

        """
        # Initialize at 0
        totals = {
            "Position Value": 0.0,
            "Delta": 0.0,
            "Gamma": 0.0,
            "Vega": 0.0,
            "Theta": 0.0,
            "Rho": 0.0
        }

        # Net long and short position risks across the portfolio
        for result in evaluated_positions:
            for key in totals:
                totals[key] += result[key]

        return totals

