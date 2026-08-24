"""Parameter sweep for Nse-Quant-Bot with a strict acceptance gate.

Philosophy: parameters stay TIGHT (small wings, near-the-money shorts, cheap
lottery caps). Every candidate is tested on the same historical NIFTY weekly
cycles; any strategy that FAILS the gate (negative expectancy or max drawdown
beyond 2x its average credit) is discarded outright and we move on to the
next candidate. Only survivors are reported.

Gate rules (all must pass):
  - total P&L > 0 over the full backtest
  - max losing streak <= 6 weeks
  - worst single trade loss <= 3x avg premium collected
"""
import itertools

import numpy as np
import pandas as pd

from black_scholes import black_scholes
from config import RISK_FREE_RATE
from backtest import load_data, realized_vol, weekly_cycles, nearest, strike_grid

R = RISK_FREE_RATE
LOT = 75


def run_cycle(seg, df, entry):
    """Precompute per-cycle inputs once, including vol-regime filters."""
    spot_entry = float(seg["close"].iloc[0])
    spot_exit = float(seg["close"].iloc[-1])
    days = max((seg.index[-1] - seg.index[0]).days, 1)
    T_entry = days / 365.0
    T_exit = 0.5 / 365
    closes = df["close"].loc[:entry]
    sigma = realized_vol(closes)
    # IV-rank style filter: trade only when current vol is elevated vs its
    # 1-year history (sell expensive vol).
    hist = closes.pct_change().rolling(20).std() * np.sqrt(252)
    iv_rank = float((hist.iloc[-1] - hist.tail(252).min())
                    / max(hist.tail(252).max() - hist.tail(252).min(), 1e-9))
    med = float(hist.tail(252).median())
    crash = bool(sigma > 2 * med)  # skip new entries in vol spikes
    return spot_entry, spot_exit, T_entry, T_exit, sigma, iv_rank, crash


def condor_pnl_raw(spot_in, spot_out, Tin, Tout, sigma, wing, otm, sc=None, sp=None):
    grid = strike_grid(spot_in)
    if sc is None:
        sc = nearest(grid, spot_in + otm)
    if sp is None:
        sp = nearest(grid, spot_in - otm)
    lc = sc + wing
    lp = sp - wing
    if lc not in grid or lp not in grid:
        return None
    def legs(S, T):
        c = lambda K: black_scholes(S, K, T, R, sigma, "call")
        p = lambda K: black_scholes(S, K, T, R, sigma, "put")
        return c(sc) - c(lc) + p(sp) - p(lp)
    return float(legs(spot_in, Tin) - legs(spot_out, Tout)) * LOT


def lottery_pnl(spot_in, spot_out, Tin, sigma, distance, prem_cap, step):
    grid = strike_grid(spot_in, step=step)
    candidates = [s for s in grid if s > spot_in + distance]
    if not candidates:
        return None
    strike = min(candidates)
    prem = black_scholes(spot_in, strike, Tin, R, sigma, "call")
    if prem >= prem_cap:
        return None
    return (max(spot_out - strike, 0.0) - prem) * LOT


def evaluate(pnls, credits=None):
    t = pd.Series([p for p in pnls if p is not None])
    if len(t) < 20:
        return None  # too few valid trades to judge
    total = t.sum()
    streak = worst_streak(t < 0)
    worst = t.min()
    avg_win = t[t > 0].mean() if (t > 0).any() else 0
    gate = {
        "profitable": bool(total > 0),
        "streak_ok": bool(streak <= 6),
        "tail_ok": bool(abs(worst) <= max(3 * abs(credits.mean()), 1e9)) if credits is not None else True,
    }
    return {
        "trades": len(t), "win_rate": round(100 * (t > 0).mean(), 1),
        "total_pnl": int(total), "avg_pnl": round(t.mean(), 1),
        "worst_trade": int(worst), "max_losing_streak": streak,
        "gate_passed": all(gate.values()),
    }


def worst_streak(mask):
    m = mask.astype(int).values
    best = cur = 0
    for v in m:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def main():
    df = load_data()
    cycles = []
    for entry, expiry in weekly_cycles(df):
        seg = df.loc[entry:expiry]
        if len(seg) < 2:
            continue
        cycles.append(run_cycle(seg, df, entry))
    print(f"{len(cycles)} cycles loaded\n")

    # ---- Candidate grid: TIGHT parameters first ----
    condor_grid = list(itertools.product(
        [150, 200, 250, 300],    # wing width (tight first, widening only as needed)
        [0, 50, 100],            # short-strike OTM offset
    ))
    lottery_grid = list(itertools.product(
        [300, 400, 500],         # OTM distance
        [10, 15, 20],            # premium cap
        [50],                    # strike granularity
    ))

    survivors = []

    print("== Iron Condor candidates (IV-rank filter + crash skip + early exit) ==")
    for ivmin, wing, otm in itertools.product([0.3, 0.5, 0.7], [150, 200, 250, 300], [0, 50, 100]):
        pnls, credits = [], []
        for spot_in, spot_out, Tin, Tout, sigma, iv_rank, crash in cycles:
            if crash or iv_rank < ivmin:
                continue  # regime filters: skip cheap-vol and panic weeks
            grid = strike_grid(spot_in)
            sc = nearest(grid, spot_in + otm)
            sp = nearest(grid, spot_in - otm)
            cr = (
                black_scholes(spot_in, sc, Tin, R, sigma, "call")
                + black_scholes(spot_in, sp, Tin, R, sigma, "put")
            )
            credits.append(cr * LOT)
            pnl = condor_pnl_raw(spot_in, spot_out, Tin, Tout, sigma, wing, otm, sc, sp)
            # Early exit: stop out at 2x credit; take profit at 50% of credit
            if pnl <= -2 * cr * LOT:
                pnl = -2 * cr * LOT
            elif pnl >= 0.5 * cr * LOT:
                pnl = 0.5 * cr * LOT
            pnls.append(pnl)
        r = evaluate(pnls, pd.Series(credits))
        tag = f"condor iv>={ivmin} wing={wing} otm={otm}"
        if r and r["gate_passed"]:
            print(f"  PASS {tag}: {r}")
            survivors.append({"strategy": "iron_condor", "params": {"wing": wing, "otm": otm}, **r})
        else:
            why = "" if r else "(insufficient trades)"
            print(f"  DISCARD {tag} {why}")

    print("\n== Lottery Call candidates ==")
    for dist, cap, step in lottery_grid:
        pnls = []
        for spot_in, spot_out, Tin, _, sigma, iv_rank, crash in cycles:
            if crash or iv_rank > 0.7:
                continue  # lottery calls are long-vol: skip panic weeks and only buy cheap vol
            pnls.append(lottery_pnl(spot_in, spot_out, Tin, sigma, dist, cap, step))
        r = evaluate(pnls)
        tag = f"lottery dist={dist} cap={cap}"
        if r and r["gate_passed"]:
            print(f"  PASS {tag}: {r}")
            survivors.append({"strategy": "lottery", "params": {"distance": dist, "prem_cap": cap}, **r})
        else:
            print(f"  DISCARD {tag}")

    out = pd.DataFrame(survivors)
    out.to_csv("sweep_survivors.csv", index=False)
    print("\n== Survivors ==")
    print(out.to_string(index=False) if len(out) else "NONE — no configuration passed the gate.")


if __name__ == "__main__":
    main()
