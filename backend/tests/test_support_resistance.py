"""Tests for the support/resistance zone detector."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from app.analysis.support_resistance import Zone, detect, nearest
from app.data.models import Candle


def _mk(prices: List[tuple[float, float, float, float]]) -> List[Candle]:
    base = datetime(2026, 9, 1, 9, 15, tzinfo=timezone.utc)
    return [
        Candle(timestamp=base + timedelta(minutes=i), open=o, high=h, low=l, close=c, volume=1000)
        for i, (o, h, l, c) in enumerate(prices)
    ]


def test_detects_repeated_resistance_touches():
    price = 100
    p = []
    # 12 cycles x 3 bars = 36 candles, above the detector's 30-bar minimum.
    for _ in range(12):
        p += [(price, 105.2, 99, 100), (100, 101, 95.1, 96), (96, 102, 95.0, 100)]
    zones = detect(_mk(p), timeframe="1m", k=1)
    assert any(z.kind == "resistance" and 104 <= z.mid <= 106 for z in zones)
    assert any(z.kind == "support" and 94 <= z.mid <= 96 for z in zones)


def test_nearest_returns_zones_on_correct_side():
    zones = [
        Zone("support", 90, 91, 2, 3, "1m", []),
        Zone("support", 80, 81, 1, 1, "1m", []),
        Zone("resistance", 110, 111, 2, 3, "1m", []),
        Zone("resistance", 120, 121, 1, 1, "1m", []),
    ]
    assert nearest(zones, price=100, kind="support").price_low == 90
    assert nearest(zones, price=100, kind="resistance").price_low == 110


def test_no_zones_when_history_too_short():
    p = [(100, 101, 99, 100)] * 10
    assert detect(_mk(p), timeframe="1m") == []
