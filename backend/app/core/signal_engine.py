"""Signal engine.

Given live candles + indicators + depth, produce a weighted, transparent
buy/sell/no-trade recommendation with entry, SL, targets, R:R and a
per-category scoring breakdown that users can inspect.

Design goals:
  * Multi-factor, not single indicator
  * Configurable weights (from UserSettings.signal_weights)
  * Explicit "NO TRADE" is a first-class output
  * Every reason is human readable
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import indicators as ind
from .mock_market import Candle, MockMarket, TIMEFRAMES


DEFAULT_WEIGHTS: Dict[str, int] = {
    "trend": 20,
    "vwap": 15,
    "ema": 12,
    "volume": 15,
    "price_action": 15,
    "order_book": 10,
    "momentum": 8,
    "mtf": 5,
}

MIN_HISTORY = 30


@dataclass
class SignalResult:
    symbol: str
    direction: str  # LONG / SHORT / NONE
    action: str     # STRONG_BUY / BUY / NO_TRADE / SELL / STRONG_SELL
    confidence: int
    entry_low: float
    entry_high: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    strategy: str
    timeframe: str
    valid_until: Optional[datetime]
    invalidation: str
    breakdown: Dict[str, Dict[str, int | str]] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)


def _to_arrays(candles: List[Candle]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    o = np.array([c.o for c in candles], dtype=float)
    h = np.array([c.h for c in candles], dtype=float)
    l = np.array([c.l for c in candles], dtype=float)
    c_ = np.array([c.c for c in candles], dtype=float)
    v = np.array([c.v for c in candles], dtype=int)
    return o, h, l, c_, v


def build_indicator_pack(symbol: str, timeframe: str = "5m", market: Optional[MockMarket] = None) -> Optional[ind.IndicatorPack]:
    market = market or MockMarket.instance()
    candles = market.get_candles(symbol, timeframe, limit=300)
    if len(candles) < MIN_HISTORY:
        return None
    o, h, l, c, v = _to_arrays(candles)

    e9 = ind.ema(c, 9)[-1]
    e20 = ind.ema(c, 20)[-1]
    e50 = ind.ema(c, 50)[-1]
    s20 = ind.sma(c, 20)[-1]
    rsi_val = ind.rsi(c, 14)[-1]
    m, s, hist = ind.macd(c)
    atr_val = ind.atr(h, l, c, 14)
    vwap_val = ind.vwap(h, l, c, v)

    # Day open / previous day high-low estimation
    # Group by IST day using timestamps of 1m candles
    ones = market.get_candles(symbol, "1m", limit=1000)
    if ones:
        day_open = ones[0].o if ones else float(c[0])
        # Prev day = candles before start of today (approx by ts date)
        today = ones[-1].t.date()
        prev = [x for x in ones if x.t.date() < today]
        if prev:
            prev_day_high = max(x.h for x in prev)
            prev_day_low = min(x.l for x in prev)
        else:
            # Fall back to earlier portion of session
            head = ones[: max(30, len(ones) // 5)]
            prev_day_high = max(x.h for x in head)
            prev_day_low = min(x.l for x in head)
        # Opening range = first 15 minutes today
        today_ones = [x for x in ones if x.t.date() == today]
        or_slice = today_ones[:15] if today_ones else ones[:15]
        opening_range_high = max(x.h for x in or_slice) if or_slice else float(h[0])
        opening_range_low = min(x.l for x in or_slice) if or_slice else float(l[0])
    else:
        day_open = float(c[0])
        prev_day_high = float(np.max(h[: max(1, len(h) // 3)]))
        prev_day_low = float(np.min(l[: max(1, len(l) // 3)]))
        opening_range_high = float(h[0])
        opening_range_low = float(l[0])

    # Pivots
    pivots = ind.classic_pivots(prev_day_high, prev_day_low, float(c[0]))
    supports, resistances = ind.swing_levels(h.tolist(), l.tolist(), lookback=120)
    # Combine with pivots
    supports = sorted({round(x, 2) for x in supports + [pivots.s1, pivots.s2, pivots.s3, prev_day_low]}, reverse=True)[:5]
    resistances = sorted({round(x, 2) for x in resistances + [pivots.r1, pivots.r2, pivots.r3, prev_day_high]})[:5]

    # Relative volume: avg of last 5 vs avg of last 30
    if v.size >= 30:
        avg_recent = float(v[-5:].mean()) or 1.0
        avg_base = float(v[-30:].mean()) or 1.0
        rel_vol = avg_recent / max(avg_base, 1.0)
    else:
        rel_vol = 1.0

    # Trends across timeframes
    t1 = ind.classify_trend([x.c for x in market.get_candles(symbol, "1m", limit=60)])
    t5 = ind.classify_trend([x.c for x in market.get_candles(symbol, "5m", limit=60)])
    t15 = ind.classify_trend([x.c for x in market.get_candles(symbol, "15m", limit=60)])
    overall = _mtf_overall([t1, t5, t15])

    return ind.IndicatorPack(
        price=float(c[-1]),
        vwap=vwap_val,
        ema9=float(e9),
        ema20=float(e20),
        ema50=float(e50),
        sma20=float(s20) if not np.isnan(s20) else float(c[-1]),
        rsi14=float(rsi_val),
        macd=float(m[-1]),
        macd_signal=float(s[-1]),
        macd_hist=float(hist[-1]),
        atr14=float(atr_val),
        prev_day_high=float(prev_day_high),
        prev_day_low=float(prev_day_low),
        day_open=float(day_open),
        opening_range_high=float(opening_range_high),
        opening_range_low=float(opening_range_low),
        support=supports,
        resistance=resistances,
        pivot=float(pivots.pivot),
        relative_volume=round(rel_vol, 2),
        trend_1m=t1,
        trend_5m=t5,
        trend_15m=t15,
        trend_overall=overall,
    )


def _mtf_overall(trends: List[str]) -> str:
    score = 0
    for t in trends:
        score += 1 if t == "Bullish" else -1 if t == "Bearish" else 0
    if score >= 2:
        return "Bullish"
    if score <= -2:
        return "Bearish"
    if score == 1:
        return "Moderately Bullish"
    if score == -1:
        return "Moderately Bearish"
    return "Neutral"


# ---------------- Scoring ----------------

def _score(price: float, pack: ind.IndicatorPack, depth: Optional[Dict], weights: Dict[str, int], direction: str) -> Tuple[int, Dict[str, Dict[str, int | str]], List[str]]:
    """Score a hypothetical LONG or SHORT setup.

    Returns (confidence 0-100, breakdown dict, human reasons list).
    """
    sign = 1 if direction == "LONG" else -1
    breakdown: Dict[str, Dict[str, int | str]] = {}
    reasons: List[str] = []

    # --- Trend ---
    trend_ok = (pack.trend_overall in ("Bullish", "Moderately Bullish") and sign > 0) or (
        pack.trend_overall in ("Bearish", "Moderately Bearish") and sign < 0
    )
    strong = pack.trend_overall in ("Bullish", "Bearish")
    trend_score = weights["trend"] if trend_ok and strong else int(weights["trend"] * 0.5) if trend_ok else 0
    breakdown["Trend"] = {"verdict": pack.trend_overall, "score": trend_score, "max": weights["trend"]}
    if trend_ok:
        reasons.append(f"Trend {pack.trend_overall} aligned with {direction}")

    # --- VWAP ---
    dist = (price - pack.vwap) / pack.vwap * 100 if pack.vwap else 0.0
    vwap_ok = (dist > 0 and sign > 0) or (dist < 0 and sign < 0)
    overextended = abs(dist) > 2.0
    if vwap_ok and not overextended:
        vwap_score = weights["vwap"]
        reasons.append(f"Price {'above' if sign>0 else 'below'} VWAP ({dist:+.2f}%)")
    elif vwap_ok and overextended:
        vwap_score = int(weights["vwap"] * 0.4)
        reasons.append(f"VWAP aligned but extended ({dist:+.2f}%)")
    else:
        vwap_score = 0
    breakdown["VWAP"] = {"verdict": f"{'Above' if dist>=0 else 'Below'} by {abs(dist):.2f}%", "score": vwap_score, "max": weights["vwap"]}

    # --- EMA alignment ---
    ema_bull = pack.ema9 > pack.ema20 > pack.ema50
    ema_bear = pack.ema9 < pack.ema20 < pack.ema50
    ema_ok = (ema_bull and sign > 0) or (ema_bear and sign < 0)
    ema_score = weights["ema"] if ema_ok else int(weights["ema"] * 0.4) if ((pack.ema9 > pack.ema20) if sign > 0 else (pack.ema9 < pack.ema20)) else 0
    breakdown["EMA"] = {"verdict": "Bullish stack" if ema_bull else "Bearish stack" if ema_bear else "Mixed", "score": ema_score, "max": weights["ema"]}
    if ema_ok:
        reasons.append("EMA 9/20/50 stacked in trade direction")

    # --- Volume ---
    rvol = pack.relative_volume
    if rvol >= 2.0:
        vol_score = weights["volume"]
        vol_verdict = f"Strong ({rvol:.1f}x)"
        reasons.append(f"Volume surge {rvol:.1f}x average")
    elif rvol >= 1.4:
        vol_score = int(weights["volume"] * 0.7)
        vol_verdict = f"Above avg ({rvol:.1f}x)"
    elif rvol >= 1.0:
        vol_score = int(weights["volume"] * 0.35)
        vol_verdict = f"Normal ({rvol:.1f}x)"
    else:
        vol_score = 0
        vol_verdict = f"Weak ({rvol:.1f}x)"
    breakdown["Volume"] = {"verdict": vol_verdict, "score": vol_score, "max": weights["volume"]}

    # --- Price action ---
    pa_score = 0
    pa_verdict = "Neutral"
    if sign > 0:
        if price > pack.opening_range_high:
            pa_score = weights["price_action"]; pa_verdict = "ORB breakout"; reasons.append("Breakout above opening range high")
        elif price > pack.prev_day_high:
            pa_score = int(weights["price_action"] * 0.9); pa_verdict = "Prev day high break"; reasons.append("Breakout above previous day high")
        elif pack.resistance and price > pack.resistance[0]:
            pa_score = int(weights["price_action"] * 0.8); pa_verdict = "Resistance broken"
            reasons.append(f"Broke resistance {pack.resistance[0]}")
        elif pack.support and abs(price - pack.support[0]) / price * 100 < 0.4:
            pa_score = int(weights["price_action"] * 0.6); pa_verdict = "Support bounce"; reasons.append(f"Bounce near support {pack.support[0]}")
    else:
        if price < pack.opening_range_low:
            pa_score = weights["price_action"]; pa_verdict = "ORB breakdown"; reasons.append("Breakdown below opening range low")
        elif price < pack.prev_day_low:
            pa_score = int(weights["price_action"] * 0.9); pa_verdict = "Prev day low break"; reasons.append("Breakdown below previous day low")
        elif pack.support and price < pack.support[0]:
            pa_score = int(weights["price_action"] * 0.8); pa_verdict = "Support broken"
            reasons.append(f"Broke support {pack.support[0]}")
        elif pack.resistance and abs(price - pack.resistance[0]) / price * 100 < 0.4:
            pa_score = int(weights["price_action"] * 0.6); pa_verdict = "Resistance rejection"; reasons.append(f"Rejection near resistance {pack.resistance[0]}")
    breakdown["Price Action"] = {"verdict": pa_verdict, "score": pa_score, "max": weights["price_action"]}

    # --- Order book / depth ---
    ob_score = 0
    ob_verdict = "n/a"
    if depth is not None:
        imb = depth.get("imbalance_pct", 0)
        # positive imbalance = bid dominance
        if (imb > 15 and sign > 0) or (imb < -15 and sign < 0):
            ob_score = weights["order_book"]
            ob_verdict = f"Aligned imbalance {imb:+.0f}%"
            reasons.append(f"Order book imbalance {imb:+.0f}% supports {direction}")
        elif (imb > 5 and sign > 0) or (imb < -5 and sign < 0):
            ob_score = int(weights["order_book"] * 0.5)
            ob_verdict = f"Mild imbalance {imb:+.0f}%"
        else:
            ob_verdict = f"Neutral {imb:+.0f}%"
    breakdown["Order Book"] = {"verdict": ob_verdict, "score": ob_score, "max": weights["order_book"]}

    # --- Momentum (RSI + MACD) ---
    rsi_ok = (pack.rsi14 > 55 and sign > 0) or (pack.rsi14 < 45 and sign < 0)
    macd_ok = (pack.macd_hist > 0 and sign > 0) or (pack.macd_hist < 0 and sign < 0)
    momentum_score = 0
    if rsi_ok and macd_ok:
        momentum_score = weights["momentum"]
        reasons.append("RSI and MACD confirm momentum")
    elif rsi_ok or macd_ok:
        momentum_score = int(weights["momentum"] * 0.5)
    # Overextension warning
    if (pack.rsi14 > 78 and sign > 0) or (pack.rsi14 < 22 and sign < 0):
        momentum_score = max(0, momentum_score - 2)
        reasons.append(f"Momentum extended (RSI {pack.rsi14:.0f}) - use caution")
    breakdown["Momentum"] = {"verdict": f"RSI {pack.rsi14:.0f} MACD {'+' if pack.macd_hist>=0 else '-'}", "score": momentum_score, "max": weights["momentum"]}

    # --- Multi-timeframe alignment ---
    mtf_matches = sum(1 for t in (pack.trend_1m, pack.trend_5m, pack.trend_15m) if (t == "Bullish" and sign > 0) or (t == "Bearish" and sign < 0))
    mtf_score = int(weights["mtf"] * (mtf_matches / 3.0))
    breakdown["Multi-TF"] = {"verdict": f"{mtf_matches}/3 aligned", "score": mtf_score, "max": weights["mtf"]}
    if mtf_matches == 3:
        reasons.append("All 3 timeframes aligned")

    total = trend_score + vwap_score + ema_score + vol_score + pa_score + ob_score + momentum_score + mtf_score
    max_total = sum(weights.values())
    confidence = int(round(total / max_total * 100))
    return confidence, breakdown, reasons


def _label(confidence: int, direction: str, min_conf: int) -> Tuple[str, str]:
    if confidence < min_conf:
        return "NONE", "NO_TRADE"
    if direction == "LONG":
        return ("LONG", "STRONG_BUY" if confidence >= 85 else "BUY")
    return ("SHORT", "STRONG_SELL" if confidence >= 85 else "SELL")


def evaluate(
    symbol: str,
    weights: Optional[Dict[str, int]] = None,
    min_confidence: int = 70,
    timeframe: str = "5m",
    market: Optional[MockMarket] = None,
) -> Optional[SignalResult]:
    market = market or MockMarket.instance()
    if market.is_index(symbol):
        return None
    pack = build_indicator_pack(symbol, timeframe=timeframe, market=market)
    if pack is None:
        return None
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    depth = market.get_depth(symbol, levels=5)

    price = pack.price

    long_conf, long_bd, long_reasons = _score(price, pack, depth, weights, "LONG")
    short_conf, short_bd, short_reasons = _score(price, pack, depth, weights, "SHORT")

    if long_conf >= short_conf:
        direction_prefer, conf, breakdown, reasons = "LONG", long_conf, long_bd, long_reasons
    else:
        direction_prefer, conf, breakdown, reasons = "SHORT", short_conf, short_bd, short_reasons

    direction, action = _label(conf, direction_prefer, min_confidence)

    # Build entry/SL/targets from ATR + structural levels
    atr_val = max(pack.atr14, price * 0.002)
    if direction == "LONG":
        entry_low = round(price - 0.05, 2)
        entry_high = round(price + atr_val * 0.15, 2)
        sl = round(min(pack.support[0] if pack.support else price - atr_val, price - atr_val), 2)
        risk = max(0.05, entry_high - sl)
        t1 = round(entry_high + risk * 1.5, 2)
        t2 = round(entry_high + risk * 2.5, 2)
        # Snap toward nearest resistance if closer
        if pack.resistance:
            for r in pack.resistance:
                if r > entry_high:
                    t1 = min(t1, round(r, 2))
                    break
        rr = round((t1 - entry_high) / risk, 2)
        invalidation = f"Close below {sl:.2f} or loss of VWAP {pack.vwap:.2f}"
    elif direction == "SHORT":
        entry_high = round(price + 0.05, 2)
        entry_low = round(price - atr_val * 0.15, 2)
        sl = round(max(pack.resistance[0] if pack.resistance else price + atr_val, price + atr_val), 2)
        risk = max(0.05, sl - entry_low)
        t1 = round(entry_low - risk * 1.5, 2)
        t2 = round(entry_low - risk * 2.5, 2)
        if pack.support:
            for s in pack.support:
                if s < entry_low:
                    t1 = max(t1, round(s, 2))
                    break
        rr = round((entry_low - t1) / risk, 2)
        invalidation = f"Close above {sl:.2f} or reclaim of VWAP {pack.vwap:.2f}"
    else:
        entry_low = entry_high = round(price, 2)
        sl = t1 = t2 = 0.0
        rr = 0.0
        invalidation = "Setup does not meet minimum confidence"
        if not reasons:
            reasons = [
                "Price between support and resistance",
                "Volume confirmation weak",
                "Risk/reward poor",
                f"Confidence {conf} below threshold {min_confidence}",
            ]

    valid_until = datetime.now(timezone.utc) + timedelta(minutes=15) if direction != "NONE" else None

    strategy = _strategy_name(pack, direction)

    return SignalResult(
        symbol=symbol,
        direction=direction,
        action=action,
        confidence=conf,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=sl,
        target_1=t1,
        target_2=t2,
        risk_reward=rr,
        strategy=strategy,
        timeframe=timeframe,
        valid_until=valid_until,
        invalidation=invalidation,
        breakdown=breakdown,
        reasons=reasons,
    )


def _strategy_name(pack: ind.IndicatorPack, direction: str) -> str:
    if direction == "NONE":
        return "none"
    price = pack.price
    if price > pack.opening_range_high or price < pack.opening_range_low:
        return "orb"
    if price > pack.prev_day_high or price < pack.prev_day_low:
        return "breakout"
    if abs(price - pack.vwap) / price * 100 < 0.3:
        return "pullback"
    return "trend_vwap"


def evaluate_universe(min_confidence: int = 70) -> List[SignalResult]:
    market = MockMarket.instance()
    out: List[SignalResult] = []
    for s in market.universe():
        res = evaluate(s["symbol"], min_confidence=min_confidence)
        if res is not None:
            out.append(res)
    return out


def exit_recommendation(
    symbol: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    target_1: float,
    target_2: float,
    market: Optional[MockMarket] = None,
) -> Dict[str, str]:
    """Recommend HOLD / BOOK_PARTIAL / EXIT for an open position."""
    market = market or MockMarket.instance()
    pack = build_indicator_pack(symbol, timeframe="5m", market=market)
    if pack is None:
        return {"recommendation": "HOLD", "reason": "Insufficient data"}
    price = pack.price
    sign = 1 if direction == "LONG" else -1

    # Stop loss
    if (sign > 0 and price <= stop_loss) or (sign < 0 and price >= stop_loss):
        return {"recommendation": "EXIT", "reason": "Stop loss hit"}

    # Target hit
    if target_1 and ((sign > 0 and price >= target_1) or (sign < 0 and price <= target_1)):
        return {"recommendation": "BOOK_PARTIAL", "reason": "Target 1 reached - consider booking 50%"}

    # Trend reversal
    if (sign > 0 and pack.trend_overall in ("Bearish", "Moderately Bearish")) or (
        sign < 0 and pack.trend_overall in ("Bullish", "Moderately Bullish")
    ):
        return {"recommendation": "EXIT", "reason": f"Trend flipped to {pack.trend_overall}"}

    # VWAP loss
    if sign > 0 and price < pack.vwap and pack.ema9 < pack.ema20:
        return {"recommendation": "EXIT", "reason": "Lost VWAP and EMA9<EMA20"}
    if sign < 0 and price > pack.vwap and pack.ema9 > pack.ema20:
        return {"recommendation": "EXIT", "reason": "Reclaimed VWAP and EMA9>EMA20"}

    # Approaching target
    if target_1 and abs(price - target_1) / price * 100 < 0.15:
        return {"recommendation": "BOOK_PARTIAL", "reason": "Approaching target 1"}

    return {"recommendation": "HOLD", "reason": "Trade thesis remains valid"}
