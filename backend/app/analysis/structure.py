"""Market structure engine: HH/HL/LH/LL + BOS + CHOCH.

Deterministic. Algorithm:

1. Detect swing pivots using a symmetric k-bar window.
2. Walk pivots chronologically. Track the last confirmed swing-high (LSH) and
   swing-low (LSL) plus the current bias (up / down / undecided).
3. Label each new pivot:
     * new pivot high > LSH  and bias is up   -> HH  (continuation of up)
     * new pivot high > LSH  and bias is down -> BOS-up (break of structure -> potential trend flip)
     * new pivot high < LSH  and bias is up   -> LH  (potential exhaustion)
     * new pivot low  < LSL  and bias is down -> LL  (continuation of down)
     * new pivot low  < LSL  and bias is up   -> BOS-down
     * new pivot low  > LSL  and bias is down -> HL  (potential exhaustion)
4. CHOCH (change of character) fires when the FIRST BOS after a confirmed
   trend flips the bias. Subsequent BOS events keep the new bias.

Every event carries: timestamp, price, type, timeframe, confidence, bars used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Sequence

from ..data.models import Candle


@dataclass
class Pivot:
    index: int
    timestamp: datetime
    price: float
    kind: str        # "high" / "low"


@dataclass
class StructureEvent:
    timestamp: datetime
    price: float
    type: str        # HH / HL / LH / LL / BOS_UP / BOS_DOWN / CHOCH_UP / CHOCH_DOWN
    timeframe: str
    confidence: int  # 1..3
    bars: int
    reason: str = ""


@dataclass
class StructureReport:
    bias: str                            # "up" / "down" / "undecided"
    last_swing_high: Optional[float]
    last_swing_low: Optional[float]
    events: List[StructureEvent] = field(default_factory=list)
    pivots: List[Pivot] = field(default_factory=list)


def _find_pivots(candles: Sequence[Candle], k: int = 3) -> List[Pivot]:
    pivots: List[Pivot] = []
    n = len(candles)
    if n < 2 * k + 1:
        return pivots
    for i in range(k, n - k):
        window = candles[i - k : i + k + 1]
        c = candles[i]
        highs = [x.high for x in window]
        lows = [x.low for x in window]
        if c.high == max(highs) and c.high > candles[i - 1].high and c.high > candles[i + 1].high:
            pivots.append(Pivot(index=i, timestamp=c.timestamp, price=c.high, kind="high"))
        if c.low == min(lows) and c.low < candles[i - 1].low and c.low < candles[i + 1].low:
            pivots.append(Pivot(index=i, timestamp=c.timestamp, price=c.low, kind="low"))
    pivots.sort(key=lambda p: (p.index, 0 if p.kind == "high" else 1))
    return pivots


def analyze(candles: Sequence[Candle], timeframe: str, pivot_k: int = 3) -> StructureReport:
    pivots = _find_pivots(candles, pivot_k)
    events: List[StructureEvent] = []
    bias = "undecided"
    lsh: Optional[Pivot] = None
    lsl: Optional[Pivot] = None
    bos_seen_in_bias = False

    for piv in pivots:
        if piv.kind == "high":
            if lsh is None:
                lsh = piv
                continue
            if piv.price > lsh.price:
                if bias == "down":
                    ev_type = "CHOCH_UP" if not bos_seen_in_bias else "BOS_UP"
                    events.append(StructureEvent(
                        timestamp=piv.timestamp, price=piv.price, type=ev_type,
                        timeframe=timeframe, confidence=3 if ev_type == "CHOCH_UP" else 2,
                        bars=piv.index - lsh.index,
                        reason=f"broke prior swing high {lsh.price}",
                    ))
                    bias = "up"
                    bos_seen_in_bias = True
                else:
                    events.append(StructureEvent(
                        timestamp=piv.timestamp, price=piv.price, type="HH",
                        timeframe=timeframe, confidence=2, bars=piv.index - lsh.index,
                        reason=f"higher high vs {lsh.price}",
                    ))
                    if bias == "undecided":
                        bias = "up"
                        bos_seen_in_bias = False
                lsh = piv
            else:
                events.append(StructureEvent(
                    timestamp=piv.timestamp, price=piv.price, type="LH",
                    timeframe=timeframe, confidence=1, bars=piv.index - lsh.index,
                    reason=f"lower high vs {lsh.price}",
                ))
                lsh = piv
        else:
            if lsl is None:
                lsl = piv
                continue
            if piv.price < lsl.price:
                if bias == "up":
                    ev_type = "CHOCH_DOWN" if not bos_seen_in_bias else "BOS_DOWN"
                    events.append(StructureEvent(
                        timestamp=piv.timestamp, price=piv.price, type=ev_type,
                        timeframe=timeframe, confidence=3 if ev_type == "CHOCH_DOWN" else 2,
                        bars=piv.index - lsl.index,
                        reason=f"broke prior swing low {lsl.price}",
                    ))
                    bias = "down"
                    bos_seen_in_bias = True
                else:
                    events.append(StructureEvent(
                        timestamp=piv.timestamp, price=piv.price, type="LL",
                        timeframe=timeframe, confidence=2, bars=piv.index - lsl.index,
                        reason=f"lower low vs {lsl.price}",
                    ))
                    if bias == "undecided":
                        bias = "down"
                        bos_seen_in_bias = False
                lsl = piv
            else:
                events.append(StructureEvent(
                    timestamp=piv.timestamp, price=piv.price, type="HL",
                    timeframe=timeframe, confidence=1, bars=piv.index - lsl.index,
                    reason=f"higher low vs {lsl.price}",
                ))
                lsl = piv

    return StructureReport(
        bias=bias,
        last_swing_high=lsh.price if lsh else None,
        last_swing_low=lsl.price if lsl else None,
        events=events,
        pivots=pivots,
    )
