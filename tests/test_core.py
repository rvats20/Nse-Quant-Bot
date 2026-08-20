import pytest
import numpy as np
import pandas as pd

from black_scholes import black_scholes, gamma
from gex_engine import compute_gex, find_gamma_walls
from iron_condor import build_condor
from lottery_calls import find_lottery_calls
from config import SPOT_PRICE, IRON_CONDOR_DISTANCE, LOTTERY_DISTANCE, LOTTERY_PREMIUM_MAX


def test_black_scholes_call_known_value():
    # Known reference value for S=100,K=100,T=1,r=0.05,sigma=0.2
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    price = black_scholes(S, K, T, r, sigma, opt="call")
    assert pytest.approx(10.450583572185565, rel=1e-6) == price


def test_gamma_positive():
    g = gamma(100.0, 100.0, 1.0, 0.05, 0.2)
    assert g > 0


def test_gex_engine_aggregation():
    # Build a small option-chain DataFrame with duplicate strikes
    df = pd.DataFrame([
        {"type": "call", "strike": 100.0, "price": 1.0, "iv": 20.0, "oi": 10},
        {"type": "call", "strike": 100.0, "price": 2.0, "iv": 25.0, "oi": 20},
        {"type": "put",  "strike": 110.0, "price": 1.5, "iv": 30.0, "oi": 5}
    ])

    levels = compute_gex(df)
    # levels should contain a row per strike with a "gex" column
    assert "strike" in levels.columns and "gex" in levels.columns

    # Recompute expected exposures using the same formula as gex_engine
    from black_scholes import gamma as bs_gamma
    expected = {}
    for _, row in df.iterrows():
        sigma = row["iv"] / 100.0
        g = bs_gamma(SPOT_PRICE, row["strike"], 5/252, 0.065, sigma)
        exposure = g * row["oi"] * 100
        expected.setdefault(row["strike"], 0.0)
        expected[row["strike"]] += exposure

    # Compare values in levels
    for _, r in levels.iterrows():
        strike = r["strike"]
        assert pytest.approx(expected[strike], rel=1e-9) == r["gex"]


def test_iron_condor_builder_basic():
    # Create a small chain with nearby strikes
    df = pd.DataFrame([
        {"type": "call", "strike": 101.0, "price": 10.0, "iv": 15.0, "oi": 100},
        {"type": "call", "strike": 103.0, "price": 8.0, "iv": 14.0, "oi": 50},
        {"type": "put",  "strike": 99.0,  "price": 9.0,  "iv": 16.0, "oi": 80},
        {"type": "put",  "strike": 97.0,  "price": 7.0,  "iv": 18.0, "oi": 60}
    ])

    condor = build_condor(df, 100.0)
    # short_call should be the call closest to 100 -> 101
    assert condor["short_call"] == 101.0
    assert condor["long_call"] == 101.0 + IRON_CONDOR_DISTANCE
    # short_put should be 99
    assert condor["short_put"] == 99.0
    assert condor["long_put"] == 99.0 - IRON_CONDOR_DISTANCE


def test_lottery_calls_scanner():
    # Use a low spot so that strike > spot + LOTTERY_DISTANCE triggers
    spot = 0.0
    df = pd.DataFrame([
        {"type": "call", "strike": 600.0, "price": 5.0, "iv": 50.0, "oi": 10},
        {"type": "call", "strike": 550.0, "price": 25.0, "iv": 60.0, "oi": 5}
    ])

    results = find_lottery_calls(df, spot)
    # Only the first row should match (strike 600, premium 5 < LOTTERY_PREMIUM_MAX)
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["strike"] == 600.0
    assert results[0]["premium"] == 5.0
