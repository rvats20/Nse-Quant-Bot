"""Backtest the Nse-Quant-Bot strategies on historical NIFTY data.

Strategies tested (weekly cycles, using spot prices as proxies for option legs):
  1. Iron Condor: short strangle at nearest strikes to spot, wings at +/- IRON_CONDOR_DISTANCE,
     held to expiry. P&L estimated via Black-Scholes at entry and expiry.
  2. Lottery Calls: buy OTM calls beyond LOTTERY_DISTANCE with premium < LOTTERY_PREMIUM_MAX
     (premium proxied by BS price using realized vol), held to expiry.

Data: ^NSEI daily OHLC from Yahoo Finance (2020-present).
"""
import datetime as dt

import numpy as np
import pandas as pd
import yfinance as yf

from black_scholes import black_scholes, gamma
from config import IRON_CONDOR_DISTANCE, LOTTERY_DISTANCE, LOTTERY_PREMIUM_MAX, RISK_FREE_RATE

WING = float(IRON_CONDOR_DISTANCE)
R = RISK_FREE_RATE


def load_data():
    df = yf.download("^NSEI", start="2020-01-01", progress=False, auto_adjust=True)
    df.columns = [c[0].lower() for c in df.columns]
    return df


def realized_vol(closes, window=20):
    return closes.pct_change().rolling(window).std().iloc[-1] * np.sqrt(252)


def weekly_cycles(df):
    """Yield (entry_date, expiry_date) pairs: every Friday-to-next-Thursday cycle."""
    fridays = df[df.index.dayofweek == 4].index
    for entry in fridays:
        # expiry: next Thursday (NIFTY weekly) or last trading day within 7 days
        window = df.loc[entry:].index[1:8]
        thursdays = [d for d in window if d.dayofweek == 3]
        expiry = thursdays[0] if thursdays else (window[-1] if len(window) else None)
        if expiry is not None:
            yield entry, expiry


def nearest(strikes, target):
    return min(strikes, key=lambda s: abs(s - target))


def strike_grid(spot, step=50):
    base = round(spot / step) * step
    return [base + i * step for i in range(-40, 41)]


def backtest(df):
    trades = []
    for entry, expiry in weekly_cycles(df):
        seg = df.loc[entry:expiry]
        if len(seg) < 2:
            continue
        spot_entry = float(seg["close"].iloc[0])
        spot_exit = float(seg["close"].iloc[-1])
        T_entry = max((expiry - entry).days / 365.0, 1 / 365)
        T_exit = 1 / 365 * 0.5  # ~half a day left at close on expiry day
        sigma = realized_vol(df["close"].loc[:entry])

        # ---- Iron Condor ----
        grid = strike_grid(spot_entry)
        sc = nearest(grid, spot_entry)
        lc = sc + WING
        sp = nearest(grid, spot_entry)
        lp = sp - WING
        credit = (
            black_scholes(spot_entry, sc, T_entry, R, sigma, "call")
            - black_scholes(spot_entry, lc, T_entry, R, sigma, "call")
            + black_scholes(spot_entry, sp, T_entry, R, sigma, "put")
            - black_scholes(spot_entry, lp, T_entry, R, sigma, "put")
        )
        debit_exit = (
            black_scholes(spot_exit, sc, T_exit, R, sigma, "call")
            - black_scholes(spot_exit, lc, T_exit, R, sigma, "call")
            + black_scholes(spot_exit, sp, T_exit, R, sigma, "put")
            - black_scholes(spot_exit, lp, T_exit, R, sigma, "put")
        )
        condor_pnl = credit - debit_exit  # per share; x75 qty for NIFTY

        # ---- Lottery Calls ----
        lot_pnl = None
        candidates = [s for s in grid if s > spot_entry + LOTTERY_DISTANCE]
        if candidates:
            strike = min(candidates)
            prem = black_scholes(spot_entry, strike, T_entry, R, sigma, "call")
            if prem < LOTTERY_PREMIUM_MAX:
                intrinsic = max(spot_exit - strike, 0.0)
                lot_pnl = intrinsic - prem

        trades.append({
            "entry": entry.date(), "expiry": expiry.date(),
            "spot_in": round(spot_entry), "spot_out": round(spot_exit),
            "condor_credit": round(float(credit), 2),
            "condor_pnl": round(float(condor_pnl), 2),
            "lottery_pnl": None if lot_pnl is None else round(lot_pnl, 2),
        })
    return pd.DataFrame(trades)


def summarize(trades):
    out = []
    for strat, col in [("Iron Condor", "condor_pnl"), ("Lottery Calls", "lottery_pnl")]:
        t = trades.dropna(subset=[col])
        pnl = t[col] * 75  # NIFTY lot size
        wins = (pnl > 0).sum()
        out.append({
            "strategy": strat, "trades": len(t),
            "win_rate_%": round(100 * wins / len(t), 1) if len(t) else None,
            "total_pnl_rs": int(pnl.sum()),
            "avg_pnl_rs": round(pnl.mean(), 1) if len(t) else None,
            "worst_rs": int(pnl.min()) if len(t) else None,
            "best_rs": int(pnl.max()) if len(t) else None,
        })
    return pd.DataFrame(out)


if __name__ == "__main__":
    df = load_data()
    print(f"NIFTY data: {df.index[0].date()} -> {df.index[-1].date()} ({len(df)} rows)")
    trades = backtest(df)
    trades.to_csv("backtest_results.csv", index=False)
    print(f"{len(trades)} weekly cycles tested\n")
    print(summarize(trades).to_string(index=False))
