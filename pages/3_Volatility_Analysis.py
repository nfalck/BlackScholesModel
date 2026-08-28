import streamlit as st
import plotly.express as px
from option_chain import (get_expiries, get_option_chain, clean_option_chain,
                          add_calculated_iv, calculate_skew_metrics, time_to_expiry)

from market_data import get_risk_free_rate

st.set_page_config(page_title="Volatility Analysis", layout="wide")
st.title("Volatility Analysis")
st.caption("View option-chain implied volatility, smile and skew.")

# Cache data to help with Yahoo Finance's rate limits
st.cache_data(ttl=3600)
def cached_expiries(ticker: str):
    return get_expiries(ticker)

@st.cache_data(ttl=900)
def cached_option_chain(ticker: str, expiry: str):
    return get_option_chain(ticker=ticker, expiry=expiry)

@st.cache_data(ttl=3600)
def cached_risk_free_rate(T: float):
    return get_risk_free_rate(T)

@st.cache_data(ttl=900)
def cached_iv_chain(ticker: str, expiry: str, r: float, max_bid_ask_pct: float, min_open_interest: int):

    # Retrieve the option chain
    chain = cached_option_chain(ticker=ticker, expiry=expiry)

    # To check whether there are stale/unavailable options to warn the user about
    raw_contracts = len(chain)

    zero_quotes = ((chain["bid"] == 0) & (chain["ask"] == 0)).sum()

    active_quotes = raw_contracts - zero_quotes

    zero_quotes_pct = (
        zero_quotes / raw_contracts
        if raw_contracts > 0
        else 0
    )

    quote_stats = {
        "raw_contracts": raw_contracts,
        "active_quotes": active_quotes,
        "zero_quotes": zero_quotes,
        "zero_quote_pct": zero_quotes_pct
    }

    # Clean the option chain and calculate the IVs

    cleaned_chain = clean_option_chain(chain, max_bid_ask_pct=max_bid_ask_pct, min_open_interest=min_open_interest)

    iv_chain = add_calculated_iv(options=cleaned_chain, r=r, initial_vol=0.25)

    # Remove non-solved IVs
    iv_chain = iv_chain.dropna(subset=["calculated_iv"])

    iv_chain = iv_chain[(iv_chain["calculated_iv"] > 0) & (iv_chain["calculated_iv"] < 5.0)].reset_index(drop=True)

    return iv_chain, quote_stats

st.subheader("Option Chain")

# Ticker selection
c1,c2 = st.columns(2)
with c1:
    ticker = st.text_input("Ticker",
                       value="AAPL",
                       help="Underlying ticker symbol."
                       ).strip().upper()

if not ticker:
    st.info("Enter a ticker to begin.")
    st.stop()

try:
    expiries = cached_expiries(ticker)
except Exception as e:
    st.error(f"Could not retrieve option expirations for {ticker}: {e}")
    st.stop()

# Expiry selection
with c2:
    expiry = st.selectbox(
        "Expiration",
        options=expiries,
        help="Available option expiration dates returned by Yahoo Finance."
    )

# Data cleaning controls
with st.expander("Quality Filters"):
    c1,c2 = st.columns(2)

    with c1:
        max_spread_pct = st.slider(
            "Maximum bid-ask spread (% of mid)",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            help="Contracts with wider relative bid-ask spreads are excluded from IV analysis."
        )

    with c2:
        min_open_interest = st.number_input(
            "Minimum open interest",
            min_value=0,
            value=1,
            step=1,
            help="Minimum number of outstanding contracts required for inclusion."
        )

max_bid_ask_pct = max_spread_pct / 100

# Retrieve maturity and risk-free rate
try:
    T = time_to_expiry(expiry)
    r = cached_risk_free_rate(T)
except Exception as e:
    st.error(f"Could not determine maturity/risk-free rate: {e}")
    st.stop()

# Create IV chain
try:
    iv_chain, quote_stats = cached_iv_chain(ticker=ticker,
                               expiry=expiry,
                               r=r,
                               max_bid_ask_pct=max_bid_ask_pct,
                               min_open_interest=min_open_interest)
except Exception as e:
    st.error(f"Could not build implied-volatility chain: {e}")
    st.stop()

# Warning of stale/unavailable option quotes
if quote_stats["zero_quote_pct"] > 0.50:
    st.warning(f"{quote_stats['zero_quote_pct']:.0%} of listed contracts currently have bid = 0 and ask = 0. Option quotes may be stale or unavailable outside the underlying market's regular trading hours.")
    st.caption(f"Listed contracts: {quote_stats['raw_contracts']}\n"
               f"Active quotes: {quote_stats['active_quotes']}\n"
               f"Zero bid/ask: {quote_stats['zero_quotes']}")

