"""Confluence engine.

Takes structured facts from the analysis modules and produces:
  * positive_evidence[]
  * negative_evidence[]
  * warnings[]
  * score  (0-100, clamped)
  * signal (BUY / SELL / WAIT — WAIT is the default)
  * trade_plan (entry_zone, stop, target_1, target_2, risk_reward) when signal != WAIT

Correlated inputs are **grouped** so overlapping evidence doesn't double-count.
The score is bounded per group by group_max weights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core import indicators as ind
from ..data.models import Candle
from .breakout import BreakoutEvent
from .momentum import MomentumVerdict
from .multi_timeframe import MTFReport
from .reversal import ReversalVerdict
from .structure import StructureReport
from .support_resistance import Zone, nearest
from .trend import TrendVerdict
from .volume import VolumeVerdict


@dataclass
class TradePlan:
    entry_low: float
    entry_high: float
    stop: float
    target_1: float
    target_2: float
    risk_reward: float


@dataclass
class ConfluenceResult:
    signal: str                        # BUY / SELL / WAIT
    score: int                         # 0..100
    bias: str                          # up / down / neutral
    positive_evidence: List[str] = field(default_factory=list)
    negative_evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    trade_plan: Optional[TradePlan] = None
    group_scores: Dict[str, int] = field(default_factory=dict)


# Group weights - the max contribution each correlated group can give.
GROUP_WEIGHTS: Dict[str, int] = {
    "trend_and_momentum": 22,     # trend + momentum are correlated
    "structure": 20,              # HH/HL/LH/LL + BOS + CHOCH
    "price_action": 15,           # candles, retest, rejection
    "support_resistance": 12,     # room to target
    "volume": 10,
    "multi_timeframe": 12,
    "breakout": 9,
}


def _clip(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(value))))


def _bias_from_signals(trend: TrendVerdict, structure: StructureReport, mtf: MTFReport) -> str:
    up = (trend.direction == "up") + (structure.bias == "up") + (mtf.overall == "aligned_up")
    down = (trend.direction == "down") + (structure.bias == "down") + (mtf.overall == "aligned_down")
    if up > down and up >= 2:
        return "up"
    if down > up and down >= 2:
        return "down"
    return "neutral"


def evaluate(
    candles: List[Candle],
    trend: TrendVerdict,
    momentum: MomentumVerdict,
    volume: VolumeVerdict,
    structure: StructureReport,
    zones: List[Zone],
    mtf: MTFReport,
    breakout: Optional[BreakoutEvent],
    reversal: ReversalVerdict,
    min_risk_reward: float = 1.5,
) -> ConfluenceResult:
    if len(candles) < 30:
        return ConfluenceResult(
            signal="WAIT",
            score=0,
            bias="neutral",
            warnings=["insufficient history"],
        )

    price = candles[-1].close
    bias = _bias_from_signals(trend, structure, mtf)

    pos: List[str] = []
    neg: List[str] = []
    warn: List[str] = []
    groups: Dict[str, int] = {}

    # ---------------- Trend + Momentum (correlated group) ----------------
    tm_score = 0
    if bias == "up":
        if trend.direction == "up":
            tm_score += 7 * max(1, trend.strength)
            pos.extend(trend.reasons)
        if momentum.verdict == "bullish":
            tm_score += 8
            pos.extend(momentum.reasons)
        if momentum.verdict == "bearish":
            tm_score -= 8
            neg.extend(momentum.reasons)
        if momentum.verdict == "overextended_up":
            tm_score -= 4
            warn.append("momentum overextended - beware pullback")
    elif bias == "down":
        if trend.direction == "down":
            tm_score += 7 * max(1, trend.strength)
            pos.extend(trend.reasons)
        if momentum.verdict == "bearish":
            tm_score += 8
            pos.extend(momentum.reasons)
        if momentum.verdict == "bullish":
            tm_score -= 8
            neg.extend(momentum.reasons)
        if momentum.verdict == "overextended_down":
            tm_score -= 4
            warn.append("momentum overextended - beware bounce")
    groups["trend_and_momentum"] = _clip(tm_score, 0, GROUP_WEIGHTS["trend_and_momentum"])

    # ---------------- Structure ----------------
    st_score = 0
    last_events = [e.type for e in structure.events[-5:]]
    if bias == "up":
        if any(t in last_events for t in ("BOS_UP", "CHOCH_UP")):
            st_score += 14
            pos.append("recent BOS/CHOCH up")
        if any(t == "HH" for t in last_events) and any(t == "HL" for t in last_events):
            st_score += 6
            pos.append("HH + HL sequence")
        if "CHOCH_DOWN" in last_events:
            st_score -= 12
            neg.append("recent CHOCH down contradicts bias")
    elif bias == "down":
        if any(t in last_events for t in ("BOS_DOWN", "CHOCH_DOWN")):
            st_score += 14
            pos.append("recent BOS/CHOCH down")
        if any(t == "LH" for t in last_events) and any(t == "LL" for t in last_events):
            st_score += 6
            pos.append("LH + LL sequence")
        if "CHOCH_UP" in last_events:
            st_score -= 12
            neg.append("recent CHOCH up contradicts bias")
    groups["structure"] = _clip(st_score, 0, GROUP_WEIGHTS["structure"])

    # ---------------- Price action (retest, rejection, reversal cleanup) ----------------
    pa_score = 0
    if breakout:
        if bias == "up" and breakout.kind in ("breakout_up", "retest"):
            pa_score += 8 + breakout.strength
            pos.extend(breakout.reasons)
        elif bias == "down" and breakout.kind in ("breakdown", "retest"):
            pa_score += 8 + breakout.strength
            pos.extend(breakout.reasons)
        elif breakout.kind == "failed_breakout":
            pa_score -= 6
            neg.append("failed breakout warning")
    if reversal.direction and reversal.direction != bias and reversal.strength >= 2:
        pa_score -= 6
        neg.append("reversal signals against current bias")
    groups["price_action"] = _clip(pa_score, 0, GROUP_WEIGHTS["price_action"])

    # ---------------- Support / resistance room ----------------
    sr_score = 0
    if bias == "up":
        r = nearest(zones, price, "resistance")
        if r:
            dist_pct = (r.mid - price) / price * 100
            if dist_pct >= 1.0:
                sr_score += 10
                pos.append(f"resistance {r.price_low:.2f}-{r.price_high:.2f} is {dist_pct:.2f}% away")
            elif dist_pct <= 0.4:
                sr_score -= 6
                neg.append(f"resistance too close ({dist_pct:.2f}%)")
                warn.append("room to target 1 is limited")
    elif bias == "down":
        s = nearest(zones, price, "support")
        if s:
            dist_pct = (price - s.mid) / price * 100
            if dist_pct >= 1.0:
                sr_score += 10
                pos.append(f"support {s.price_low:.2f}-{s.price_high:.2f} is {dist_pct:.2f}% away")
            elif dist_pct <= 0.4:
                sr_score -= 6
                neg.append(f"support too close ({dist_pct:.2f}%)")
                warn.append("room to target 1 is limited")
    groups["support_resistance"] = _clip(sr_score, 0, GROUP_WEIGHTS["support_resistance"])

    # ---------------- Volume ----------------
    v_score = 0
    if volume.confirms_move:
        v_score += 5
        pos.append("volume confirms the last move")
    if volume.trend == "expanding":
        v_score += 3
    if volume.trend == "contracting":
        v_score -= 2
        warn.append("contracting volume")
    if volume.is_spike:
        v_score += 2
    groups["volume"] = _clip(v_score, 0, GROUP_WEIGHTS["volume"])

    # ---------------- Multi-timeframe ----------------
    mtf_score = 0
    if bias == "up" and mtf.overall == "aligned_up":
        mtf_score = GROUP_WEIGHTS["multi_timeframe"]
        pos.append("multi-timeframe aligned up")
    elif bias == "down" and mtf.overall == "aligned_down":
        mtf_score = GROUP_WEIGHTS["multi_timeframe"]
        pos.append("multi-timeframe aligned down")
    elif mtf.overall == "mixed":
        mtf_score = 3
        warn.append("mixed multi-timeframe picture")
    groups["multi_timeframe"] = _clip(mtf_score, 0, GROUP_WEIGHTS["multi_timeframe"])

    # ---------------- Breakout as its own group ----------------
    bo_score = 0
    if breakout and bias == "up" and breakout.kind == "breakout_up":
        bo_score = min(GROUP_WEIGHTS["breakout"], 3 + breakout.strength * 2)
    elif breakout and bias == "down" and breakout.kind == "breakdown":
        bo_score = min(GROUP_WEIGHTS["breakout"], 3 + breakout.strength * 2)
    groups["breakout"] = _clip(bo_score, 0, GROUP_WEIGHTS["breakout"])

    total = sum(groups.values())
    score = _clip(total)

    # ---------------- Trade plan ----------------
    plan: Optional[TradePlan] = None
    atr = ind.atr([c.high for c in candles], [c.low for c in candles], [c.close for c in candles], 14)
    atr = max(atr, price * 0.002)

    if bias == "up" and score >= 65:
        entry_low = round(price - 0.05, 2)
        entry_high = round(price + atr * 0.2, 2)
        struct_stop = structure.last_swing_low or (price - atr * 1.5)
        stop = round(min(struct_stop, price - atr), 2)
        risk = max(0.05, entry_high - stop)
        t1 = round(entry_high + risk * 1.5, 2)
        t2 = round(entry_high + risk * 2.5, 2)
        r = nearest(zones, price, "resistance")
        if r and r.mid > entry_high:
            t1 = min(t1, round(r.mid, 2))
        rr = round((t1 - entry_high) / risk, 2) if risk else 0.0
        if rr >= min_risk_reward:
            plan = TradePlan(entry_low, entry_high, stop, t1, t2, rr)
        else:
            warn.append(f"risk/reward {rr:.2f} below min {min_risk_reward}")
    elif bias == "down" and score >= 65:
        entry_high = round(price + 0.05, 2)
        entry_low = round(price - atr * 0.2, 2)
        struct_stop = structure.last_swing_high or (price + atr * 1.5)
        stop = round(max(struct_stop, price + atr), 2)
        risk = max(0.05, stop - entry_low)
        t1 = round(entry_low - risk * 1.5, 2)
        t2 = round(entry_low - risk * 2.5, 2)
        s = nearest(zones, price, "support")
        if s and s.mid < entry_low:
            t1 = max(t1, round(s.mid, 2))
        rr = round((entry_low - t1) / risk, 2) if risk else 0.0
        if rr >= min_risk_reward:
            plan = TradePlan(entry_low, entry_high, stop, t1, t2, rr)
        else:
            warn.append(f"risk/reward {rr:.2f} below min {min_risk_reward}")

    # ---------------- Decision ----------------
    signal = "WAIT"
    if plan and bias == "up" and score >= 65:
        signal = "BUY"
    elif plan and bias == "down" and score >= 65:
        signal = "SELL"
    else:
        if score < 45:
            warn.append("insufficient evidence")
        elif not plan:
            warn.append("no acceptable trade plan")

    return ConfluenceResult(
        signal=signal,
        score=score,
        bias=bias,
        positive_evidence=pos,
        negative_evidence=neg,
        warnings=warn,
        trade_plan=plan,
        group_scores=groups,
    )
