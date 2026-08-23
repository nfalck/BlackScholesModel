from option_chain import get_option_chain, clean_option_chain, add_calculated_iv

def create_market_vols(portfolio, rates_by_expiry: dict) -> dict:
    """
    Create a dictionary of market implied vols for every option contract in a portfolio.
    Args:
        portfolio: OptionPortfolio containing the positions.
        rates_by_expiry (dict): Risk-free rates for each expiry.

    Returns:
        dict: Market implied vol keyed by contract.

    """
    vols_by_contract = {}

    ticker_expiry_pairs = {
        (position.ticker, position.expiry)
        for position in portfolio.positions
    }

    for ticker, expiry in ticker_expiry_pairs:
        if expiry not in rates_by_expiry:
            raise ValueError(f"Missing rate for expiry: {expiry}")

        r = rates_by_expiry[expiry]

        # Fetch market option chain
        chain = get_option_chain(ticker=ticker, expiry=expiry)

        # Remove illiquid quotes
        cleaned_chain = clean_option_chain(chain, max_bid_ask_pct=0.50, min_open_interest=1)

        # Calculate own IV from market mid prices
        iv_chain = add_calculated_iv(options=cleaned_chain, r=r, initial_vol=0.25)

        # Remove failed/unreasonable solver outputs
        iv_chain = iv_chain.dropna(subset=["calculated_iv"])

        iv_chain = iv_chain[(iv_chain["calculated_iv"] > 0) & (iv_chain["calculated_iv"] < 5.0)]

        # Store each contract's IV
        for i, row in iv_chain.iterrows():
            key = (
                str(row["ticker"]).upper(),
                str(row["otype"]).lower(),
                float(row["strike"]),
                str(row["expiry"])
            )

            vols_by_contract[key] = float(row["calculated_iv"])

    return vols_by_contract
