import requests
import pandas as pd

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

def parse_oi_greeks(chain_data):
    calls, puts = [], []
    for entry in chain_data:
        ce = entry.get("CE")
        pe = entry.get("PE")
        if ce:
            calls.append({
                "Strike": ce["strikePrice"],
                "OI": ce.get("openInterest", 0),
                "Change OI": ce.get("changeinOpenInterest", 0),
                "IV": ce.get("impliedVolatility", 0),
                "Delta": ce.get("greeks", {}).get("delta", "N/A")
            })
        if pe:
            puts.append({
                "Strike": pe["strikePrice"],
                "OI": pe.get("openInterest", 0),
                "Change OI": pe.get("changeinOpenInterest", 0),
                "IV": pe.get("impliedVolatility", 0),
                "Delta": pe.get("greeks", {}).get("delta", "N/A")
            })
    return pd.DataFrame(calls), pd.DataFrame(puts)
