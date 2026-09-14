"""Tests for the replay engine.

The most important test in this file is `test_no_lookahead_invariant`,
which proves that when the cursor is at candle N, the analysis engine's
output is IDENTICAL whether or not candles N+1..N+50 exist in the
dataset. This is the core no-look-ahead guarantee.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import List

from app.backtesting.replay_session import ReplayProvider, ReplaySession
from app.backtesting.aggregator import aggregate, can_aggregate
from app.data.models import Candle
from app.signals.engine import run as run_analysis


def _synthetic(n: int, seed: int = 1) -> List[Candle]:
    rng = random.Random(seed)
    base = datetime(2026, 9, 1, 3, 45, tzinfo=timezone.utc)  # 09:15 IST
    out = []
    price = 100.0
    for i in range(n):
        step = rng.gauss(0, 0.4) + math.sin(i / 15) * 0.15
        o = price
        c = max(1.0, o + step)
        h = max(o, c) + abs(rng.gauss(0, 0.15))
        l = min(o, c) - abs(rng.gauss(0, 0.15))
        v = rng.randint(5000, 15000)
        out.append(Candle(timestamp=base + timedelta(minutes=5 * i), open=o, high=h, low=l, close=c, volume=v))
        price = c
    return out


def _session_from(candles: List[Candle], cursor: int) -> ReplaySession:
    from app.backtesting.replay_session import _hydrate_all_tfs
    tfs = _hydrate_all_tfs("5m", candles)
    return ReplaySession(
        id="test",
        symbol="TEST",
        primary_tf="5m",
        candles_by_tf=tfs,
        cursor=cursor,
    )


# ---------------- Aggregator ----------------

def test_aggregator_5m_to_15m_groups_correctly():
    candles = _synthetic(60)
    agg = aggregate(candles, "5m", "15m")
    assert agg
    # 60 5m candles -> 20 15m candles (some edge buckets may drop, allow ±2)
    assert 18 <= len(agg) <= 20
    # Open of first 15m must equal open of first 5m in that bucket
    assert agg[0].open == candles[0].open
    # High of a bucket must be >= any 5m high inside it
    for c15 in agg[:5]:
        contained = [c for c in candles if c15.timestamp <= c.timestamp < c15.timestamp + timedelta(minutes=15)]
        if contained:
            assert c15.high >= max(x.high for x in contained) - 1e-9


def test_can_aggregate_only_upwards():
    assert can_aggregate("5m", "15m")
    assert can_aggregate("1m", "1h")
    assert not can_aggregate("5m", "1m")
    assert not can_aggregate("5m", "7m")   # non-divisor


# ---------------- Replay provider basics ----------------

def test_replay_provider_never_returns_candles_beyond_cursor():
    candles = _synthetic(120)
    session = _session_from(candles, cursor=40)
    provider = ReplayProvider(session)
    series = provider.get_ohlcv("TEST", "5m", limit=500)
    assert series.candles
    cutoff_ts = session.current_timestamp()
    for c in series.candles:
        assert c.timestamp <= cutoff_ts


def test_replay_provider_updates_when_cursor_moves():
    candles = _synthetic(120)
    session = _session_from(candles, cursor=30)
    provider = ReplayProvider(session)
    n0 = len(provider.get_ohlcv("TEST", "5m", limit=500).candles)
    session.cursor = 50
    n1 = len(provider.get_ohlcv("TEST", "5m", limit=500).candles)
    assert n1 > n0
    assert n1 == 51


# ---------------- The critical no-look-ahead invariant ----------------

def _report_signature(report) -> tuple:
    """Reduce a report to the fields that would leak if look-ahead existed."""
    return (
        report.signal,
        report.score,
        report.bias,
        tuple(sorted(report.group_scores.items())),
        report.trend["direction"], report.trend["strength"],
        report.momentum["rsi14"],
        report.structure["bias"],
        len(report.structure["events"]),
        len(report.support), len(report.resistance),
    )


def test_no_lookahead_invariant():
    """Given identical candles [0..N], the analysis report at cursor N must
    be identical whether the dataset contains candles beyond N or not."""
    full = _synthetic(200, seed=7)
    truncated = full[:120]
    N = 100

    session_truncated = _session_from(truncated, cursor=N)
    session_full = _session_from(full, cursor=N)

    report_a = run_analysis(ReplayProvider(session_truncated), "TEST", timeframe="5m")
    report_b = run_analysis(ReplayProvider(session_full), "TEST", timeframe="5m")

    assert _report_signature(report_a) == _report_signature(report_b)
    # Trade plan (if any) must also be identical - it uses stop / target
    # derived from historical structure and ATR only.
    assert (report_a.trade_plan is None) == (report_b.trade_plan is None)
    if report_a.trade_plan is not None:
        assert report_a.trade_plan == report_b.trade_plan


def test_replay_is_deterministic():
    """Two identical sessions produce identical reports at the same cursor."""
    candles = _synthetic(150, seed=11)
    s1 = _session_from(candles, cursor=90)
    s2 = _session_from(candles, cursor=90)
    r1 = run_analysis(ReplayProvider(s1), "TEST", timeframe="5m")
    r2 = run_analysis(ReplayProvider(s2), "TEST", timeframe="5m")
    assert _report_signature(r1) == _report_signature(r2)


def test_replay_step_and_reset():
    from app.api.replay import step as step_endpoint
    candles = _synthetic(80)
    session = _session_from(candles, cursor=30)
    from app.backtesting.replay_session import STORE
    STORE.put(session)
    st = step_endpoint(session.id, count=5)
    assert st["cursor"] == 35
    st = step_endpoint(session.id, count=999)
    assert st["cursor"] == session.total() - 1
    assert st["status"] == "finished"
    STORE.delete(session.id)
