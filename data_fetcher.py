import requests
import pandas as pd

URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

def fetch_option_chain():

    session = requests.Session()

    session.get("https://www.nseindia.com", headers=headers, timeout=15)

    resp = session.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    rows = []

    for r in data["records"]["data"]:

        strike = r["strikePrice"]

        if "CE" in r:
            ce = r["CE"]
            rows.append({
                "type": "call",
                "strike": strike,
                "price": ce["lastPrice"],
                "iv": ce["impliedVolatility"],
                "oi": ce["openInterest"]
            })

        if "PE" in r:
            pe = r["PE"]
            rows.append({
                "type": "put",
                "strike": strike,
                "price": pe["lastPrice"],
                "iv": pe["impliedVolatility"],
                "oi": pe["openInterest"]
            })

    return pd.DataFrame(rows)
