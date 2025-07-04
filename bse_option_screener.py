import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from modules.option_chain import fetch_option_chain, parse_oi_greeks

st.set_page_config(page_title="📈 All-Stock Screener (NSE Live)", layout="wide")

REFRESH_INTERVAL = 5

@st.cache_data(ttl=3600)
def get_all_nse_stocks():
    url = "https://www1.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv"
    }
    try:
        df = pd.read_csv(url)
        symbols = df["SYMBOL"].dropna().unique()
        return [symbol.strip() + ".NS" for symbol in symbols]
    except Exception as e:
        st.error(f"❌ Failed to fetch NSE stock list: {e}")
        return []

def fetch_price_data(ticker):
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False)
        return data if not data.empty else None
    except:
        return None

def analyze_stock(df):
    if df is None or len(df) < 200:
        return False

    close = df["Close"]
    ma50 = close.rolling(window=50).mean()
    ma200 = close.rolling(window=200).mean()
    ema21 = EMAIndicator(close, window=21).ema_indicator()
    rsi = RSIIndicator(close, window=14).rsi()
    volume = df["Volume"]

    golden_cross = ma50.iloc[-1] > ma200.iloc[-1] and ma50.iloc[-2] <= ma200.iloc[-2]
    momentum = rsi.iloc[-1] > 50
    above_ema = close.iloc[-1] > ema21.iloc[-1]
    vol_spike = volume.iloc[-1] > volume.rolling(window=10).mean().iloc[-1] * 1.5

    if golden_cross and momentum and above_ema and vol_spike:
        return {
            "Last Price": close.iloc[-1],
            "RSI": round(rsi.iloc[-1], 2),
            "Vol Spike Ratio": round(volume.iloc[-1] / volume.rolling(10).mean().iloc[-1], 2)
        }
    else:
        return False

st.title("📊 NSE Live Stock Screener (Golden Cross + Momentum)")
st.caption("Now scanning all listed stocks from NSE live CSV")
st.markdown("🔁 Auto-refresh every 5 seconds...")

symbols = get_all_nse_stocks()
results = []

progress = st.progress(0)
for i, symbol in enumerate(symbols[:50]):  # For performance, limit to 50 at a time
    df = fetch_price_data(symbol)
    result = analyze_stock(df)
    if result:
        results.append({
            "Symbol": symbol.replace(".NS", ""),
            "Last Price": result["Last Price"],
            "RSI": result["RSI"],
            "Vol Spike": result["Vol Spike Ratio"]
        })
    progress.progress((i + 1) / 50)

if results:
    st.success(f"✅ Found {len(results)} bullish candidates!")
    df_results = pd.DataFrame(results).sort_values("Vol Spike", ascending=False)
    st.dataframe(df_results, use_container_width=True)
else:
    st.warning("🚫 No matches found with the current filter.")

# Optional: Still show option chain for INFY demo
st.markdown("### 🔍 Options Chain (INFY - demo)")
chain = fetch_option_chain("INFY")
calls_df, puts_df = parse_oi_greeks(chain)
st.markdown("#### 📈 Call Options")
st.dataframe(calls_df.sort_values("OI", ascending=False).head(10))
st.markdown("#### 📉 Put Options")
st.dataframe(puts_df.sort_values("OI", ascending=False).head(10))

time.sleep(REFRESH_INTERVAL)
st.experimental_rerun()
