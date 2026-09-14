"""Risk management: position sizing, daily P&L tracking, and safety checks.

All calculations are pure-ish: they read/write DB via passed session but do
no I/O beyond that. This keeps them testable.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


# ---------------- Position sizing ----------------

def calc_position_size(
    capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss: float,
    direction: str = "LONG",
) -> Dict:
    warnings: List[str] = []
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share <= 0:
        return {
            "risk_per_share": 0.0,
            "max_quantity_by_risk": 0,
            "capital_required": 0.0,
            "available_capital": capital,
            "suggested_quantity": 0,
            "risk_amount": 0.0,
            "warnings": ["Entry and stop loss cannot be equal"],
        }
    max_qty_by_risk = int(risk_per_trade / risk_per_share)
    max_qty_by_capital = int(capital / entry_price) if entry_price > 0 else 0
    suggested = max(0, min(max_qty_by_risk, max_qty_by_capital))
    capital_required = suggested * entry_price
    if max_qty_by_risk > max_qty_by_capital:
        warnings.append("Capital limits your position more than risk allows")
    if suggested == 0:
        warnings.append("Insufficient capital or risk budget for even 1 share")
    return {
        "risk_per_share": round(risk_per_share, 2),
        "max_quantity_by_risk": max_qty_by_risk,
        "capital_required": round(capital_required, 2),
        "available_capital": round(capital, 2),
        "suggested_quantity": suggested,
        "risk_amount": round(suggested * risk_per_share, 2),
        "warnings": warnings,
    }


# ---------------- Daily P&L ----------------

def _today() -> date:
    return datetime.now(timezone.utc).date()


def get_or_create_daily(db: Session, settings: models.UserSettings) -> models.DailyPnL:
    today = _today()
    row = db.scalar(select(models.DailyPnL).where(models.DailyPnL.trade_date == today))
    if row is None:
        row = models.DailyPnL(
            trade_date=today,
            daily_target=settings.daily_profit_target,
            daily_max_loss=settings.daily_max_loss,
        )
        db.add(row)
        db.flush()
    return row


def recompute_daily(db: Session, settings: models.UserSettings, current_prices: Dict[str, float]) -> models.DailyPnL:
    row = get_or_create_daily(db, settings)
    row.daily_target = settings.daily_profit_target
    row.daily_max_loss = settings.daily_max_loss

    # realized from today's closed positions
    today = row.trade_date
    closed = db.scalars(
        select(models.Position).where(
            models.Position.status == "CLOSED",
            models.Position.opened_at >= datetime.combine(today, datetime.min.time()),
        )
    ).all()
    realized = sum(p.realized_pnl for p in closed)
    wins = sum(1 for p in closed if p.realized_pnl > 0)
    losses = sum(1 for p in closed if p.realized_pnl < 0)

    # unrealized from open positions
    open_positions = db.scalars(select(models.Position).where(models.Position.status == "OPEN")).all()
    unrealized = 0.0
    for p in open_positions:
        cp = current_prices.get(p.symbol, p.entry_price)
        sign = 1 if p.direction == "LONG" else -1
        unrealized += sign * (cp - p.entry_price) * p.quantity

    row.realized_pnl = round(realized, 2)
    row.unrealized_pnl = round(unrealized, 2)
    row.trades_count = len(closed)
    row.winning_trades = wins
    row.losing_trades = losses
    row.target_reached = realized >= settings.daily_profit_target
    row.loss_limit_hit = realized <= -abs(settings.daily_max_loss)
    return row


def daily_goal_view(daily: models.DailyPnL, settings: models.UserSettings) -> Dict:
    total = daily.realized_pnl
    remaining = max(0.0, settings.daily_profit_target - total)
    progress = 0.0
    if settings.daily_profit_target > 0:
        progress = max(0.0, min(100.0, total / settings.daily_profit_target * 100))
    win_rate = 0.0
    if daily.trades_count > 0:
        win_rate = daily.winning_trades / daily.trades_count * 100
    conservative = bool(settings.conservative_after_target and daily.target_reached)
    active_threshold = settings.conservative_confidence if conservative else settings.min_confidence
    return {
        "trade_date": daily.trade_date,
        "daily_target": settings.daily_profit_target,
        "daily_max_loss": settings.daily_max_loss,
        "realized_pnl": daily.realized_pnl,
        "unrealized_pnl": daily.unrealized_pnl,
        "remaining_target": round(remaining, 2),
        "progress_pct": round(progress, 1),
        "trades_count": daily.trades_count,
        "max_trades": settings.max_trades_per_day,
        "winning_trades": daily.winning_trades,
        "losing_trades": daily.losing_trades,
        "win_rate": round(win_rate, 1),
        "target_reached": daily.target_reached,
        "loss_limit_hit": daily.loss_limit_hit,
        "conservative_mode": conservative,
        "active_confidence_threshold": active_threshold,
    }


# ---------------- Safety gates ----------------

def can_take_new_trade(daily: models.DailyPnL, settings: models.UserSettings, open_positions: int) -> Tuple[bool, str]:
    if daily.loss_limit_hit:
        return False, "Daily maximum loss reached. New trade signals are locked."
    if daily.trades_count >= settings.max_trades_per_day:
        return False, f"Daily max trades ({settings.max_trades_per_day}) already taken."
    if open_positions >= settings.max_open_positions:
        return False, f"Maximum open positions ({settings.max_open_positions}) reached."
    return True, ""
