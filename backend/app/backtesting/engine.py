"""Bar-by-bar backtester built on top of ReplaySession + the shared
confluence analysis engine.

Design promise: the same code path produces the report the UI shows and
the signals the backtest trades. There is only ONE signal engine.

Iteration:
  1. Advance the ReplaySession cursor by one candle.
  2. Ask signals.engine.run(ReplayProvider(session), ...) for a report.
     The provider only exposes candles up to the cursor - no look-ahead.
  3. If a position is open, try to close it on the next candle's H/L using
     the paper.py rules (pessimistic on simultaneous stop+target).
  4. If flat and the fresh signal is BUY/SELL with a trade plan, open a
     new paper trade sized to `risk_per_trade`.

Metrics are computed for the full run, plus separately for the IN-SAMPLE
(first `train_frac` fraction) and OUT-OF-SAMPLE tail so the user can
see if the strategy holds up on unseen data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from ..data.models import Candle
from ..signals.engine import run as run_analysis
from .metrics import Metrics, summarise
from .paper import PaperTrade, force_close, open_trade, try_close_on_candle
from .replay_session import ReplayProvider, ReplaySession


@dataclass
class BacktestConfig:
    timeframe: str = "5m"
    train_frac: float = 0.7
    warmup_bars: int = 30
    max_bars: Optional[int] = None
    risk_per_trade: float = 250.0
    brokerage_per_order: float = 20.0
    slippage_bps: float = 5.0
    min_risk_reward: float = 1.5
    close_at_end: bool = True         # flatten any open trade on the last candle


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    total_candles: int
    warmup_bars: int
    train_frac: float
    train_end_index: int
    config: Dict[str, Any]
    overall: Dict[str, Any]
    in_sample: Dict[str, Any]
    out_of_sample: Dict[str, Any]
    trades: List[Dict[str, Any]] = field(default_factory=list)
    signals_timeline: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: Dict[str, Any] = field(default_factory=dict)


def _size_position(entry: float, stop: float, risk_per_trade: float) -> int:
    per = abs(entry - stop)
    if per <= 0:
        return 0
    return max(1, int(risk_per_trade / per))


def run_backtest(session: ReplaySession, config: BacktestConfig) -> BacktestResult:
    session.train_frac = config.train_frac
    primary = session.candles_by_tf[config.timeframe] if config.timeframe in session.candles_by_tf else session.primary()
    n = len(primary)
    if config.max_bars:
        n = min(n, config.max_bars)
    train_end = int(n * config.train_frac)

    provider = ReplayProvider(session)
    closed_trades: List[PaperTrade] = []
    open_trade_state: Optional[PaperTrade] = None
    timeline: List[Dict[str, Any]] = []
    signal_counts: Dict[str, int] = {"BUY": 0, "SELL": 0, "WAIT": 0}

    session.primary_tf = config.timeframe if config.timeframe in session.candles_by_tf else session.primary_tf

    start_i = max(config.warmup_bars, 1)
    for i in range(start_i, n):
        session.cursor = i
        # 1) Try to close an open trade on the current candle
        if open_trade_state is not None:
            c = primary[i]
            closed = try_close_on_candle(open_trade_state, c, i, config.brokerage_per_order, config.slippage_bps)
            if closed:
                closed_trades.append(open_trade_state)
                open_trade_state = None

        # 2) Get a fresh signal at the current bar (analysis sees [0..i])
        report = run_analysis(provider, session.symbol, timeframe=config.timeframe, min_risk_reward=config.min_risk_reward)
        signal_counts[report.signal] = signal_counts.get(report.signal, 0) + 1
        timeline.append({
            "index": i,
            "timestamp": primary[i].timestamp.isoformat(),
            "signal": report.signal,
            "score": report.score,
            "bias": report.bias,
            "in_sample": i < train_end,
        })

        # 3) Open a new trade only if flat, engine gave a plan, and RR is valid
        if open_trade_state is None and report.signal in ("BUY", "SELL") and report.trade_plan:
            plan = report.trade_plan
            entry = (plan["entry_low"] + plan["entry_high"]) / 2
            qty = _size_position(entry, plan["stop"], config.risk_per_trade)
            if qty > 0:
                open_trade_state = open_trade(
                    symbol=session.symbol,
                    timeframe=config.timeframe,
                    direction="LONG" if report.signal == "BUY" else "SHORT",
                    entry_index=i,
                    entry_time=primary[i].timestamp,
                    entry_price=entry,
                    stop=plan["stop"],
                    target=plan["target_1"],
                    quantity=qty,
                    signal_score=report.score,
                    signal_reasons=list(report.positive_evidence),
                    brokerage=config.brokerage_per_order,
                    slippage_bps=config.slippage_bps,
                )

    # End of window: optionally flatten
    if open_trade_state is not None and config.close_at_end:
        last_i = n - 1
        force_close(open_trade_state, primary[last_i], last_i, config.brokerage_per_order, config.slippage_bps)
        closed_trades.append(open_trade_state)
        open_trade_state = None

    overall_metrics = summarise(closed_trades, signal_counts)
    in_sample_trades = [t for t in closed_trades if t.entry_index < train_end]
    oos_trades = [t for t in closed_trades if t.entry_index >= train_end]
    in_sample_signals = {"BUY": 0, "SELL": 0, "WAIT": 0}
    oos_signals = {"BUY": 0, "SELL": 0, "WAIT": 0}
    for ev in timeline:
        target = in_sample_signals if ev["in_sample"] else oos_signals
        target[ev["signal"]] = target.get(ev["signal"], 0) + 1
    in_metrics = summarise(in_sample_trades, in_sample_signals)
    oos_metrics = summarise(oos_trades, oos_signals)

    trades_json: List[Dict[str, Any]] = []
    for t in closed_trades:
        d = asdict(t)
        d["entry_time"] = t.entry_time.isoformat()
        d["exit_time"] = t.exit_time.isoformat() if t.exit_time else None
        d["in_sample"] = t.entry_index < train_end
        trades_json.append(d)

    return BacktestResult(
        symbol=session.symbol,
        timeframe=config.timeframe,
        total_candles=n,
        warmup_bars=start_i,
        train_frac=config.train_frac,
        train_end_index=train_end,
        config=asdict(config),
        overall=asdict(overall_metrics),
        in_sample=asdict(in_metrics),
        out_of_sample=asdict(oos_metrics),
        trades=trades_json,
        signals_timeline=timeline,
        assumptions={
            "brokerage_per_order_inr": config.brokerage_per_order,
            "slippage_bps_each_side": config.slippage_bps,
            "risk_per_trade_inr": config.risk_per_trade,
            "min_risk_reward": config.min_risk_reward,
            "intra_candle_conflict_resolution": "stop fills first (pessimistic)",
            "close_at_end": config.close_at_end,
        },
    )
