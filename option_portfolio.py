from option_position import OptionPosition
from blackscholes import BlackScholes
import pandas as pd

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

    def evaluate(self, spot_prices: dict, r: float, vol: float, days_forward: int = 0) -> list[dict]:
        """
        Price every option position and calculate position-level risk.
        Args:
            spot_prices (dict): Current underlying prices of each ticker.
            r (float): Risk-free rate as a decimal.
            vol (float): Volatility as a decimal.
            days_forward (int): # of calendar days to move forward for scenario analysis.

        Returns:
            list[dict]: Pricing and Greeks results for each position.
        """
        if days_forward < 0:
            raise ValueError("days_forward cannot be negative.")

        missing_tickers = {
            position.ticker
            for position in self.positions
            if position.ticker not in spot_prices
        }

        if missing_tickers:
            raise ValueError(f"Missing spot prices for: {sorted(missing_tickers)}")

        results = []

        # Evaluate each option position individually
        for position in self.positions:
            S = spot_prices[position.ticker]

            bs = BlackScholes(
                ticker=position.ticker,
                expiry=position.expiry
            )

            # Calculate current time to expiry
            T = bs.time_to_expiration()

            # Reduce time to expiry to simulate the passage of time
            stressed_T = T - (days_forward / 365.0)

            if stressed_T <= 0:
                raise ValueError(f"Scenario moves beyond expiry for {position.ticker} {position.strike} {position.otype}")

            # Price the option and calculate its Greeks
            out = bs.quote(S=S, K=position.strike, T=stressed_T, r=r, vol=vol)

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
                    "T": stressed_T,
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

    @classmethod
    def from_csv(cls, file):
        """
        Create an OptionPortfolio from a CSV file.

        Expected Columns:
            ticker
            otype
            strike
            expiry
            quantity
            multiplier (optional)

        Args:
            file: Uploaded CSV file from Streamlit Dashboard.

        Returns:
            OptionPortfolio: Portfolio created from CSV positions.

        """
        df = pd.read_csv(file)

        required_columns = {
            "ticker",
            "otype",
            "strike",
            "expiry",
            "quantity"
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        positions = []

        for i, row in df.iterrows():
            multiplier = (
                int(row["multiplier"])
                if "multiplier" in df.columns
                else 100
            )

            position = OptionPosition(
                ticker=str(row["ticker"]),
                otype=str(row["otype"]),
                strike=float(row["strike"]),
                expiry=str(row["expiry"]),
                quantity=int(row["quantity"]),
                multiplier=multiplier
            )

            positions.append(position)

        return cls(positions)