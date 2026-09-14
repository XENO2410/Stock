"""Analytics dashboard endpoint."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _windowed_sum(rows: List[models.Position], since: datetime) -> float:
    return round(sum(p.realized_pnl for p in rows if p.closed_at and p.closed_at >= since), 2)


@router.get("/overview", response_model=schemas.AnalyticsOverview)
def overview(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Position).where(models.Position.status == "CLOSED")).all()
    now = datetime.now(timezone.utc)
    today = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)

    total_pnl = round(sum(p.realized_pnl for p in rows), 2)
    total_trades = len(rows)
    wins = [p for p in rows if p.realized_pnl > 0]
    losses = [p for p in rows if p.realized_pnl < 0]
    win_rate = round(len(wins) / total_trades * 100, 1) if total_trades else 0.0
    average_win = round(sum(p.realized_pnl for p in wins) / len(wins), 2) if wins else 0.0
    average_loss = round(sum(p.realized_pnl for p in losses) / len(losses), 2) if losses else 0.0
    total_wins = sum(p.realized_pnl for p in wins)
    total_losses = abs(sum(p.realized_pnl for p in losses))
    profit_factor = round(total_wins / total_losses, 2) if total_losses else 0.0
    largest_win = round(max((p.realized_pnl for p in wins), default=0.0), 2)
    largest_loss = round(min((p.realized_pnl for p in losses), default=0.0), 2)

    # Max drawdown from equity curve
    sorted_rows = sorted([p for p in rows if p.closed_at], key=lambda p: p.closed_at)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in sorted_rows:
        equity += p.realized_pnl
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    # By strategy
    strat_map: Dict[str, List[models.Position]] = defaultdict(list)
    for p in rows:
        strat_map[p.strategy or "unknown"].append(p)
    by_strategy = []
    for name, ps in strat_map.items():
        w = sum(1 for p in ps if p.realized_pnl > 0)
        by_strategy.append({
            "strategy": name,
            "trades": len(ps),
            "win_rate": round(w / len(ps) * 100, 1) if ps else 0.0,
            "pnl": round(sum(p.realized_pnl for p in ps), 2),
        })

    # By hour
    hour_map: Dict[int, List[models.Position]] = defaultdict(list)
    for p in rows:
        if p.opened_at:
            hour_map[p.opened_at.hour].append(p)
    by_hour = []
    for h in sorted(hour_map):
        ps = hour_map[h]
        w = sum(1 for p in ps if p.realized_pnl > 0)
        by_hour.append({
            "hour": h,
            "trades": len(ps),
            "win_rate": round(w / len(ps) * 100, 1),
            "pnl": round(sum(p.realized_pnl for p in ps), 2),
        })

    return schemas.AnalyticsOverview(
        total_pnl=total_pnl,
        today_pnl=_windowed_sum(rows, today),
        week_pnl=_windowed_sum(rows, week),
        month_pnl=_windowed_sum(rows, month),
        total_trades=total_trades,
        win_rate=win_rate,
        average_win=average_win,
        average_loss=average_loss,
        profit_factor=profit_factor,
        largest_win=largest_win,
        largest_loss=largest_loss,
        max_drawdown=round(max_dd, 2),
        by_strategy=by_strategy,
        by_hour=by_hour,
    )
