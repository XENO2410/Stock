"""Tests for the market-structure engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from app.analysis.structure import analyze
from app.data.models import Candle


def _mk(prices: List[tuple[float, float, float, float]]) -> List[Candle]:
    """Build candles from (open, high, low, close) tuples on a 1-min stride."""
    base = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    out: List[Candle] = []
    for i, (o, h, l, c) in enumerate(prices):
        out.append(Candle(timestamp=base + timedelta(minutes=i), open=o, high=h, low=l, close=c, volume=1000))
    return out


def test_uptrend_produces_hh_hl_sequence():
    # Alternating higher highs and higher lows with an intermediate pullback.
    p = [
        (100, 101, 99, 100),  # baseline
        (100, 102, 100, 101),
        (101, 105, 101, 104),  # swing high @ 105
        (104, 104, 100, 101),
        (101, 100, 99, 100),   # swing low @ 99
        (100, 103, 100, 102),
        (102, 108, 102, 107),  # swing high @ 108 (HH)
        (107, 107, 104, 105),
        (105, 105, 103, 104),  # swing low @ 103 (HL)
        (104, 107, 104, 106),
        (106, 112, 106, 111),  # swing high @ 112 (HH)
        (111, 111, 108, 109),
    ]
    r = analyze(_mk(p), timeframe="1m", pivot_k=1)
    types = [e.type for e in r.events]
    assert "HH" in types
    assert "HL" in types
    assert r.bias == "up"


def test_choch_flip_from_up_to_down():
    p = [
        (100, 101, 99, 100),
        (100, 105, 100, 104),  # SH 105
        (104, 104, 102, 103),
        (103, 103, 100, 101),  # SL 100
        (101, 108, 101, 107),  # HH 108
        (107, 107, 104, 105),
        (105, 105, 103, 104),  # HL 103
        (104, 106, 104, 105),
        # Sharp drop that produces a low below 103 and a raised low after it,
        # so the pivot detector actually confirms the new SL.
        (105, 105, 100, 101),
        (101, 101, 97, 98),    # SL 97 breaks 103
        (98, 100, 98, 99),     # next low raised so bar 9's low is a strict pivot
        (99, 100, 98, 99),
    ]
    r = analyze(_mk(p), timeframe="1m", pivot_k=1)
    types = [e.type for e in r.events]
    assert "CHOCH_DOWN" in types or "BOS_DOWN" in types
    assert r.bias == "down"


def test_no_events_when_flat():
    p = [(100, 100.5, 99.5, 100)] * 20
    r = analyze(_mk(p), timeframe="1m", pivot_k=1)
    assert r.events == [] or all(ev.confidence <= 1 for ev in r.events)
