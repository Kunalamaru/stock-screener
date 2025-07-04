import streamlit as st
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import requests

st.set_page_config(page_title="📈 3% Move Predictor + Options", layout="wide")

# Load NIFTY 100
@st.cache_data(ttl=86400)
def get_nifty_100_symbols():
    return [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "KOTAKBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "ASIANPAINT", "MARUTI",
        "SUNPHARMA", "BAJFINANCE", "BAJAJFINSV", "AXISBANK", "WIPRO",
        "TITAN", "ULTRACEMCO", "ONGC", "NTPC", "POWERGRID", "COALINDIA",
        "HCLTECH", "TECHM", "NESTLEIND", "TATAMOTORS", "TATASTEEL", "ADANIENT",
        "ADANIPORTS", "JSWSTEEL", "HDFCLIFE", "SBILIFE", "DIVISLAB", "CIPLA",
        "DRREDDY", "ICICIPRULI", "HINDALCO", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "GRASIM", "BRITANNIA", "M&M", "BPCL", "INDUSINDBK",
        "SHREECEM", "IOC", "UPL", "SIEMENS", "GAIL", "PIDILITIND", "AMBUJACEM",
        "DABUR", "BIOCON", "LUPIN", "TRENT", "COLPAL", "DMART", "TORNTPHARM"
    ]

# Fetch EOD data
def fetch_price_data(symbol):
    try:
        df = yf.download(symbol, period="10d", interval="1d", progress=False)
        return df if not df.empty else None
    except:
        return None

# Fetch option chain from NSE
def fetch_option_chain(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        response = session.get(url, headers=headers)
        data = response.json()
        return data.get("records", {}).get("data", [])
    except Exception as e:
        return []

# Parse option chain
def parse_oi_greeks(chain_data):
    calls, puts = [], []
    for entry in chain_data:
        ce = entry.get("CE")
        pe = entry.get("PE")
        if ce:
            calls.append({
                "Strike": ce["strikePrice"],
                "OI": ce.get("openInterest", 0),
                "Chg OI": ce.get("changeinOpenInterest", 0),
                "IV": ce.get("impliedVolatility", 0),
                "Delta": ce.get("greeks", {}).get("delta", "N/A")
            })
        if pe:
            puts.append({
                "Strike": pe["strikePrice"],
                "OI": pe.get("openInterest", 0),
                "Chg OI": pe.get("changeinOpenInterest", 0),
                "IV": pe.get("impliedVolatility", 0),
                "Delta": pe.get("greeks", {}).get("delta", "N/A")
            })
    return pd.DataFrame(calls), pd.DataFrame(puts)

# Analyze stock
def analyze_stock(df):
    if df is None or len(df) < 6:
        return None

    close = df["Close"].dropna()
    volume = df["Volume"].dropna()
    if len(close) < 6 or len(volume) < 6:
        return None

    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    ema5 = EMAIndicator(close, window=5).ema_indicator().iloc[-1]

    today_close = close.iloc[-1]
    prev_close = close.iloc[-2]
    prev_high = df["High"].iloc[-2]
    today_vol = volume.iloc[-1]
    avg_vol = volume[-6:-1].mean()

    # Conditions
    price_breakout = today_close > prev_high
    vol_spike = today_vol > 2 * avg_vol
    rsi_bullish = rsi > 55
    above_ema = today_close > ema5

    score = int(price_breakout) + int(vol_spike) + int(rsi_bullish) + int(above_ema)
    pct_change = round((today_close - prev_close) / prev_close * 100, 2)
    vol_ratio = round(today_vol / avg_vol, 2)

    return {
        "Last Price": round(today_close, 2),
        "% Change": pct_change,
        "Volume Spike": vol_ratio,
        "RSI": round(rsi, 2),
        "Score": score
    } if score >= 3 else None

# === Streamlit App ===
st.title("📊 NSE Screener — 3% Move Predictor + Option Chain")
st.caption("Filter: Volume > 2× avg, RSI > 55, Price > prev high & EMA5")

symbols = [s + ".NS" for s in get_nifty_100_symbols()]
results = []

progress = st.progress(0)
for i, symbol in enumerate(symbols[:50]):  # Limit for performance
    df = fetch_price_data(symbol)
    result = analyze_stock(df)
    if result:
        results.append({
            "Symbol": symbol.replace(".NS", ""),
            **result
        })
    progress.progress((i + 1) / 50)

if results:
    df_final = pd.DataFrame(results)
    df_final.sort_values(by=["Score", "% Change"], ascending=[False, False], inplace=True)
    st.success(f"✅ {len(df_final)} stocks found")
    st.dataframe(df_final, use_container_width=True)

    # Show Option Chain per stock
    st.markdown("## 🔍 Option Chain Snapshots")
    for row in df_final.itertuples(index=False):
        sym = row.Symbol
        st.markdown(f"### 📈 {sym} Options")
        chain_data = fetch_option_chain(sym)
        calls_df, puts_df = parse_oi_greeks(chain_data)
        st.markdown("**Call Options (Top 5 OI)**")
        st.dataframe(calls_df.sort_values("OI", ascending=False).head(5))
        st.markdown("**Put Options (Top 5 OI)**")
        st.dataframe(puts_df.sort_values("OI", ascending=False).head(5))
else:
    st.warning("🚫 No qualifying stocks found today.")
