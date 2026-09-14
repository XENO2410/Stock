"""Backtest metrics.

WAIT is never counted as a trade. Only closed paper trades count towards
returns. R-multiples are computed as PnL / (risk_per_share * quantity).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Dict, List

from .paper import PaperTrade


@dataclass
class Metrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    average_trade: float = 0.0
    average_r: float = 0.0
    median_r: float = 0.0
    r_distribution: Dict[str, int] = field(default_factory=dict)
    buy_signals: int = 0
    sell_signals: int = 0
    wait_signals: int = 0
    total_fees: float = 0.0
    total_slippage: float = 0.0


def _r_bucket(r: float) -> str:
    if r <= -2:
        return "<=-2R"
    if r <= -1:
        return "-2R..-1R"
    if r <= 0:
        return "-1R..0R"
    if r < 1:
        return "0R..+1R"
    if r < 2:
        return "+1R..+2R"
    if r < 3:
        return "+2R..+3R"
    return ">=+3R"


def summarise(trades: List[PaperTrade], signal_counts: Dict[str, int]) -> Metrics:
    m = Metrics(
        buy_signals=signal_counts.get("BUY", 0),
        sell_signals=signal_counts.get("SELL", 0),
        wait_signals=signal_counts.get("WAIT", 0),
    )
    closed = [t for t in trades if not t.is_open()]
    if not closed:
        return m

    wins = [t for t in closed if t.pnl > 0]
    losses = [t for t in closed if t.pnl < 0]

    m.total_trades = len(closed)
    m.winning_trades = len(wins)
    m.losing_trades = len(losses)
    m.win_rate = round(len(wins) / m.total_trades * 100, 2) if m.total_trades else 0.0
    m.gross_profit = round(sum(t.pnl for t in wins), 2)
    m.gross_loss = round(abs(sum(t.pnl for t in losses)), 2)
    m.net_pnl = round(sum(t.pnl for t in closed), 2)
    m.average_win = round(m.gross_profit / len(wins), 2) if wins else 0.0
    m.average_loss = round(-m.gross_loss / len(losses), 2) if losses else 0.0
    m.profit_factor = round(m.gross_profit / m.gross_loss, 2) if m.gross_loss else 0.0
    m.expectancy = round(m.net_pnl / m.total_trades, 2)
    m.average_trade = m.expectancy
    rs = [t.r_multiple for t in closed]
    m.average_r = round(sum(rs) / len(rs), 3) if rs else 0.0
    m.median_r = round(float(median(rs)), 3) if rs else 0.0
    m.total_fees = round(sum(t.fees for t in closed), 2)
    m.total_slippage = round(sum(t.slippage for t in closed), 2)

    # Max drawdown from equity curve of closed trades
    equity = 0.0
    peak = 0.0
    dd = 0.0
    max_dd = 0.0
    max_win_streak = 0
    max_loss_streak = 0
    win_streak = 0
    loss_streak = 0
    for t in closed:
        equity += t.pnl
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
        if t.pnl > 0:
            win_streak += 1
            loss_streak = 0
            max_win_streak = max(max_win_streak, win_streak)
        elif t.pnl < 0:
            loss_streak += 1
            win_streak = 0
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            win_streak = loss_streak = 0
    m.max_drawdown = round(max_dd, 2)
    m.max_consecutive_wins = max_win_streak
    m.max_consecutive_losses = max_loss_streak

    dist: Dict[str, int] = {}
    for r in rs:
        b = _r_bucket(r)
        dist[b] = dist.get(b, 0) + 1
    m.r_distribution = dist
    return m
