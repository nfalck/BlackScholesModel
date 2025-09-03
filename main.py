import streamlit as st
from blackscholes import BlackScholes

st.set_page_config(page_title="Black Scholes Model", layout="wide")
st.title("Black Scholes Model")

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

with st.sidebar:
    st.header("Mode")
    advanced = st.toggle("Advanced Mode (manual S, T, r)", value=False)
    manual_r = st.toggle("Manually input risk-free rate", value=False)

    st.header("Inputs")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    expiry = st.text_input("Expiry (YYYY-MM-DD)", "2025-12-19").strip()
    K_single = st.number_input("Strike K", value=200.0, min_value=0.01, step=1.0, format="%.2f")
    vol = st.number_input("Volatility σ (annual, decimal)", value=0.25, min_value=0.0001, step=0.01, format="%.4f")

    if advanced:
        st.divider()
        S_manual = st.number_input("Underlying Price", value=200.0, min_value=0.0001, step=0.1, format="%.2f")
        T_manual = st.number_input("Time to expiry T (years)", value=0.50, min_value=1e-9, step=0.01,
                                   format="%.6f")

    if manual_r:
        r_override = st.number_input("Risk-free rate r (annual, decimal, manual)", value=0.02, step=0.001, format="%.6f")

try:
    bs = BlackScholes(ticker=ticker, expiry=expiry)
    if advanced:
        S = float(S_manual)
        T = max(1e-12, float(T_manual))
        if manual_r:
            r = float(r_override)
        else:
            r = bs.get_risk_free_rate(T)
    else:
        if manual_r:
            r = float(r_override)
        else:
            T = bs.time_to_expiration()
            r = bs.get_risk_free_rate(T)
        S = bs.get_underlying_price(ticker=ticker)
        T = bs.time_to_expiration()
except Exception as e:
    st.error(f"Setup error: {e}")
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ticker", ticker)
c2.metric("Underlying Price (S)", f"{S:.4f}")
c3.metric("T (years)", f"{T:.6f}")
c4.metric("r (annual)", f"{r:.4%}")
c5.metric("Volatility", f"{vol:.4f}")

st.write("---")

st.header("Single Strike")
try:
    vol = float(vol)
    out_single = bs.quote(S=S, T=T, r=r, K=K_single, vol=vol)
except Exception as e:
    st.error(f"Pricing error (single strike): {e}")
    st.stop()

c1, c2, c3 = st.columns(3)

# c1.metric("Strike (K)", f"{K_single:.4f}")
with c1:
    st.markdown(
        f"""
        <div class="value-card strike-card">
            <div class="value-label">Strike (K)</div>
            <div class="value-num">{K_single:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

#c2.metric("BS Call", f"{out_single['prices']['call']:.4f}")
with c2:
    st.markdown(
        f"""
            <div class="value-card call-card">
                <div class="value-label">CALL Value</div>
                <div class="value-num">${out_single['prices']['call']:.4f}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

# c3.metric("BS Put",  f"{out_single['prices']['put']:.4f}")
with c3:
    st.markdown(
        f"""
            <div class="value-card put-card">
                <div class="value-label">PUT Value</div>
                <div class="value-num">${out_single['prices']['put']:.4f}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

st.subheader("Greeks at Single Strike")
for greek, symbol in [
    ("Delta", "$\\Delta$"),
    ("Gamma", "$\\Gamma$"),
    ("Vega", "$\\nu$"),
    ("Theta", "$\\Theta$"),
    ("Rho", "$\\rho$")
]:
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**{greek}**  \n{symbol}")
    c2.metric("Call", f"{out_single['greeks']['call'][greek]:.6f}")
    c3.metric("Put",  f"{out_single['greeks']['put'][greek]:.6f}")