if iv_chain.empty:
    st.warning("No usable option contracts remain after filtering.")
    st.stop()

# Summary of market info
spot = float(iv_chain["spot"].iloc[0])

st.subheader("Market Overview")
c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric(
        "spot",
        f"${spot:,.2f}"
    )

with c2:
    st.metric("Expiration", expiry)

with c3:
    st.metric(
        "Time to Expiry",
        f"{T:.3f} years"
    )

with c4:
    st.metric(
        "Risk-free Rate",
        f"{r:.2%}"
    )
# Skew analysis
try:
    skew = calculate_skew_metrics(iv_chain)
except Exception as e:
    st.error(f"Could not calculate skew metrics: {e}")
    st.stop()

st.subheader("Volatility Skew")
c1,c2,c3 = st.columns(3)

with c1:
    st.metric(
        "ATM IV",
        f"{skew['ATM IV']:.2%}",
        help="Calculated implied volatility nearest 100% moneyness (K / S = 1)."
    )

with c2:
    st.metric(
        "Downside Skew",
        f"{skew['Downside Skew'] * 100:+.2f} vol pts",
        help="IV near 90% moneyness minus ATM IV. Positive values indicate richer downside volatility."
    )

with c3:
    st.metric(
        "Upside Skew",
        f"{skew['Upside Skew'] * 100:+.2f} vol pts",
        help="IV near 110% moneyness minus ATM IV."
    )

# Smile display
st.subheader("Implied Volatility Smile")
c1,c2 = st.columns(2)

with c1:
    x_axis = st.radio(
        "Horizontal Axis",
        options=["Moneyness", "Strike"],
        horizontal=True
    )

with c2:
    option_types = st.multiselect(
        "Option Types",
        options=["call", "put"],
        default=["call", "put"]
    )

# Keep underlying IV dataset intact and filter only what we display
plot_df = iv_chain[(iv_chain["moneyness"] >= 0.90) & (iv_chain["moneyness"] <= 1.10)].copy()
plot_df = plot_df[plot_df["otype"].isin(option_types)]

if plot_df.empty:
    st.warning("No contracts available for the selected display filters.")
else:
    plot_df["IV (%)"] = (plot_df["calculated_iv"] * 100)

    if x_axis == "Moneyness":
        x_col = "moneyness"
        x_label = "Moneyness (K / S)"
    else:
        x_col = "strike"
        x_label = "Strike"

    plot_df = plot_df.sort_values(["otype", x_col])

    smile_fig = px.line(
        plot_df,
        x=x_col,
        y="IV (%)",
        color="otype",
        markers=True,
        labels={
            x_col: x_label,
            "otype": "Option Type",
            "IV (%)": "Implied Volatility (%)"
        },
        title=f"Implied Volatility Smile - {ticker} {expiry}",
        hover_data={
            "strike": ":.2f",
            "spot": ":.2f",
            "mid": ":.2f",
            "moneyness": ":.3f",
            "IV (%)": ":.2f",
            "openInterest": True
        }
    )

    if x_axis == "Moneyness":
        smile_fig.add_vline(
            x=1.0,
            line_dash="dash",
            annotation_text="ATM"
        )
    else:
        smile_fig.add_vline(
            x=spot,
            line_dash="dash",
            annotation_text="Spot"
        )

    smile_fig.update_layout(height=550, legend_title_text="Option Type")

    st.plotly_chart(smile_fig, width="stretch")

# Calculation Details
with st.expander("Methodology & Details"):
    st.markdown(
        """
        **Dividends**
        
        The current Black Scholes implementation in this dashboard does not yet include a dividend
        yield parameter. The model therefore assumes a non-dividend paying underlying.
        
        For dividend-paying equities, this may create differences between calculated IV and market-reported IV. 
        
        Support for continuous dividend yield 'q' is planned as a future feature for this dashboard. 
        
        ---
        
        **Market Price**
        
        The implied volatility calculation uses the option's bid-ask midpoint: 
        
        mid = (bid + ask) / 2
        
        ---
        
        **Calculated IV**
        
        The dashboard solves for volatility using the Newton-Raphson method such that
        the Black Scholes theoretical option value matches the observed midpoint.
        
        ---
        
        **Moneyness**
        
        K / S
        
        - below 1: strike below spot
        - around 1: at-the-money
        - above 1: strike above spot
        
        The smile plot has a moneyness range of between 0.90 and 1.10 set for its display.
        
        ---
        
        **Skew**
        
        Downside and upside skew are measured relative to the calculated ATM implied volatility. 
        """
    )