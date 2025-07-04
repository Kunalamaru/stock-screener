import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
import plotly.express as px
from ta.momentum import RSIIndicator
from modules.option_chain import fetch_option_chain, parse_oi_greeks

st.set_page_config(page_title="📈 Volume Spike + RSI Chart", layout="wide")
REFRESH_INTERVAL = 5

@st.cache_data(ttl=86400)
def get_all_nse_stocks():
    nifty_100_symbols = [
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
    return [symbol + ".NS" for symbol in nifty_100_symbols]

def fetch_price_data(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        return data if not data.empty else None
    except:
        return None

def analyze_stock(df):
    if df is None or len(df) < 20:
        return False
    volume = df["Volume"]
    close = df["Close"]
    avg_vol_10d = volume.rolling(window=10).mean()
    vol_spike = volume.iloc[-1] > 1.5 * avg_vol_10d.iloc[-1]
    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    if vol_spike:
        return {
            "Last Price": close.iloc[-1],
            "Volume": volume.iloc[-1],
            "Avg Vol (10D)": round(avg_vol_10d.iloc[-1], 0),
            "Vol Spike Ratio": round(volume.iloc[-1] / avg_vol_10d.iloc[-1], 2),
            "RSI": round(rsi, 2)
        }
    else:
        return False

# UI
st.title("📊 NSE Screener — Volume Spike + RSI Ranking")
st.caption("Live data via Yahoo Finance | Top NIFTY 100 stocks")
st.markdown("🔁 Auto-refreshes every 5 seconds")

symbols = get_all_nse_stocks()
results = []

progress = st.progress(0)
for i, symbol in enumerate(symbols[:50]):  # Limit to 50 per run for performance
    df = fetch_price_data(symbol)
    result = analyze_stock(df)
    if result:
        results.append({
            "Symbol": symbol.replace(".NS", ""),
            "Last Price": result["Last Price"],
            "Volume": result["Volume"],
            "10-Day Avg": result["Avg Vol (10D)"],
            "Spike Ratio": result["Vol Spike Ratio"],
            "RSI": result["RSI"]
        })
    progress.progress((i + 1) / 50)

if results:
    df_results = pd.DataFrame(results)
    df_results.sort_values(by=["Spike Ratio", "RSI"], ascending=[False, True], inplace=True)
    st.success(f"✅ {len(df_results)} stocks found with volume spike and RSI info")
    st.dataframe(df_results, use_container_width=True)

    st.markdown("### 📈 Volume Spike Chart")
    fig = px.bar(df_results,
                 x="Symbol", y="Spike Ratio",
                 color="RSI",
                 text="RSI",
                 title="Volume Spike vs RSI (low RSI = more oversold)",
                 color_continuous_scale="Blues_r")
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_tickangle=-45, height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("🚫 No stocks met the volume spike filter.")

# Demo Option Chain
st.markdown("### 🔍 Options Chain (INFY - demo)")
chain = fetch_option_chain("INFY")
calls_df, puts_df = parse_oi_greeks(chain)
st.markdown("#### 📈 Call Options")
st.dataframe(calls_df.sort_values("OI", ascending=False).head(10))
st.markdown("#### 📉 Put Options")
st.dataframe(puts_df.sort_values("OI", ascending=False).head(10))

time.sleep(REFRESH_INTERVAL)
st.experimental_rerun()
