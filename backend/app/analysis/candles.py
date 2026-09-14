"""Candle-pattern classifiers.

Deterministic, single-candle and two-candle patterns useful as small
evidence contributions to the confluence engine. No arbitrary thresholds
that aren't explained in code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..data.models import Candle


@dataclass
class CandlePattern:
    name: str          # e.g. "bullish_engulfing"
    bias: str          # "bullish" / "bearish" / "neutral"
    strength: int      # 1..3 (weak/medium/strong)


def _tiny_body(c: Candle) -> bool:
    return c.body <= c.range * 0.1 and c.range > 0


def _long_body(c: Candle) -> bool:
    return c.range > 0 and c.body >= c.range * 0.6


def classify_one(c: Candle) -> Optional[CandlePattern]:
    if c.range <= 0:
        return None
    if _tiny_body(c):
        return CandlePattern("doji", "neutral", 1)
    # Hammer: small body near top, long lower wick, small upper wick
    if c.lower_wick >= c.body * 2 and c.upper_wick <= c.body * 0.5:
        return CandlePattern("hammer", "bullish", 2)
    # Shooting star: small body near bottom, long upper wick, small lower wick
    if c.upper_wick >= c.body * 2 and c.lower_wick <= c.body * 0.5:
        return CandlePattern("shooting_star", "bearish", 2)
    # Marubozu (very long body, tiny wicks)
    if _long_body(c) and c.upper_wick <= c.range * 0.05 and c.lower_wick <= c.range * 0.05:
        return CandlePattern("marubozu", "bullish" if c.is_bull else "bearish", 3)
    return None


def classify_two(prev: Candle, cur: Candle) -> Optional[CandlePattern]:
    if prev.range <= 0 or cur.range <= 0:
        return None
    # Bullish engulfing
    if not prev.is_bull and cur.is_bull and cur.open <= prev.close and cur.close >= prev.open:
        return CandlePattern("bullish_engulfing", "bullish", 3)
    # Bearish engulfing
    if prev.is_bull and not cur.is_bull and cur.open >= prev.close and cur.close <= prev.open:
        return CandlePattern("bearish_engulfing", "bearish", 3)
    return None


def recent_patterns(candles: List[Candle], lookback: int = 5) -> List[CandlePattern]:
    """Return patterns detected in the last `lookback` candles, latest last."""
    out: List[CandlePattern] = []
    if not candles:
        return out
    window = candles[-lookback:]
    for i, c in enumerate(window):
        one = classify_one(c)
        if one:
            out.append(one)
        if i > 0:
            two = classify_two(window[i - 1], c)
            if two:
                out.append(two)
    return out
