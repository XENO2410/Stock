"""Technical indicators and level detection.

Pure functions operating on lists / numpy arrays; no external deps beyond numpy.
All indicators avoid look-ahead: they use only data up to the current bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np


# ---------------- Moving averages ----------------

def ema(values: Sequence[float], period: int) -> np.ndarray:
    """Exponential moving average."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0 or period <= 1:
        return arr.copy()
    k = 2.0 / (period + 1.0)
    out = np.empty_like(arr)
    out[0] = arr[0]
    for i in range(1, arr.size):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def sma(values: Sequence[float], period: int) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr.copy()
    out = np.full(arr.size, np.nan, dtype=float)
    if arr.size < period:
        return out
    csum = np.cumsum(arr)
    out[period - 1] = csum[period - 1] / period
    out[period:] = (csum[period:] - csum[:-period]) / period
    return out


# ---------------- Oscillators ----------------

def rsi(values: Sequence[float], period: int = 14) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size < period + 1:
        return np.full(arr.size, 50.0)
    delta = np.diff(arr, prepend=arr[0])
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros_like(arr)
    avg_loss = np.zeros_like(arr)
    avg_gain[period] = gains[1:period + 1].mean()
    avg_loss[period] = losses[1:period + 1].mean()
    for i in range(period + 1, arr.size):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period
    rs = np.where(avg_loss == 0, 100.0, avg_gain / np.where(avg_loss == 0, 1, avg_loss))
    out = 100 - 100 / (1 + rs)
    out[:period] = 50.0
    return out


def macd(values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ef = ema(values, fast)
    es = ema(values, slow)
    m = ef - es
    s = ema(m, signal)
    h = m - s
    return m, s, h


# ---------------- VWAP / ATR ----------------

def vwap(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[int]) -> float:
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    v = np.asarray(volumes, dtype=float)
    if v.sum() <= 0:
        return float(c[-1]) if c.size else 0.0
    tp = (h + l + c) / 3.0
    return float((tp * v).sum() / v.sum())


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if h.size < 2:
        return 0.0
    prev_c = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum.reduce([h - l, np.abs(h - prev_c), np.abs(l - prev_c)])
    if tr.size < period:
        return float(tr.mean())
    return float(tr[-period:].mean())


# ---------------- Levels ----------------

@dataclass
class Levels:
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float


def classic_pivots(prev_high: float, prev_low: float, prev_close: float) -> Levels:
    p = (prev_high + prev_low + prev_close) / 3.0
    r1 = 2 * p - prev_low
    s1 = 2 * p - prev_high
    r2 = p + (prev_high - prev_low)
    s2 = p - (prev_high - prev_low)
    r3 = prev_high + 2 * (p - prev_low)
    s3 = prev_low - 2 * (prev_high - p)
    return Levels(pivot=p, r1=r1, r2=r2, r3=r3, s1=s1, s2=s2, s3=s3)


def swing_levels(highs: Sequence[float], lows: Sequence[float], lookback: int = 60, cluster_bps: float = 40) -> Tuple[List[float], List[float]]:
    """Identify recent swing highs/lows and cluster nearby levels.

    Returns (supports_sorted_desc, resistances_sorted_asc). ``cluster_bps`` is
    the clustering tolerance in basis points of price.
    """
    h = np.asarray(highs[-lookback:], dtype=float)
    l = np.asarray(lows[-lookback:], dtype=float)
    if h.size < 5:
        return [], []
    swings_high: List[float] = []
    swings_low: List[float] = []
    for i in range(2, h.size - 2):
        if h[i] > h[i - 1] and h[i] > h[i - 2] and h[i] > h[i + 1] and h[i] > h[i + 2]:
            swings_high.append(float(h[i]))
        if l[i] < l[i - 1] and l[i] < l[i - 2] and l[i] < l[i + 1] and l[i] < l[i + 2]:
            swings_low.append(float(l[i]))

    def cluster(levels: List[float]) -> List[float]:
        if not levels:
            return []
        levels = sorted(levels)
        merged: List[List[float]] = [[levels[0]]]
        for v in levels[1:]:
            base = merged[-1][-1]
            if abs(v - base) / base * 10000 <= cluster_bps:
                merged[-1].append(v)
            else:
                merged.append([v])
        return [round(sum(grp) / len(grp), 2) for grp in merged]

    return cluster(swings_low), cluster(swings_high)


# ---------------- Aggregate snapshot ----------------

@dataclass
class IndicatorPack:
    price: float
    vwap: float
    ema9: float
    ema20: float
    ema50: float
    sma20: float
    rsi14: float
    macd: float
    macd_signal: float
    macd_hist: float
    atr14: float
    prev_day_high: float
    prev_day_low: float
    day_open: float
    opening_range_high: float
    opening_range_low: float
    support: List[float]
    resistance: List[float]
    pivot: float
    relative_volume: float
    trend_1m: str
    trend_5m: str
    trend_15m: str
    trend_overall: str


def classify_trend(closes: Sequence[float]) -> str:
    if len(closes) < 20:
        return "Insufficient"
    e9 = ema(closes, 9)[-1]
    e20 = ema(closes, 20)[-1]
    if e9 > e20 * 1.001:
        return "Bullish"
    if e9 < e20 * 0.999:
        return "Bearish"
    return "Neutral"
