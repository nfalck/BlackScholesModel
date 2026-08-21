from option_position import OptionPosition
from blackscholes import BlackScholes

class OptionPortfolio:
    def __init__(self, positions: list[OptionPosition] | None = None):
        self.positions = positions if positions is not None else []

    def add_position(self, position: OptionPosition) -> None:
        self.positions.append(position)

    def evaluate(self, S: float, r: float, vol: float) -> list[dict]:
        results = []

        for position in self.positions:
            bs = BlackScholes(
                ticker=position.ticker,
                expiry=position.expiry
            )

            T = bs.time_to_expiration()

            out = bs.quote(S=S, K=position.strike, T=T, r=r, vol=vol)

            option_price = out["prices"][position.otype]
            reporting_greeks = out["reporting_greeks"][position.otype]
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
        totals = {
            "Position Value": 0.0,
            "Delta": 0.0,
            "Gamma": 0.0,
            "Vega": 0.0,
            "Theta": 0.0,
            "Rho": 0.0
        }

        for result in evaluated_positions:
            for key in totals:
                totals[key] += result[key]

        return totals

