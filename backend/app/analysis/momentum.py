"""Momentum classification: RSI, MACD, ROC, plus divergence hints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from ..core import indicators as ind
from ..data.models import Candle


@dataclass
class MomentumVerdict:
    rsi14: float
    macd: float
    macd_signal: float
    macd_hist: float
    roc10: float
    verdict: str        # "bullish" / "bearish" / "neutral" / "overextended_up" / "overextended_down"
    reasons: List[str]
    divergence: Optional[str] = None  # "bullish" / "bearish" / None


def _roc(values: np.ndarray, period: int = 10) -> float:
    if values.size < period + 1 or values[-period - 1] == 0:
        return 0.0
    return float((values[-1] - values[-period - 1]) / abs(values[-period - 1]) * 100.0)


def _detect_divergence(price: np.ndarray, osc: np.ndarray, lookback: int = 20) -> Optional[str]:
    """Classic regular divergence between price and RSI, over `lookback` bars."""
    if price.size < lookback or osc.size < lookback:
        return None
    p = price[-lookback:]
    o = osc[-lookback:]
    p_hi_idx = int(np.argmax(p))
    p_lo_idx = int(np.argmin(p))
    # Bearish: price higher high, oscillator lower high
    if p_hi_idx > 0 and p[-1] > p[p_hi_idx - 1] * 1.001 and o[-1] < o[p_hi_idx - 1]:
        return "bearish"
    # Bullish: price lower low, oscillator higher low
    if p_lo_idx > 0 and p[-1] < p[p_lo_idx - 1] * 0.999 and o[-1] > o[p_lo_idx - 1]:
        return "bullish"
    return None


def classify(candles: List[Candle]) -> MomentumVerdict:
    reasons: List[str] = []
    if len(candles) < 30:
        return MomentumVerdict(50, 0, 0, 0, 0, "neutral", ["insufficient history"], None)
    closes = np.array([c.close for c in candles], dtype=float)
    rsi_series = ind.rsi(closes, 14)
    rsi = float(rsi_series[-1])
    macd_series, macd_sig, macd_hist = ind.macd(closes)
    m = float(macd_series[-1])
    s = float(macd_sig[-1])
    h = float(macd_hist[-1])
    roc = _roc(closes)

    verdict = "neutral"
    if rsi > 78:
        verdict = "overextended_up"
        reasons.append(f"RSI {rsi:.1f} overextended")
    elif rsi < 22:
        verdict = "overextended_down"
        reasons.append(f"RSI {rsi:.1f} overextended")
    elif rsi > 55 and h > 0 and roc > 0:
        verdict = "bullish"
        reasons.append(f"RSI {rsi:.1f}, MACD+, ROC {roc:+.2f}%")
    elif rsi < 45 and h < 0 and roc < 0:
        verdict = "bearish"
        reasons.append(f"RSI {rsi:.1f}, MACD-, ROC {roc:+.2f}%")
    else:
        reasons.append(f"RSI {rsi:.1f}, MACD hist {h:+.3f}")

    div = _detect_divergence(closes, rsi_series)
    if div:
        reasons.append(f"{div} divergence vs RSI")

    return MomentumVerdict(
        rsi14=round(rsi, 2),
        macd=round(m, 4),
        macd_signal=round(s, 4),
        macd_hist=round(h, 4),
        roc10=round(roc, 2),
        verdict=verdict,
        reasons=reasons,
        divergence=div,
    )
