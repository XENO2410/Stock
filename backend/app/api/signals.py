"""Signals endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import signal_engine as se
from ..core.mock_market import MockMarket
from ..db import get_db
from .deps import get_or_create_settings

router = APIRouter(prefix="/api/signals", tags=["signals"])


def _result_to_signal(res: se.SignalResult) -> models.Signal:
    return models.Signal(
        symbol=res.symbol,
        direction=res.direction,
        action=res.action,
        confidence=res.confidence,
        entry_low=res.entry_low,
        entry_high=res.entry_high,
        stop_loss=res.stop_loss,
        target_1=res.target_1,
        target_2=res.target_2,
        risk_reward=res.risk_reward,
        strategy=res.strategy,
        timeframe=res.timeframe,
        valid_until=res.valid_until,
        invalidation=res.invalidation,
        breakdown=res.breakdown,
        reasons=res.reasons,
    )


@router.get("/{symbol}", response_model=schemas.SignalOut)
def signal_for(symbol: str, timeframe: str = "5m", db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    res = se.evaluate(
        symbol.upper(),
        weights=settings.signal_weights,
        min_confidence=settings.min_confidence,
        timeframe=timeframe,
    )
    if res is None:
        raise HTTPException(422, "Insufficient data to generate a signal")
    row = _result_to_signal(res)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=List[schemas.SignalOut])
def top_signals(
    min_confidence: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    settings = get_or_create_settings(db)
    threshold = min_confidence if min_confidence is not None else settings.min_confidence
    results = se.evaluate_universe(min_confidence=0)  # rank across all, threshold applied client-side too
    results.sort(key=lambda r: r.confidence, reverse=True)
    out: List[models.Signal] = []
    for r in results[:limit]:
        row = _result_to_signal(r)
        # persist last-N briefly for auditing (skip if no-trade)
        if r.action != "NO_TRADE":
            db.add(row)
        out.append(row)
    db.commit()
    # For non-persisted rows, fabricate ids & timestamps for schema
    for i, row in enumerate(out):
        if row.id is None:
            row.id = -(i + 1)
            row.created_at = datetime.now(timezone.utc)
    return out
