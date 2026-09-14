"""Daily goal endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..core import risk as risk_mod
from ..core.mock_market import MockMarket
from ..db import get_db
from .deps import get_or_create_settings

router = APIRouter(prefix="/api/goal", tags=["goal"])


@router.get("", response_model=schemas.DailyGoalOut)
def daily_goal(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    market = MockMarket.instance()
    prices = {s["symbol"]: (market.get_quote(s["symbol"]) or {}).get("price", 0.0) for s in market.universe()}
    daily = risk_mod.recompute_daily(db, settings, prices)
    db.commit()
    return risk_mod.daily_goal_view(daily, settings)
