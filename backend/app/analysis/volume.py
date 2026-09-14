"""Volume analysis: relative volume, spikes, and price/volume relation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from ..data.models import Candle


@dataclass
class VolumeVerdict:
    relative_volume: float   # last-5-avg / last-30-avg
    is_spike: bool           # last candle >= 2x its 30-avg
    trend: str               # "expanding" / "contracting" / "steady"
    confirms_move: bool      # last-candle direction is supported by above-average volume
    reasons: List[str]


def classify(candles: List[Candle]) -> VolumeVerdict:
    reasons: List[str] = []
    if len(candles) < 30 or not any(c.volume > 0 for c in candles):
        return VolumeVerdict(1.0, False, "steady", False, ["no volume data"])
    vols = np.array([c.volume for c in candles], dtype=float)
    last5 = float(vols[-5:].mean()) or 1.0
    last30 = float(vols[-30:].mean()) or 1.0
    rvol = last5 / last30 if last30 > 0 else 1.0

    is_spike = bool(vols[-1] >= last30 * 2.0)
    if is_spike:
        reasons.append(f"volume spike {vols[-1]/last30:.1f}x avg")

    if rvol >= 1.4:
        trend = "expanding"
        reasons.append(f"expanding volume RVol {rvol:.2f}x")
    elif rvol <= 0.7:
        trend = "contracting"
        reasons.append(f"contracting volume RVol {rvol:.2f}x")
    else:
        trend = "steady"

    last = candles[-1]
    prev_close = candles[-2].close if len(candles) >= 2 else last.close
    price_up = last.close > prev_close
    price_down = last.close < prev_close
    confirms = bool(
        (price_up and vols[-1] >= last30) or (price_down and vols[-1] >= last30)
    )
    if confirms:
        reasons.append("move confirmed by above-average volume")

    return VolumeVerdict(
        relative_volume=round(rvol, 2),
        is_spike=is_spike,
        trend=trend,
        confirms_move=confirms,
        reasons=reasons,
    )
