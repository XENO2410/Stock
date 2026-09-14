"""Support/resistance detection as zones (not lines).

For each detected swing pivot we build a small zone (based on ATR) and
merge overlapping / nearby zones. Strength = touch count + reaction quality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np

from ..core import indicators as ind
from ..data.models import Candle


@dataclass
class Zone:
    kind: str                 # "support" / "resistance"
    price_low: float
    price_high: float
    strength: int             # 1..3
    touch_count: int
    timeframe: str
    reasons: List[str] = field(default_factory=list)

    @property
    def mid(self) -> float:
        return (self.price_low + self.price_high) / 2

    def contains(self, price: float, tol: float = 0.0) -> bool:
        return self.price_low - tol <= price <= self.price_high + tol


def _pivots(highs: Sequence[float], lows: Sequence[float], k: int = 3):
    """Return (swing_high_idx, swing_low_idx) using k-bar look-around."""
    h = np.asarray(highs)
    l = np.asarray(lows)
    ph, pl = [], []
    for i in range(k, len(h) - k):
        if h[i] == h[i - k : i + k + 1].max() and h[i] > h[i - 1] and h[i] > h[i + 1]:
            ph.append(i)
        if l[i] == l[i - k : i + k + 1].min() and l[i] < l[i - 1] and l[i] < l[i + 1]:
            pl.append(i)
    return ph, pl


def _cluster(prices: List[float], tol: float) -> List[List[float]]:
    if not prices:
        return []
    prices = sorted(prices)
    clusters: List[List[float]] = [[prices[0]]]
    for p in prices[1:]:
        base = clusters[-1][-1]
        if abs(p - base) <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return clusters


def detect(candles: List[Candle], timeframe: str, lookback: int = 150, k: int = 3, max_zones: int = 8) -> List[Zone]:
    if len(candles) < 30:
        return []
    window = candles[-lookback:] if len(candles) > lookback else candles
    highs = [c.high for c in window]
    lows = [c.low for c in window]
    closes = [c.close for c in window]

    atr = ind.atr(highs, lows, closes, 14)
    if atr <= 0:
        atr = max(1e-6, float(np.mean(highs) - np.mean(lows)) / max(1, len(window)))
    tol = max(atr * 0.5, closes[-1] * 0.001)

    ph_idx, pl_idx = _pivots(highs, lows, k)
    if not ph_idx and not pl_idx:
        return []

    swing_highs = [highs[i] for i in ph_idx]
    swing_lows = [lows[i] for i in pl_idx]
    price = closes[-1]

    zones: List[Zone] = []

    def _build(kind: str, groups: List[List[float]]) -> None:
        for grp in groups:
            mid = sum(grp) / len(grp)
            half = tol / 2
            zone = Zone(
                kind=kind,
                price_low=round(mid - half, 2),
                price_high=round(mid + half, 2),
                strength=min(3, len(grp)),
                touch_count=len(grp),
                timeframe=timeframe,
                reasons=[f"{len(grp)} swing pivots"],
            )
            zones.append(zone)

    _build("resistance", _cluster(swing_highs, tol))
    _build("support", _cluster(swing_lows, tol))

    # Reaction quality: bump strength if a close reacted strongly off the zone
    for z in zones:
        reactions = 0
        for c in window:
            if z.contains(c.high, tol=tol * 0.2) and c.close < z.price_low:
                reactions += 1
            elif z.contains(c.low, tol=tol * 0.2) and c.close > z.price_high:
                reactions += 1
        if reactions >= 2:
            z.strength = min(3, z.strength + 1)
            z.reasons.append(f"{reactions} strong reactions")

    # Split into support (below price) and resistance (above), keep closest zones first
    supports = sorted([z for z in zones if z.kind == "support" and z.mid < price], key=lambda z: price - z.mid)
    resistances = sorted([z for z in zones if z.kind == "resistance" and z.mid > price], key=lambda z: z.mid - price)
    keep = supports[: max_zones // 2] + resistances[: max_zones // 2]
    return keep


def nearest(zones: List[Zone], price: float, kind: str) -> Zone | None:
    candidates = [z for z in zones if z.kind == kind]
    if kind == "support":
        candidates = [z for z in candidates if z.mid < price]
    else:
        candidates = [z for z in candidates if z.mid > price]
    if not candidates:
        return None
    return min(candidates, key=lambda z: abs(z.mid - price))
