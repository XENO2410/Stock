"""Tests for the backtest engine + paper-trade rules."""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import List

from app.backtesting.engine import BacktestConfig, run_backtest
from app.backtesting.paper import PaperTrade, force_close, open_trade, try_close_on_candle
from app.backtesting.replay_session import ReplaySession, _hydrate_all_tfs
from app.data.models import Candle


def _synthetic(n: int, seed: int = 3) -> List[Candle]:
    rng = random.Random(seed)
    base = datetime(2026, 9, 1, 3, 45, tzinfo=timezone.utc)
    out = []
    price = 100.0
    for i in range(n):
        step = rng.gauss(0, 0.5) + math.sin(i / 12) * 0.2
        o = price
        c = max(1.0, o + step)
        h = max(o, c) + abs(rng.gauss(0, 0.15))
        l = min(o, c) - abs(rng.gauss(0, 0.15))
        out.append(Candle(timestamp=base + timedelta(minutes=5 * i), open=o, high=h, low=l, close=c, volume=rng.randint(5000, 15000)))
        price = c
    return out


def _session(candles: List[Candle]) -> ReplaySession:
    tfs = _hydrate_all_tfs("5m", candles)
    return ReplaySession(id="bt", symbol="TEST", primary_tf="5m", candles_by_tf=tfs, cursor=0)


# ---------------- paper.py fill rules ----------------

def _c(open_: float, high: float, low: float, close: float, i: int = 0) -> Candle:
    return Candle(timestamp=datetime(2026, 9, 1, 0, i, tzinfo=timezone.utc), open=open_, high=high, low=low, close=close, volume=1)


def test_stop_and_target_in_same_candle_favours_stop():
    trade = open_trade(
        symbol="X", timeframe="5m", direction="LONG",
        entry_index=0, entry_time=_c(100, 100, 100, 100).timestamp, entry_price=100,
        stop=99, target=102, quantity=10, signal_score=70, signal_reasons=[],
        brokerage=0, slippage_bps=0,
    )
    # Candle spans both 99 (stop) and 102 (target): stop must win.
    closed = try_close_on_candle(trade, _c(101, 102, 99, 101, i=1), idx=1, brokerage=0, slippage_bps=0)
    assert closed
    assert trade.reason == "stop"
    assert trade.resolution == "both_touched_stop_first"


def test_target_only_hit_is_a_win():
    trade = open_trade(
        symbol="X", timeframe="5m", direction="LONG",
        entry_index=0, entry_time=_c(100, 100, 100, 100).timestamp, entry_price=100,
        stop=99, target=102, quantity=10, signal_score=70, signal_reasons=[],
        brokerage=0, slippage_bps=0,
    )
    closed = try_close_on_candle(trade, _c(100.5, 102.5, 100.2, 102.1, i=1), idx=1, brokerage=0, slippage_bps=0)
    assert closed
    assert trade.reason == "target"
    assert trade.pnl > 0
    assert trade.r_multiple > 0


def test_stop_only_hit_is_a_loss():
    trade = open_trade(
        symbol="X", timeframe="5m", direction="LONG",
        entry_index=0, entry_time=_c(100, 100, 100, 100).timestamp, entry_price=100,
        stop=99, target=102, quantity=10, signal_score=70, signal_reasons=[],
        brokerage=0, slippage_bps=0,
    )
    closed = try_close_on_candle(trade, _c(99.8, 100.2, 98.5, 99.0, i=1), idx=1, brokerage=0, slippage_bps=0)
    assert closed
    assert trade.reason == "stop"
    assert trade.pnl < 0


def test_short_stop_uses_high_and_target_uses_low():
    trade = open_trade(
        symbol="X", timeframe="5m", direction="SHORT",
        entry_index=0, entry_time=_c(100, 100, 100, 100).timestamp, entry_price=100,
        stop=101, target=98, quantity=10, signal_score=70, signal_reasons=[],
        brokerage=0, slippage_bps=0,
    )
    closed = try_close_on_candle(trade, _c(99.5, 99.8, 97.5, 98.0, i=1), idx=1, brokerage=0, slippage_bps=0)
    assert closed
    assert trade.reason == "target"
    assert trade.pnl > 0


def test_force_close_marks_eod():
    trade = open_trade(
        symbol="X", timeframe="5m", direction="LONG",
        entry_index=0, entry_time=_c(100, 100, 100, 100).timestamp, entry_price=100,
        stop=99, target=105, quantity=10, signal_score=70, signal_reasons=[],
        brokerage=0, slippage_bps=0,
    )
    force_close(trade, _c(100, 100.5, 99.5, 100.2, i=1), idx=1, brokerage=20, slippage_bps=0)
    assert trade.reason == "eod"
    assert trade.exit_price is not None


# ---------------- End-to-end backtest ----------------

def test_backtest_runs_and_splits_train_test():
    candles = _synthetic(240)
    session = _session(candles)
    cfg = BacktestConfig(timeframe="5m", train_frac=0.7, warmup_bars=40, risk_per_trade=250, min_risk_reward=1.2)
    result = run_backtest(session, cfg)
    assert result.total_candles == 240
    assert result.train_end_index == int(240 * 0.7)
    assert "wait_signals" in result.overall
    # Signal counts must add up to the number of evaluated bars
    ev_total = result.overall["buy_signals"] + result.overall["sell_signals"] + result.overall["wait_signals"]
    assert ev_total == len(result.signals_timeline)
    # In-sample + out-of-sample trade counts sum to overall
    assert (
        result.in_sample["total_trades"] + result.out_of_sample["total_trades"]
        == result.overall["total_trades"]
    )


def test_backtest_never_treats_wait_as_a_trade():
    # A very tight risk/reward requirement forces WAIT everywhere
    candles = _synthetic(120)
    session = _session(candles)
    cfg = BacktestConfig(timeframe="5m", train_frac=0.7, warmup_bars=30, min_risk_reward=999.0)
    result = run_backtest(session, cfg)
    assert result.overall["total_trades"] == 0
    assert result.overall["wait_signals"] > 0
