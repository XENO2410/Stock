"""Breakout / retest / failed breakout detection.

A breakout is not "price crossed a line". It's a confluence:
  1. Close (not just wick) beyond a zone by more than a tolerance.
  2. Above-average volume on the breakout bar.
  3. Bar of the same direction as the break.
  4. Higher-timeframe trend not opposing the break.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..data.models import Candle
from .support_resistance import Zone


@dataclass
class BreakoutEvent:
    kind: str          # "breakout_up" / "breakdown" / "retest" / "failed_breakout"
    zone_mid: float
    price: float
    strength: int      # 1..3
    reasons: List[str] = field(default_factory=list)


def _avg_volume(candles: List[Candle], n: int = 20) -> float:
    vols = [c.volume for c in candles[-n:] if c.volume > 0]
    return float(np.mean(vols)) if vols else 0.0


def evaluate(
    candles: List[Candle],
    zones: List[Zone],
    trend_direction: str,
    tolerance_pct: float = 0.12,
) -> Optional[BreakoutEvent]:
    if len(candles) < 5 or not zones:
        return None
    last = candles[-1]
    prev = candles[-2]
    avg_vol = _avg_volume(candles)

    # Iterate closest zones first for the last close direction
    if last.close >= prev.close:
        candidates = sorted([z for z in zones if z.kind == "resistance"], key=lambda z: abs(z.mid - last.close))
    else:
        candidates = sorted([z for z in zones if z.kind == "support"], key=lambda z: abs(z.mid - last.close))
    if not candidates:
        return None
    z = candidates[0]

    tol = z.mid * (tolerance_pct / 100.0)
    reasons: List[str] = []

    # Breakout up
    if z.kind == "resistance" and last.close > z.price_high + tol and prev.close <= z.price_high:
        strength = 1
        if last.volume >= avg_vol * 1.3 > 0:
            strength += 1
            reasons.append("volume confirms")
        else:
            reasons.append("weak volume")
        if trend_direction != "down":
            strength += 1
            reasons.append(f"trend {trend_direction} supportive")
        return BreakoutEvent(
            kind="breakout_up",
            zone_mid=z.mid,
            price=last.close,
            strength=min(3, strength),
            reasons=reasons + [f"closed above resistance {z.price_high}"],
        )

    # Breakdown
    if z.kind == "support" and last.close < z.price_low - tol and prev.close >= z.price_low:
        strength = 1
        if last.volume >= avg_vol * 1.3 > 0:
            strength += 1
            reasons.append("volume confirms")
        else:
            reasons.append("weak volume")
        if trend_direction != "up":
            strength += 1
            reasons.append(f"trend {trend_direction} supportive")
        return BreakoutEvent(
            kind="breakdown",
            zone_mid=z.mid,
            price=last.close,
            strength=min(3, strength),
            reasons=reasons + [f"closed below support {z.price_low}"],
        )

    # Retest: previously broke resistance; now dipping back into the zone but holding above midpoint
    if z.kind == "resistance" and prev.close > z.price_high and last.low <= z.price_high and last.close >= z.mid:
        return BreakoutEvent(
            kind="retest",
            zone_mid=z.mid,
            price=last.close,
            strength=2,
            reasons=["retest of prior resistance", "close above zone mid"],
        )
    if z.kind == "support" and prev.close < z.price_low and last.high >= z.price_low and last.close <= z.mid:
        return BreakoutEvent(
            kind="retest",
            zone_mid=z.mid,
            price=last.close,
            strength=2,
            reasons=["retest of prior support", "close below zone mid"],
        )

    # Failed breakout: closed back inside the zone after wicking beyond
    if z.kind == "resistance" and prev.high > z.price_high and last.close < z.price_low:
        return BreakoutEvent(
            kind="failed_breakout",
            zone_mid=z.mid,
            price=last.close,
            strength=2,
            reasons=["wick beyond resistance", "close back below zone"],
        )
    if z.kind == "support" and prev.low < z.price_low and last.close > z.price_high:
        return BreakoutEvent(
            kind="failed_breakout",
            zone_mid=z.mid,
            price=last.close,
            strength=2,
            reasons=["wick beyond support", "close back above zone"],
        )

    return None
