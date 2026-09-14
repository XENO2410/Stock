"""Multi-timeframe alignment.

Runs a lightweight trend classification on each higher timeframe and reports
alignment. Uses whatever series the provider can produce; a missing TF is
simply skipped, not faked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..data.provider import MarketDataProvider
from .trend import classify as classify_trend


DEFAULT_TFS: List[str] = ["5m", "15m", "1h", "4h", "1d"]


@dataclass
class TFEntry:
    timeframe: str
    direction: str
    strength: int


@dataclass
class MTFReport:
    per_timeframe: List[TFEntry] = field(default_factory=list)
    overall: str = "undecided"      # "aligned_up" / "aligned_down" / "mixed" / "undecided"
    alignment_score: int = 0        # -3..+3
    reasons: List[str] = field(default_factory=list)


def analyze(provider: MarketDataProvider, symbol: str, timeframes: List[str] | None = None) -> MTFReport:
    tfs = timeframes or DEFAULT_TFS
    entries: List[TFEntry] = []
    score = 0
    for tf in tfs:
        series = provider.get_ohlcv(symbol, tf, limit=200)
        if len(series) < 20:
            continue
        verdict = classify_trend(series.candles)
        entries.append(TFEntry(timeframe=tf, direction=verdict.direction, strength=verdict.strength))
        if verdict.direction == "up":
            score += 1
        elif verdict.direction == "down":
            score -= 1

    if not entries:
        return MTFReport(per_timeframe=[], overall="undecided", alignment_score=0, reasons=["no timeframe data"])

    ups = sum(1 for e in entries if e.direction == "up")
    downs = sum(1 for e in entries if e.direction == "down")
    total = len(entries)
    reasons = [f"{e.timeframe}: {e.direction} (str {e.strength})" for e in entries]

    if ups == total:
        overall = "aligned_up"
    elif downs == total:
        overall = "aligned_down"
    elif ups >= total * 0.7:
        overall = "aligned_up"
    elif downs >= total * 0.7:
        overall = "aligned_down"
    elif ups > 0 and downs > 0:
        overall = "mixed"
    else:
        overall = "undecided"

    return MTFReport(
        per_timeframe=entries,
        overall=overall,
        alignment_score=score,
        reasons=reasons,
    )
