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
    K = st.number_input("Strike K", value=200.0, min_value=0.01, step=1.0, format="%.2f")
    vol_guess = st.number_input("Volatility σ (annual, decimal)", value=0.25, min_value=0.0001, step=0.01, format="%.4f")

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
c5.metric("Volatility", f"{vol_guess:.4f}")

st.write("---")
try:
    vol = float(vol_guess)
    out_single = bs.quote(S=S, T=T, r=r, K=K, vol=vol)
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
            <div class="value-num">{K:.2f}</div>
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
                <div class="value-num">${out_single['prices']['call']:.2f}</div>
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
                <div class="value-num">${out_single['prices']['put']:.2f}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

st.subheader("Greeks")
for greek, symbol in [
    ("Delta", "$\\Delta$"),
    ("Gamma", "$\\Gamma$"),
    ("Vega", "$\\nu$"),
    ("Theta", "$\\Theta$"),
    ("Rho", "$\\rho$")
]:
    c1, c2, c3 = st.columns([1,1,1])
    c1.markdown(f"**{greek}**  \n{symbol}")
    c2.metric("Call", f"{out_single['greeks']['call'][greek]:.3f}")
    c3.metric("Put",  f"{out_single['greeks']['put'][greek]:.3f}")

st.write("---")
st.header("Implied Volatility (Newton Raphson Method)")

c1_iv, c2_iv, c3_iv = st.columns(3)
market_call_price = float(c1_iv.number_input("Market Call price", value=0.0, min_value=0.0, step=0.05, format="%.4f"))
market_put_price = float(c2_iv.number_input("Market Put price",  value=0.0, min_value=0.0, step=0.05, format="%.4f"))
iv_tol = float(c3_iv.number_input("Tolerance", value=1e-8, min_value=1e-10, format="%.1e"))

def implied_vol_newton(otype):
    max_iter = 100
    old_vol = vol_guess

    for i in range(max_iter):
        bs_results = bs.quote(S=S, T=T, r=r, K=K, vol=old_vol)
        if otype == "call":
            theoretical_price = bs_results["prices"]["call"]
            Cprime = bs_results["greeks"]["call"]["Vega"]
        else:
            theoretical_price = bs_results["prices"]["put"]
            Cprime = bs_results["greeks"]["put"]["Vega"]

        if otype == "call":
            C = theoretical_price - market_call_price
        else:
            C = theoretical_price - market_put_price

        new_vol = old_vol - (C/Cprime)
        new_bs_results = bs.quote(S=S, T=T, r=r, K=K, vol=new_vol)

        if otype == "call":
            if abs(old_vol - new_vol) < iv_tol or abs(new_bs_results["prices"]["call"] - market_call_price) < iv_tol:
                break
        else:
            if abs(old_vol - new_vol) < iv_tol or abs(new_bs_results["prices"]["put"] - market_put_price) < iv_tol:
                break

        old_vol = new_vol
    implied_vol = old_vol
    return implied_vol

iv_call = None
iv_put = None

if market_call_price > 0:
    iv_call = implied_vol_newton("call")
if market_put_price > 0:
    iv_put = implied_vol_newton("put")

c1_iv_res, c2_iv_res, c3_iv_res = st.columns(3)
c1_iv_res.metric("Your σ (input)", f"{float(vol_guess):.4f}")
c2_iv_res.metric("Implied σ (Call)", f"{iv_call:.4f}" if iv_call is not None else "—")
c3_iv_res.metric("Implied σ (Put)",  f"{iv_put:.4f}"  if iv_put  is not None else "—")

