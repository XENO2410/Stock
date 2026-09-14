"""Trend classification.

Combines EMA stack + slope + higher-timeframe trend into a single verdict
per timeframe. Uses the existing indicators module - never redefines math.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from ..core import indicators as ind
from ..data.models import Candle


@dataclass
class TrendVerdict:
    direction: str      # "up" / "down" / "sideways"
    strength: int       # 0..3
    ema9: float
    ema20: float
    ema50: float
    slope_pct: float    # slope of ema20 over last 10 bars, in %/bar
    reasons: List[str]


def _slope_pct(values: np.ndarray, lookback: int = 10) -> float:
    if values.size < lookback + 1 or values[-lookback - 1] == 0:
        return 0.0
    return float((values[-1] - values[-lookback - 1]) / abs(values[-lookback - 1]) * 100.0)


def classify(candles: List[Candle]) -> TrendVerdict:
    reasons: List[str] = []
    if len(candles) < 20:
        return TrendVerdict("sideways", 0, 0, 0, 0, 0.0, ["insufficient history"])
    closes = np.array([c.close for c in candles], dtype=float)
    ema9 = float(ind.ema(closes, 9)[-1])
    ema20 = float(ind.ema(closes, 20)[-1])
    ema50 = float(ind.ema(closes, 50)[-1]) if len(closes) >= 50 else float(ind.ema(closes, len(closes))[-1])
    slope = _slope_pct(ind.ema(closes, 20))

    stacked_up = ema9 > ema20 > ema50
    stacked_down = ema9 < ema20 < ema50

    direction = "sideways"
    strength = 0
    if stacked_up:
        direction = "up"
        strength = 2
        reasons.append("EMA 9 > EMA 20 > EMA 50")
    elif stacked_down:
        direction = "down"
        strength = 2
        reasons.append("EMA 9 < EMA 20 < EMA 50")
    else:
        if ema9 > ema20:
            direction, strength = "up", 1
            reasons.append("EMA 9 > EMA 20")
        elif ema9 < ema20:
            direction, strength = "down", 1
            reasons.append("EMA 9 < EMA 20")
        else:
            reasons.append("EMAs flat")

    # Slope refinement
    if direction == "up" and slope > 0.15:
        strength = min(3, strength + 1)
        reasons.append(f"positive EMA20 slope ({slope:+.2f}%)")
    if direction == "down" and slope < -0.15:
        strength = min(3, strength + 1)
        reasons.append(f"negative EMA20 slope ({slope:+.2f}%)")
    if abs(slope) < 0.05:
        # trend is losing conviction
        strength = max(0, strength - 1)
        reasons.append("slope near zero")

    return TrendVerdict(
        direction=direction,
        strength=strength,
        ema9=ema9,
        ema20=ema20,
        ema50=ema50,
        slope_pct=round(slope, 3),
        reasons=reasons,
    )
