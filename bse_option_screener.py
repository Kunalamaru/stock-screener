import streamlit as st
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import requests

st.set_page_config(page_title="📈 3% Move Predictor + Option Chain + Telegram", layout="wide")

# === CONFIGURE YOUR TELEGRAM BOT HERE ===
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
CHAT_ID = "PASTE_YOUR_CHAT_ID_HERE"


# === Telegram Alert Function ===
def send_telegram_alert(stock_info):
    if not BOT_TOKEN or not CHAT_ID:
        return

    message = (
        f"🚨 *Stock Alert: {stock_info['Symbol']}*\n"
        f"💰 Price: ₹{stock_info['Last Price']}\n"
        f"📈 RSI: {stock_info['RSI']}\n"
        f"📊 % Change: {stock_info['% Change']}%\n"
        f"📦 Volume Spike: {stock_info['Volume Spike']}x\n"
        f"🧠 Score: {stock_info['Score']} / 4"
    )

    url = f"https://api.telegram.org/bot{8154012655:AAGk2Czczh7uIIKXVJv1m_0V4uqHf0wlY}/sendMessage"
    payload = {"7488960267": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print(f"✅ Telegram alert sent for {stock_info['Symbol']}")
        else:
            print("❌ Telegram error:", response.text)
    except Exception as e:
        print("❌ Exception in Telegram:", e)


# === Stock List ===
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


def fetch_price_data(symbol):
    try:
        df = yf.download(symbol, period="10d", interval="1d", progress=False)
        return df if not df.empty else None
    except:
        return None


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
    except Exception:
        return []


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


def analyze_stock(df):
    if df is None or len(df) < 6:
        return None

    close = df.get("Close", pd.Series(dtype=float)).dropna()
    volume = df.get("Volume", pd.Series(dtype=float)).dropna()

    if len(close) < 15 or len(volume) < 6:
        return None

    try:
        rsi = RSIIndicator(close, window=14).rsi().dropna().iloc[-1]
    except:
        return None

    try:
        ema5 = EMAIndicator(close, window=5).ema_indicator().iloc[-1]
    except:
        return None

    try:
        today_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        prev_high = df["High"].iloc[-2]
        today_vol = volume.iloc[-1]
        avg_vol = volume[-6:-1].mean()
    except:
        return None

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
st.title("📊 NSE Screener — 3% Move Predictor + Option Chain + Telegram Alerts")
st.caption("Alerts: Volume > 2× avg, RSI > 55, Price > Prev High & EMA5")

symbols = [s + ".NS" for s in get_nifty_100_symbols()]
results = []

progress = st.progress(0)
for i, symbol in enumerate(symbols[:50]):  # Limit for performance
    df = fetch_price_data(symbol)
    result = analyze_stock(df)
    if result:
        result["Symbol"] = symbol.replace(".NS", "")
        results.append(result)
        send_telegram_alert(result)
    progress.progress((i + 1) / 50)

if results:
    df_final = pd.DataFrame(results)
    df_final.sort_values(by=["Score", "% Change"], ascending=[False, False], inplace=True)
    st.success(f"✅ {len(df_final)} stocks found")
    st.dataframe(df_final, use_container_width=True)

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
