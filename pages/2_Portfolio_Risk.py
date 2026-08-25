import streamlit as st
import pandas as pd
from option_portfolio import OptionPortfolio
from option_position import OptionPosition
from scenario import run_scenario
from pnl_approximation import greek_pnl_approximation
from market_data import get_underlying_price, get_risk_free_rate
from option_chain import time_to_expiry, get_option_chain
from market_iv import create_market_vols
import plotly.graph_objects as go
import numpy as np
import plotly.express as px

@st.cache_data(ttl=900)
def cached_spot_price(ticker: str):
    return get_underlying_price(ticker)

@st.cache_data(ttl=3600)
def cached_risk_free_rate(T: float):
    return get_risk_free_rate(T)

@st.cache_data(ttl=900)
def cached_option_chain(ticker: str, expiry: str):
    return get_option_chain(ticker=ticker, expiry=expiry)

def format_dollar(value: float) -> str:
    if value < 0:
        return f"-${abs(value):,.2f}"
    return f"${value:,.2f}"

def portfolio_from_dataframe(df: pd.DataFrame) -> OptionPortfolio:
    positions = []
    for i, row in df.iterrows():
        position = OptionPosition(
            ticker=str(row["ticker"]),
            otype=str(row["otype"]),
            strike=float(row["strike"]),
            expiry=str(row["expiry"]),
            quantity=int(row["quantity"]),
            multiplier=int(row["multiplier"])
        )

        positions.append(position)
    return OptionPortfolio(positions)

default_portfolio = pd.DataFrame(
    [
        {
            "ticker": "AAPL",
            "otype": "call",
            "strike": 200.0,
            "expiry": "2027-01-15",
            "quantity": 10,
            "multiplier": 100
        },
        {
            "ticker": "AAPL",
            "otype": "put",
            "strike": 250.0,
            "expiry": "2027-01-15",
            "quantity": -5,
            "multiplier": 100
        }
    ]
)

st.set_page_config(page_title="Options Portfolio Risk", layout="wide")
st.title("Options Portfolio Risk")
st.caption("Portfolio-level valuation, Greeks and scenario analysis.")

st.subheader("Portfolio Input")

input_method = st.radio(
    "Portfolio Source",
    ["Build Portfolio", "Upload CSV"],
    horizontal=True
)

portfolio = None

if input_method == "Build Portfolio":
    edited_df = st.data_editor(
        default_portfolio,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "ticker": st.column_config.TextColumn(
                "Ticker",
                help="Underlying ticker symbol."
            ),
            "otype": st.column_config.SelectboxColumn(
                "Type",
                options=["call", "put"],
                help="Option type."
            ),
            "strike": st.column_config.NumberColumn(
                "Strike",
                min_value=0.01,
                format="%.2f"
            ),
            "expiry": st.column_config.TextColumn(
                "Expiry",
                help="Expiration date in YYYY-MM-DD format."
            ),
            "quantity": st.column_config.NumberColumn(
                "Quantity",
                step=1,
                help=(
                    "Positive = long contracts."
                    "Negative = short contracts."
                )
            ),
            "multiplier": st.column_config.NumberColumn(
                "Multiplier",
                min_value=1,
                default=100,
                step=1,
                help="Usually 100 for US equity options."
            )
        }
    )

    try:
        portfolio = portfolio_from_dataframe(edited_df)
    except Exception as e:
        st.error(f"Invalid portfolio: {e}")
        st.stop()
else:
    uploaded_file = st.file_uploader("Upload Portfolio CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            portfolio = OptionPortfolio.from_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not load portfolio: {e}")
            st.stop()

