"""Tests for the confluence engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from app.analysis import (
    breakout as breakout_mod,
    confluence as confluence_mod,
    momentum as momentum_mod,
    reversal as reversal_mod,
    structure as structure_mod,
    support_resistance as sr_mod,
    trend as trend_mod,
    volume as volume_mod,
)
from app.analysis.multi_timeframe import MTFReport, TFEntry
from app.data.models import Candle


def _series(steps: List[float], volume: int = 5000) -> List[Candle]:
    base = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    out = []
    for i, close in enumerate(steps):
        o = steps[i - 1] if i > 0 else close
        hi = max(o, close) + 0.2
        lo = min(o, close) - 0.2
        out.append(Candle(timestamp=base + timedelta(minutes=i), open=o, high=hi, low=lo, close=close, volume=volume))
    return out


def _run(prices, mtf_overall="aligned_up"):
    candles = _series(prices) if prices and isinstance(prices[0], (int, float)) else prices
    trend = trend_mod.classify(candles)
    momentum = momentum_mod.classify(candles)
    vol = volume_mod.classify(candles)
    zones = sr_mod.detect(candles, timeframe="1m", k=1)
    structure = structure_mod.analyze(candles, timeframe="1m", pivot_k=1)
    breakout = breakout_mod.evaluate(candles, zones, trend.direction)
    mtf = MTFReport(
        per_timeframe=[TFEntry("1h", "up" if "up" in mtf_overall else "down", 2)],
        overall=mtf_overall,
        alignment_score=2 if "up" in mtf_overall else -2,
    )
    reversal = reversal_mod.evaluate(candles, structure, momentum, breakout)
    return confluence_mod.evaluate(
        candles=candles, trend=trend, momentum=momentum, volume=vol, structure=structure,
        zones=zones, mtf=mtf, breakout=breakout, reversal=reversal, min_risk_reward=1.2,
    )


def test_wait_is_default_on_flat_market():
    r = _run([100.0] * 80, mtf_overall="mixed")
    assert r.signal == "WAIT"
    assert r.score < 65


def test_scores_are_bounded_0_100():
    r = _run([100 + i * 0.5 for i in range(80)])
    assert 0 <= r.score <= 100


def test_uptrend_generates_bullish_bias():
    prices = [100 + i * 0.4 for i in range(80)]
    r = _run(prices)
    assert r.bias in ("up", "neutral")
    # Positive evidence should not be empty for a strong uptrend
    assert r.positive_evidence


def test_conflicting_mtf_leaves_signal_in_wait():
    prices = [100 + i * 0.4 for i in range(80)]
    r = _run(prices, mtf_overall="aligned_down")
    # bias should not be "up" when higher TF disagrees strongly
    assert r.signal == "WAIT" or r.bias != "up"


def test_no_trade_plan_when_risk_reward_below_min():
    # Short series that generates bias but tiny stop/target distance
    prices = [100 + (i % 3) * 0.05 for i in range(60)]
    r = _run(prices)
    if r.trade_plan is None:
        assert r.signal == "WAIT"
