"""Reversal detector.

Never claims a reversal from a single indicator. Requires a combination:
  * CHOCH on the analysed timeframe (from structure engine), AND at least one of:
      - momentum divergence
      - clear rejection candle (large wick against prior trend)
      - failed breakout of the closest zone
      - close beyond the last swing extreme
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..data.models import Candle
from .breakout import BreakoutEvent
from .candles import CandlePattern, classify_one
from .momentum import MomentumVerdict
from .structure import StructureReport


@dataclass
class ReversalVerdict:
    direction: Optional[str]        # "up" / "down" / None
    strength: int                   # 0..3
    reasons: List[str] = field(default_factory=list)


def _last_choch(structure: StructureReport) -> Optional[str]:
    for ev in reversed(structure.events):
        if ev.type in ("CHOCH_UP", "CHOCH_DOWN"):
            return ev.type
    return None


def _rejection(c: Candle, side: str) -> bool:
    if c.range <= 0:
        return False
    if side == "up":
        return c.lower_wick >= c.body * 1.5 and c.close > (c.high + c.low) / 2
    return c.upper_wick >= c.body * 1.5 and c.close < (c.high + c.low) / 2


def evaluate(
    candles: List[Candle],
    structure: StructureReport,
    momentum: MomentumVerdict,
    breakout: Optional[BreakoutEvent],
) -> ReversalVerdict:
    if len(candles) < 5:
        return ReversalVerdict(None, 0, ["insufficient history"])
    last = candles[-1]
    choch = _last_choch(structure)
    reasons: List[str] = []
    signals = 0

    direction: Optional[str] = None
    if choch == "CHOCH_UP":
        direction = "up"
        reasons.append("CHOCH up")
        signals += 1
    elif choch == "CHOCH_DOWN":
        direction = "down"
        reasons.append("CHOCH down")
        signals += 1

    if momentum.divergence == "bullish":
        if direction != "down":
            direction = direction or "up"
        reasons.append("bullish RSI divergence")
        signals += 1
    if momentum.divergence == "bearish":
        if direction != "up":
            direction = direction or "down"
        reasons.append("bearish RSI divergence")
        signals += 1

    pattern: Optional[CandlePattern] = classify_one(last)
    if pattern and pattern.bias == "bullish" and _rejection(last, "up"):
        if direction != "down":
            direction = direction or "up"
        reasons.append(f"{pattern.name} with wick rejection")
        signals += 1
    if pattern and pattern.bias == "bearish" and _rejection(last, "down"):
        if direction != "up":
            direction = direction or "down"
        reasons.append(f"{pattern.name} with wick rejection")
        signals += 1

    if breakout and breakout.kind == "failed_breakout":
        reasons.append("failed breakout confirms reversal risk")
        signals += 1

    if direction is None or signals < 2:
        return ReversalVerdict(None, min(signals, 1), reasons or ["no reversal signals"])
    return ReversalVerdict(direction=direction, strength=min(3, signals), reasons=reasons)
