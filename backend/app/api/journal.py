"""Journal endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("", response_model=List[schemas.JournalOut])
def list_entries(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.TradeJournalEntry).order_by(models.TradeJournalEntry.created_at.desc()).limit(limit)
    ).all()
    return rows


@router.post("", response_model=schemas.JournalOut, status_code=201)
def create(payload: schemas.JournalIn, db: Session = Depends(get_db)):
    sign = 1 if payload.direction == "LONG" else -1
    exit_price = payload.exit_price or 0.0
    pnl = 0.0
    pnl_pct = 0.0
    if exit_price:
        pnl = sign * (exit_price - payload.entry_price) * payload.quantity
        pnl_pct = (exit_price - payload.entry_price) / payload.entry_price * 100 * sign
    row = models.TradeJournalEntry(
        symbol=payload.symbol.upper(),
        direction=payload.direction,
        entry_time=payload.entry_time,
        entry_price=payload.entry_price,
        exit_time=payload.exit_time,
        exit_price=exit_price,
        quantity=payload.quantity,
        stop_loss=payload.stop_loss or 0.0,
        target=payload.target or 0.0,
        pnl=round(pnl, 2),
        pnl_pct=round(pnl_pct, 2),
        strategy=payload.strategy or "",
        signal_confidence=payload.signal_confidence or 0,
        market_conditions=payload.market_conditions or "",
        entry_reason=payload.entry_reason or "",
        exit_reason=payload.exit_reason or "",
        what_went_well=payload.what_went_well or "",
        what_went_wrong=payload.what_went_wrong or "",
        followed_signal=bool(payload.followed_signal),
        broke_rules=bool(payload.broke_rules),
        emotion=payload.emotion or "",
        notes=payload.notes or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{entry_id}", status_code=204)
def delete(entry_id: int, db: Session = Depends(get_db)):
    row = db.get(models.TradeJournalEntry, entry_id)
    if row is None:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
