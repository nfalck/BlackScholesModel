import streamlit as st
from blackscholes import BlackScholes
from market_data import get_underlying_price, get_risk_free_rate
import numpy as np
import matplotlib.pyplot as plt
from implied_vol import implied_vol_newton

st.set_page_config(page_title="Black Scholes Model", layout="wide")
st.title("Black Scholes Model")

# CSS for the Call and Put Values
st.markdown(
    """
    <style>
    .value-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.3rem;
        font-weight: 600;
    }
    .strike-card { background-color: #f0f0f0; color: #000; }
    .call-card   { background-color: #90ee90; color: #000; } /* light green */
    .put-card    { background-color: #ffcccb; color: #000; } /* light red */
    .value-label { font-size: 0.9rem; margin-bottom: 0.3rem; }
    .value-num   { font-size: 1.4rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar for User Inputs
with st.sidebar:
    st.header("Mode")
    advanced = st.toggle("Advanced Mode (manual S, T)", value=False)
    manual_r = st.toggle("Manually input risk-free rate", value=False)

    st.header("Inputs")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    expiry = st.text_input("Expiry (YYYY-MM-DD)", "2027-12-19").strip()
    K = st.number_input("Strike K", value=200.0, min_value=0.01, step=1.0, format="%.2f")
    vol_guess = st.number_input("Volatility σ (annual, decimal)", value=0.25, min_value=0.0001, step=0.01, format="%.4f")

    # Ability to manually input S and T if advanced mode is chosen
    if advanced:
        st.divider()
        S_manual = st.number_input("Underlying Price", value=200.0, min_value=0.0001, step=0.1, format="%.2f")
        T_manual = st.number_input("Time to expiry T (years)", value=0.50, min_value=1e-9, step=0.01,
                                   format="%.6f")

    # Ability to manually input the risk-free rate if chosen
    if manual_r:
        r_override = st.number_input("Risk-free rate r (annual, decimal, manual)", value=0.02, step=0.001, format="%.6f")

# Black-Scholes Initialization & Creation of Needed Variables for Calculation
try:
    bs = BlackScholes(ticker=ticker, expiry=expiry)
    if advanced:
        S = float(S_manual)
        T = max(1e-12, float(T_manual)) # to avoid div by 0
        if manual_r:
            r = float(r_override)
        else:
            r = get_risk_free_rate(T)
    else:
        T = bs.time_to_expiration()
        S = get_underlying_price(ticker=ticker)
        if manual_r:
            r = float(r_override)
        else:
            r = get_risk_free_rate(T)
except Exception as e:
    st.error(f"Setup error: {e}")
    st.stop()

# Visualization of Inputs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ticker", ticker)
c2.metric("Underlying Price (S)", f"{S:.4f}")
c3.metric("T (years)", f"{T:.6f}")
c4.metric("r (annual)", f"{r:.4%}")
c5.metric("Volatility", f"{vol_guess:.4f}")

st.write("---")
# Black-Scholes Calculation
try:
    vol = float(vol_guess)
    out = bs.quote(S=S, T=T, r=r, K=K, vol=vol)
except Exception as e:
    st.error(f"Pricing error: {e}")
    st.stop()

# Visualization of the Results
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f"""
        <div class="value-card strike-card">
            <div class="value-label">Strike (K)</div>
            <div class="value-num">{K:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
            <div class="value-card call-card">
                <div class="value-label">CALL Value</div>
                <div class="value-num">${out['prices']['call']:.2f}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
            <div class="value-card put-card">
                <div class="value-label">PUT Value</div>
                <div class="value-num">${out['prices']['put']:.2f}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

# Greeks Visualization
st.subheader("Greeks")
reporting = out["reporting_greeks"]
contract_multiplier = 100

for greek, symbol, unit in [
    ("Delta", "$\\Delta$", "per $1 underlying move"),
    ("Gamma", "$\\Gamma$", "Δ change per $1 move"),
    ("Vega", "$\\nu$", "per +1 vol point"),
    ("Theta", "$\\Theta$", "per day"),
    ("Rho", "$\\rho$", "per +1% rate move")
]:
    call_value = reporting["call"][greek]
    put_value = reporting["put"][greek]

    # captions for greek values per contract
    def contract_caption(greek: str, value: float, multiplier: int = 100) -> str:
        contract_value = value * multiplier

        if greek == "Delta":
            return (
                f"≈ \\${contract_value:,.2f} per contract "
                f"for a \\$1 underlying move"
            )

        elif greek == "Gamma":
            return (
                f"≈ {contract_value:.4f} "
                f"Δ per contract"
            )

        elif greek == "Vega":
            return (
                f"≈ ${contract_value:,.2f} per contract "
                f"for +1 vol point"
            )

        elif greek == "Theta":
            return (
                f"≈ ${contract_value:,.2f} per contract/day"
            )

        elif greek == "Rho":
            return (
                f"≈ ${contract_value:,.2f} per contract "
                f"for +1% rates"
            )

    c1, c2, c3 = st.columns([1,1.5,1.5])

    with c1:
        st.markdown(
            f"""
            **{greek}**
            {symbol}
            <small>{unit}</small>
            """, unsafe_allow_html=True
        )

    with c2:
        st.metric(
            "Call",
            f"{call_value:.4f}"
        )

        st.caption(
            contract_caption(
                greek,
                call_value,
                contract_multiplier
            )
        )

    with c3:
        st.metric(
            "Put",
            f"{put_value:.4f}"
        )

        st.caption(
            contract_caption(
                greek,
                put_value,
                contract_multiplier
            )
        )
st.write("---")
# Visualization of Inputs for Implied Volatility Calculation
st.header("Implied Volatility (Newton Raphson Method)")

c1_iv, c2_iv, c3_iv = st.columns(3)
market_call_price = float(c1_iv.number_input("Market Call price", value=0.0, min_value=0.0, step=0.05, format="%.4f"))
market_put_price = float(c2_iv.number_input("Market Put price",  value=0.0, min_value=0.0, step=0.05, format="%.4f"))
iv_tol = float(c3_iv.number_input("Tolerance", value=1e-8, min_value=1e-10, format="%.1e"))

# Initialize
iv_call = None
iv_put = None

# Calculate IV when market price is put in by the user
if market_call_price > 0:
    try:
        iv_call = implied_vol_newton(bs=bs, otype="call", market_price=market_call_price, S=S, K=K, T=T, r=r,
                                     initial_vol=float(vol_guess), tol=iv_tol)
    except Exception as e:
        st.error(f"Call IV calculation failed: {e}")
if market_put_price > 0:
    try:
        iv_put = implied_vol_newton(bs=bs, otype="put", market_price=market_put_price, S=S, K=K, T=T, r=r,
                                     initial_vol=float(vol_guess), tol=iv_tol)
    except Exception as e:
        st.error(f"Put IV calculation failed: {e}")

# Visualization of the Results
c1_iv_res, c2_iv_res, c3_iv_res = st.columns(3)
c1_iv_res.metric("Your σ (input)", f"{float(vol_guess):.4f}")
c2_iv_res.metric("Implied σ (Call)", f"{iv_call:.4f}" if iv_call is not None else "—")
c3_iv_res.metric("Implied σ (Put)",  f"{iv_put:.4f}" if iv_put is not None else "—")

# Plotting the Results for Further Visualization
def plot_newton(if_call: bool, market_price: float, iv_solved: float, title_suffix: str):
    """
    Plots Call/Put price vs Implied Volatility (IV) showing where user-input volatility is compared to IV
    Args:
    if_call (bool): if the option is call (True) or put (False)
    market_price (float): user-input of market price
    iv_solved (float): the solved IV from implied_vol_newton()
    title_suffix (str): suffix to add in plot depending if option is call or put
    """
    # Creation of Several Volatilities to Extend the Curve
    s_guess = max([x for x in [float(vol), iv_solved or 0] if x is not None] + [0.25])
    sigma_min = 0.01 # start at 1%
    sigma_max = max(2.0 * vol_guess, (iv_solved or 0) * 1.5, 1.0) # largest of user's guess or 1.5 x IV to extend the curve
    sigma_max = min(sigma_max, 5.0) # cap at 500%
    sigmas = np.linspace(sigma_min, sigma_max, 240) # array of evenly spaced numbers between min and max vol, 240 values

    # Calculate Prices for Various Volatilities and Plot BS Curve
    if if_call:
        curve = np.array([bs.quote(S=S, T=T, r=r, K=K, vol=s)["prices"]["call"] for s in sigmas])
    else:
        curve = np.array([bs.quote(S=S, T=T, r=r, K=K, vol=s)["prices"]["put"] for s in sigmas])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(sigmas * 100.0, curve, label="BS Price")  # x-axis in %

    # Horizontal line for market price (blue)
    if market_price > 0:
        ax.axhline(market_price, linestyle="--", label=f"Market Price = {market_price:.4f}")
    if iv_solved is not None:
        # Vertical line for IV (green)
        ax.axvline(iv_solved * 100.0, linestyle="--", color="green", label=f"Implied Vol = {iv_solved:.4f}")
        # Dot at where IV and market price meets (red)
        if if_call:
            ax.scatter([iv_solved * 100.0], [bs.quote(S=S, T=T, r=r, K=K, vol=iv_solved)["prices"]["call"]], color="red", zorder=3, label="Calc. Price")
        else:
            ax.scatter([iv_solved * 100.0], [bs.quote(S=S, T=T, r=r, K=K, vol=iv_solved)["prices"]["put"]], color="red", zorder=3, label="Calc. Price")
    # Also show vertical line of user input of volatility as a reference
    ax.axvline(float(vol) * 100.0, linestyle=":", label=f"Your Vol = {float(vol):.4f}")

    ax.set_title(f"Price vs Implied Volatility ({title_suffix})")
    ax.set_xlabel("Implied Volatility (%)")
    ax.set_ylabel(("Call" if if_call else "Put") + " Price")
    ax.legend()
    st.pyplot(fig, clear_figure=True)

# To Show on Streamlit
call_plot, put_plot = st.columns(2)
if market_call_price > 0:
    with call_plot:
        plot_newton(True, market_call_price, iv_call, "CALL")
if market_put_price > 0:
    with put_plot:
        plot_newton(False, market_put_price, iv_put, "PUT")

