"""Backtesting endpoint.

Runs a compact bar-by-bar simulation on cached mock candles.
The API is intentionally simple so it can be extended per strategy.
Uses only information available up to each bar (no look-ahead).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import indicators as ind
from ..core.mock_market import MockMarket
from ..db import get_db

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def _simulate(candles, strategy: str, capital: float, risk_per_trade: float):
    o = np.array([c.o for c in candles])
    h = np.array([c.h for c in candles])
    l = np.array([c.l for c in candles])
    c_ = np.array([c.c for c in candles])
    v = np.array([c.v for c in candles])
    if c_.size < 60:
        return [], 0.0, 0.0

    ema9 = ind.ema(c_, 9)
    ema20 = ind.ema(c_, 20)
    vwap_series = np.zeros_like(c_)
    tp = (h + l + c_) / 3.0
    cum_v = np.cumsum(v)
    cum_pv = np.cumsum(tp * v)
    vwap_series = np.where(cum_v > 0, cum_pv / np.where(cum_v == 0, 1, cum_v), c_)

    trades = []
    position = None
    for i in range(30, c_.size):
        price = c_[i]
        # Entry signals
        if position is None:
            long_ok = ema9[i] > ema20[i] and price > vwap_series[i] and c_[i] > c_[i - 1]
            short_ok = ema9[i] < ema20[i] and price < vwap_series[i] and c_[i] < c_[i - 1]
            if strategy == "breakout":
                long_ok = long_ok and price > np.max(h[i - 20 : i])
                short_ok = short_ok and price < np.min(l[i - 20 : i])
            elif strategy == "pullback":
                long_ok = ema9[i] > ema20[i] and abs(price - vwap_series[i]) / price < 0.003 and c_[i] > c_[i - 1]
                short_ok = ema9[i] < ema20[i] and abs(price - vwap_series[i]) / price < 0.003 and c_[i] < c_[i - 1]
            elif strategy == "orb":
                orh = np.max(h[:5])
                orl = np.min(l[:5])
                long_ok = price > orh
                short_ok = price < orl
            if long_ok:
                atr = float(np.mean(h[i - 14 : i] - l[i - 14 : i]))
                sl = price - max(atr, price * 0.003)
                risk = price - sl
                qty = max(1, int(risk_per_trade / max(risk, 0.05)))
                position = {"dir": "LONG", "entry_i": i, "entry": price, "sl": sl, "target": price + risk * 1.8, "qty": qty}
            elif short_ok:
                atr = float(np.mean(h[i - 14 : i] - l[i - 14 : i]))
                sl = price + max(atr, price * 0.003)
                risk = sl - price
                qty = max(1, int(risk_per_trade / max(risk, 0.05)))
                position = {"dir": "SHORT", "entry_i": i, "entry": price, "sl": sl, "target": price - risk * 1.8, "qty": qty}
        else:
            hit_stop = (position["dir"] == "LONG" and l[i] <= position["sl"]) or (
                position["dir"] == "SHORT" and h[i] >= position["sl"]
            )
            hit_target = (position["dir"] == "LONG" and h[i] >= position["target"]) or (
                position["dir"] == "SHORT" and l[i] <= position["target"]
            )
            if hit_stop or hit_target or i == c_.size - 1:
                exit_price = position["target"] if hit_target else position["sl"] if hit_stop else price
                sign = 1 if position["dir"] == "LONG" else -1
                pnl = sign * (exit_price - position["entry"]) * position["qty"]
                trades.append({
                    "entry_i": position["entry_i"],
                    "exit_i": i,
                    "direction": position["dir"],
                    "entry": position["entry"],
                    "exit": exit_price,
                    "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "reason": "target" if hit_target else "stop" if hit_stop else "eod",
                })
                position = None

    net = round(sum(t["pnl"] for t in trades), 2)

    # Max drawdown
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    return trades, net, max_dd


@router.post("", response_model=schemas.BacktestOut)
def run_backtest(payload: schemas.BacktestIn, db: Session = Depends(get_db)):
    market = MockMarket.instance()
    candles = market.get_candles(payload.symbol.upper(), payload.timeframe, limit=1000)
    trades, net, max_dd = _simulate(candles, payload.strategy, payload.capital, payload.risk_per_trade)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    losses = sum(1 for t in trades if t["pnl"] < 0)
    total = len(trades)
    win_rate = round(wins / total * 100, 1) if total else 0.0
    total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    pf = round(total_wins / total_losses, 2) if total_losses else 0.0
    start = candles[0].t.date() if candles else datetime.now(timezone.utc).date()
    end = candles[-1].t.date() if candles else start

    row = models.Backtest(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        strategy=payload.strategy,
        start_date=start,
        end_date=end,
        capital=payload.capital,
        risk_per_trade=payload.risk_per_trade,
        total_trades=total,
        winning_trades=wins,
        losing_trades=losses,
        net_pnl=net,
        max_drawdown=round(max_dd, 2),
        profit_factor=pf,
        win_rate=win_rate,
        params={"days": payload.days},
    )
    db.add(row)
    db.flush()
    for t in trades:
        db.add(
            models.BacktestTrade(
                backtest_id=row.id,
                entry_time=candles[t["entry_i"]].t,
                exit_time=candles[t["exit_i"]].t,
                direction=t["direction"],
                entry_price=t["entry"],
                exit_price=t["exit"],
                quantity=t["qty"],
                pnl=t["pnl"],
                reason=t["reason"],
            )
        )
    db.commit()
    db.refresh(row)
    return row
