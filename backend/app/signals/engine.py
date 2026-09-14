"""Analysis orchestrator.

Pulls candles from a MarketDataProvider, runs every analysis module,
combines the outputs via the confluence engine, and returns a fully
structured report the API layer can serialise.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from ..analysis import (
    breakout as breakout_mod,
    candles as candles_mod,
    confluence as confluence_mod,
    momentum as momentum_mod,
    multi_timeframe as mtf_mod,
    reversal as reversal_mod,
    structure as structure_mod,
    support_resistance as sr_mod,
    trend as trend_mod,
    volume as volume_mod,
)
from ..data.provider import MarketDataProvider
from ..data.models import DataSource
from .explanations import summary


@dataclass
class AnalysisReport:
    symbol: str
    timeframe: str
    source: str
    price: float
    signal: str
    score: int
    bias: str
    positive_evidence: List[str] = field(default_factory=list)
    negative_evidence: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    group_scores: Dict[str, int] = field(default_factory=dict)
    trade_plan: Optional[Dict[str, Any]] = None
    summary: str = ""

    trend: Dict[str, Any] = field(default_factory=dict)
    momentum: Dict[str, Any] = field(default_factory=dict)
    volume: Dict[str, Any] = field(default_factory=dict)
    structure: Dict[str, Any] = field(default_factory=dict)
    breakout: Dict[str, Any] = field(default_factory=dict)
    reversal: Dict[str, Any] = field(default_factory=dict)
    multi_timeframe: Dict[str, Any] = field(default_factory=dict)
    support: List[Dict[str, Any]] = field(default_factory=list)
    resistance: List[Dict[str, Any]] = field(default_factory=list)
    candle_patterns: List[Dict[str, Any]] = field(default_factory=list)


def run(
    provider: MarketDataProvider,
    symbol: str,
    timeframe: str = "5m",
    min_risk_reward: float = 1.5,
) -> AnalysisReport:
    series = provider.get_ohlcv(symbol, timeframe, limit=300)
    if len(series) < 30:
        return AnalysisReport(
            symbol=symbol.upper(),
            timeframe=timeframe,
            source=series.source.value,
            price=series.candles[-1].close if series.candles else 0.0,
            signal="WAIT",
            score=0,
            bias="neutral",
            warnings=["insufficient history"],
            summary="WAIT - not enough historical candles for analysis.",
        )

    candles = series.candles

    trend_v = trend_mod.classify(candles)
    momentum_v = momentum_mod.classify(candles)
    volume_v = volume_mod.classify(candles)
    zones = sr_mod.detect(candles, timeframe)
    structure_r = structure_mod.analyze(candles, timeframe)
    breakout_e = breakout_mod.evaluate(candles, zones, trend_v.direction)
    mtf_r = mtf_mod.analyze(provider, symbol)
    reversal_v = reversal_mod.evaluate(candles, structure_r, momentum_v, breakout_e)
    conf = confluence_mod.evaluate(
        candles=candles,
        trend=trend_v,
        momentum=momentum_v,
        volume=volume_v,
        structure=structure_r,
        zones=zones,
        mtf=mtf_r,
        breakout=breakout_e,
        reversal=reversal_v,
        min_risk_reward=min_risk_reward,
    )

    plan_dict = asdict(conf.trade_plan) if conf.trade_plan else None
    patterns = candles_mod.recent_patterns(candles)

    supports = [
        {"price_low": z.price_low, "price_high": z.price_high, "strength": z.strength, "reasons": z.reasons}
        for z in zones if z.kind == "support"
    ]
    resistances = [
        {"price_low": z.price_low, "price_high": z.price_high, "strength": z.strength, "reasons": z.reasons}
        for z in zones if z.kind == "resistance"
    ]

    report = AnalysisReport(
        symbol=symbol.upper(),
        timeframe=timeframe,
        source=series.source.value,
        price=candles[-1].close,
        signal=conf.signal,
        score=conf.score,
        bias=conf.bias,
        positive_evidence=conf.positive_evidence,
        negative_evidence=conf.negative_evidence,
        warnings=conf.warnings,
        group_scores=conf.group_scores,
        trade_plan=plan_dict,
        trend={
            "direction": trend_v.direction,
            "strength": trend_v.strength,
            "ema9": trend_v.ema9,
            "ema20": trend_v.ema20,
            "ema50": trend_v.ema50,
            "slope_pct": trend_v.slope_pct,
            "reasons": trend_v.reasons,
        },
        momentum={
            "rsi14": momentum_v.rsi14,
            "macd": momentum_v.macd,
            "macd_signal": momentum_v.macd_signal,
            "macd_hist": momentum_v.macd_hist,
            "roc10": momentum_v.roc10,
            "verdict": momentum_v.verdict,
            "divergence": momentum_v.divergence,
            "reasons": momentum_v.reasons,
        },
        volume={
            "relative_volume": volume_v.relative_volume,
            "is_spike": volume_v.is_spike,
            "trend": volume_v.trend,
            "confirms_move": volume_v.confirms_move,
            "reasons": volume_v.reasons,
        },
        structure={
            "bias": structure_r.bias,
            "last_swing_high": structure_r.last_swing_high,
            "last_swing_low": structure_r.last_swing_low,
            "events": [
                {
                    "timestamp": ev.timestamp,
                    "type": ev.type,
                    "price": ev.price,
                    "confidence": ev.confidence,
                    "reason": ev.reason,
                }
                for ev in structure_r.events[-10:]
            ],
        },
        breakout=(
            {"kind": breakout_e.kind, "zone_mid": breakout_e.zone_mid, "strength": breakout_e.strength, "reasons": breakout_e.reasons}
            if breakout_e else {}
        ),
        reversal={"direction": reversal_v.direction, "strength": reversal_v.strength, "reasons": reversal_v.reasons},
        multi_timeframe={
            "overall": mtf_r.overall,
            "alignment_score": mtf_r.alignment_score,
            "per_timeframe": [{"timeframe": e.timeframe, "direction": e.direction, "strength": e.strength} for e in mtf_r.per_timeframe],
        },
        support=supports,
        resistance=resistances,
        candle_patterns=[{"name": p.name, "bias": p.bias, "strength": p.strength} for p in patterns],
    )
    report.summary = summary(conf)
    return report
