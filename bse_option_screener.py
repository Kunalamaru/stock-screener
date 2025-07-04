import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from modules.option_chain import fetch_option_chain, parse_oi_greeks

st.set_page_config(page_title="📈 Enhanced Option Screener", layout="wide")

NSE_OPTION_CSV_URL = "https://www1.nseindia.com/content/fo/fo_mktlots.csv"
REFRESH_INTERVAL = 5

@st.cache_data(ttl=300)
def fetch_nse_option_stocks():
    try:
        df = pd.read_csv(NSE_OPTION_CSV_URL)
        symbols = df["SYMBOL"].dropna().unique()
        return [s + ".NS" for s in symbols if isinstance(s, str)]
    except Exception as e:
        st.error(f"Error fetching NSE options data: {e}")
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

st.title("📈 Positive Expectancy Option Screener")
st.caption("Filters: Golden Cross + RSI > 50 + 21EMA + Volume Spike")
st.markdown("🔄 Refreshing every 5 seconds...")

symbols = fetch_nse_option_stocks()
results = []

progress = st.progress(0)
total = len(symbols)

for i, symbol in enumerate(symbols[:50]):
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
    st.warning("No matches found with all criteria met.")

st.markdown("### 🔍 Options Chain (INFY)")
chain = fetch_option_chain("INFY")
calls_df, puts_df = parse_oi_greeks(chain)
st.markdown("#### 📈 Call Options")
st.dataframe(calls_df.sort_values("OI", ascending=False).head(10))
st.markdown("#### 📉 Put Options")
st.dataframe(puts_df.sort_values("OI", ascending=False).head(10))

time.sleep(REFRESH_INTERVAL)
st.experimental_rerun()