if portfolio is not None:

    tickers = sorted({position.ticker for position in portfolio.positions})

    spot_prices = {}

    for ticker in tickers:
        try:
            spot_prices[ticker] = cached_spot_price(ticker)
        except Exception as e:
            st.error(f"Could not fetch market price for {ticker}: {e}")
            st.stop()

    expiries = sorted({
        position.expiry
        for position in portfolio.positions
    })

    rates_by_expiry = {}

    for expiry in expiries:

        T = time_to_expiry(expiry)

        rates_by_expiry[expiry] = cached_risk_free_rate(T)

    try:
        vols_by_contract = create_market_vols(portfolio=portfolio, rates_by_expiry=rates_by_expiry, chain_fetcher=cached_option_chain)
    except Exception as e:
        st.error(f"Could not retrieve market implied volatility: {e}")
        st.stop()

    st.subheader("Market Data")

    cols = st.columns(len(tickers))
    for col, ticker in zip(cols, tickers):
        with col:
            st.metric(
                f"{ticker} Spot",
                f"${spot_prices[ticker]:,.2f}"
            )

    if portfolio is not None:
        try:
            evaluated = portfolio.evaluate(spot_prices=spot_prices, rates_by_expiry=rates_by_expiry, vols_by_contract=vols_by_contract)

            summary = portfolio.risk_summary(evaluated)

        except Exception as e:
            st.error(f"Error loading portfolio: {e}")
            st.stop()

    st.subheader("Portfolio Risk")
    c1,c2,c3 = st.columns(3)

    with c1:
        st.metric(
            "Net Market Value",
            format_dollar(summary["Position Value"])
        )

    with c2:
        st.metric(
            "Delta",
            f"{summary['Delta']:,.2f}",
            help=("Approximate portfolio P&L for a $1 increase.")
        )

    with c3:
        st.metric(
            "Gamma",
            f"{summary['Gamma']:,.4f}"
        )

    c4,c5,c6 = st.columns(3)

    with c4:
        st.metric(
            "Vega (per +1 vol point)",
            format_dollar(summary["Vega"]),
            help=("Approximate portfolio P&L when implied volatility increases by 1 vol point.")
        )

    with c5:
        st.metric(
            "Theta (per day)",
            format_dollar(summary["Theta"]),
            help=("Approximate portfolio P&L from one calendar day passing.")
        )

    with c6:
        st.metric(
            "Rho (per +100 bps)",
            format_dollar(summary["Rho"]),
            help=("Approximate portfolio P&L if the risk-free rate increases by 100 bps.")
        )

    st.subheader("Position Breakdown")

    df = pd.DataFrame(evaluated)

    st.dataframe(
        df,
        width="stretch",
        hide_index=True
    )

    st.subheader("Scenario Analysis")

    c1,c2,c3,c4 = st.columns(4)

    with c1:
        spot_shock_pct = st.number_input(
            "Spot Shock (%)",
            value=-10.0,
            step=1.0,
            help=("Percentage shock applied to the underlying price.")
        )

    with c2:
        vol_shock_points = st.number_input(
            "Vol Shock (vol points)",
            value=5.0,
            step=1.0,
            help=("Absolute change in implied volatility.")
        )

    with c3:
        rate_shock_bps = st.number_input(
            "Rate Shock (bps)",
            value=100.0,
            step=25.0,
            help=("Interest rate shock in basis points.")
        )

    with c4:
        days_forward = st.number_input(
            "Days Forward",
            min_value=0,
            value=5,
            step=1,
            help=("Number of calendar days to roll the portfolio forward.")
        )

    spot_change = spot_shock_pct / 100
    vol_change = vol_shock_points / 100
    rate_change = rate_shock_bps / 10000

    full_repricing = run_scenario(
        portfolio=portfolio,
        spot_prices=spot_prices,
        rates_by_expiry=rates_by_expiry,
        vols_by_contract=vols_by_contract,
        spot_change=spot_change,
        vol_change=vol_change,
        rate_change=rate_change,
        days_forward=days_forward
    )

    approximation = greek_pnl_approximation(
        evaluated_positions=evaluated,
        spot_prices=spot_prices,
        spot_change=spot_change,
        vol_change=vol_change,
        rate_change=rate_change,
        days_forward=days_forward
    )

    absolute_error = (approximation["Total PnL"] - full_repricing["PnL"])

    if full_repricing["PnL"] != 0:
        percentage_error = (abs(absolute_error)/abs(full_repricing["PnL"])) * 100
    else:
        percentage_error = 0.0

    st.subheader("Scenario Results")

    c1,c2,c3 = st.columns(3)

    with c1:
        st.metric(
            "Full Repricing P&L",
            format_dollar(full_repricing["PnL"])
        )

    with c2:
        st.metric(
            "Greek Approximation P&L",
            format_dollar(approximation["Total PnL"])
        )

    with c3:
        st.metric(
            "Approximation Error",
            f"{percentage_error:.2f}%"
        )

    st.divider()

    st.caption("Stressed Market Conditions")

    st.caption("Underlying Prices")

    spot_cols = st.columns(len(spot_prices))

    for col, ticker in zip(spot_cols, spot_prices):
        base_spot = full_repricing["Base Spots"][ticker]
        stressed_spot = full_repricing["Stressed Spots"][ticker]

        with col:
            st.metric(
                f"{ticker} Spot",
                f"${stressed_spot:,.2f}",
                delta=f"{spot_shock_pct:+.1f}%",
                help=(
                    f"Base spot: ${base_spot:,.2f}. "
                    f"Scenario applies a {spot_shock_pct:+.1f}% shock."
                )
            )

    c1,c2,c3 = st.columns(3)

    c1.metric(
        "Volatility shock",
        f"{vol_shock_points:+.1f} vol pts",
        help = (f"The shock is applied to every contract's market implied volatility.")
    )

    c2.metric(
        "Rate Curve Shock",
        f"{rate_shock_bps:+.0f} bps",
        delta_color="off",
        help=(
            "The shock is applied to every maturity-specific risk-free rate in the portfolio."
        )
    )

    c3.metric(
        "Time Forward",
        f"{days_forward} days",
        help=("Number of calendar days moved forward in the scenario.")
    )

    stressed_rates = full_repricing["Stressed Rates"]
    base_rates = full_repricing["Base Rates"]

    with st.expander("Risk-Free Rates by Expiry"):

        for expiry in base_rates:
            st.write(
                f"**{expiry}**: "
                f"{base_rates[expiry]:.2%} → "
                f"{stressed_rates[expiry]:.2%}"
    )

    with st.expander("Implied Volatility by Contract"):
        base_vols = full_repricing["Base Vols"]
        stressed_vols = full_repricing["Stressed Vols"]

        for position in portfolio.positions:
            contract = (
                position.ticker,
                position.otype,
                float(position.strike),
                position.expiry
            )

            if contract not in base_vols:
                continue

            st.write(
                f"**{position.ticker} "
                f"{position.strike:g} "
                f"{position.otype} | "
                f"{position.expiry}**: "
                f"{base_vols[contract]:.2%} → "
                f"{stressed_vols[contract]:.2%}"
            )

    st.divider()

    st.subheader("Greek P&L Contribution")

    pnl_breakdown = pd.DataFrame({
        "Risk Factor": [
            "Delta",
            "Gamma",
            "Vega",
            "Theta",
            "Rho"
        ],
        "PnL": [
            approximation["Delta PnL"],
            approximation["Gamma PnL"],
            approximation["Vega PnL"],
            approximation["Theta PnL"],
            approximation["Rho PnL"]
        ]
    })

    pnl_display = pnl_breakdown.copy()
    pnl_display["PnL"] = pnl_display["PnL"].apply(format_dollar)

    st.dataframe(
        pnl_display,
        hide_index=True,
        width="stretch"
    )

    risk_factors = pnl_breakdown["Risk Factor"].tolist()
    pnl_values = pnl_breakdown["PnL"].tolist()

    bar_colors = [
        "#2ECC71" if value >= 0 else "#E74C3C"
        for value in pnl_values
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=risk_factors,
            y=pnl_values,
            marker_color=bar_colors,
            text=[
                format_dollar(value)
                for value in pnl_values
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "P&L Contribution: $%{y:,.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title="Greek P&L Attribution",
        xaxis_title="Risk Factor",
        yaxis_title = "P&L ($)",
        showlegend=False,
        height=500
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    non_delta = pnl_breakdown[
        pnl_breakdown["Risk Factor"] != "Delta"
    ]

    non_delta_values = non_delta["PnL"].tolist()

    fig_non_delta = go.Figure()

    fig_non_delta.add_trace(
        go.Bar(
            x=non_delta["Risk Factor"],
            y=non_delta_values,
            marker_color=[
                "#2ECC71" if value >= 0 else "#E74C3C"
                for value in non_delta_values
            ],
            text=[
                format_dollar(value)
                for value in non_delta_values
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "P&L Contribution: $%{y:,.2f}"
                "<extra></extra>"
            )
        )
    )

    fig_non_delta.update_layout(
        title="Non-Delta P&L Attribution",
        yaxis_title="P&L ($)",
        showlegend=False,
        height=500
    )

    st.plotly_chart(
        fig_non_delta,
        width="stretch"
    )

    st.divider()

    st.subheader("Spot x Volatility Stress Map")

    st.caption(
        "Full repricing portfolio P&L across combinations of spot and implied-volatility shocks."
    )

    spot_shocks = np.arange(-20, 21, 5)
    vol_shocks = np.arange(-10,16,5)

    heatmap_values = []

    for vol_shock in vol_shocks:
        row = []

        for spot_shock in spot_shocks:

            invalid_vol = any(base_vol + (vol_shock/100) <=0 for base_vol in vols_by_contract.values())
            if invalid_vol:
                row.append(np.nan)
                continue

            result = run_scenario(portfolio=portfolio,
                                  spot_prices=spot_prices,
                                  rates_by_expiry=rates_by_expiry,
                                  vols_by_contract=vols_by_contract,
                                  spot_change=spot_shock/100,
                                  vol_change=vol_shock/100)

            row.append(result["PnL"])
        heatmap_values.append(row)

    fig_heatmap = px.imshow(
        heatmap_values,
        x=[f"{shock:+.0f}%" for shock in spot_shocks],
        y=[f"{shock:+.0f} pts" for shock in vol_shocks],
        labels={
            "x": "Spot Shock",
            "y": "Volatility Shock",
            "color": "Portfolio P&L"
        },
        text_auto=".0f",
        aspect="auto",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0
    )

    fig_heatmap.update_traces(
        hovertemplate=(
            "<b>Spot Shock:</b> %{x}<br>"
            "<b>Volatility Shock:</b> %{y}<br>"
            "<b>Portfolio P&L:</b> $%{z:,.2f}"
            "<extra></extra>"
        )
    )

    fig_heatmap.update_layout(
        height=550,
        title={
            "text": "Portfolio Stress Surface",
            "x": 0.5,
            "xanchor": "center"
        },
        xaxis_title="Spot Shock",
        yaxis_title="Volatility Shock",
        coloraxis_colorbar=dict(title="P&L ($)")
    )

    st.plotly_chart(fig_heatmap, width="stretch")