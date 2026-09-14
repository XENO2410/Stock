"""Positions endpoints (paper + live-ready)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import risk as risk_mod
from ..core import signal_engine as se
from ..core.mock_market import MockMarket
from ..db import get_db
from .deps import get_or_create_settings

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.post("/size", response_model=schemas.PositionSizeOut)
def size(payload: schemas.PositionSizeIn, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    risk_amount = payload.override_risk or settings.max_loss_per_trade
    result = risk_mod.calc_position_size(
        capital=settings.capital,
        risk_per_trade=risk_amount,
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        direction=payload.direction,
    )
    return result


@router.post("", response_model=schemas.PositionOut, status_code=201)
def open_position(payload: schemas.PositionIn, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    market = MockMarket.instance()
    q = market.get_quote(payload.symbol.upper())
    if not q:
        raise HTTPException(404, "Unknown symbol")
    entry = payload.entry_price or q["price"]

    # Safety gates
    daily = risk_mod.recompute_daily(db, settings, {payload.symbol.upper(): q["price"]})
    open_positions = db.scalars(select(models.Position).where(models.Position.status == "OPEN")).all()
    ok, reason = risk_mod.can_take_new_trade(daily, settings, len(open_positions))
    if not ok:
        raise HTTPException(409, reason)

    fees = settings.brokerage_per_order
    pos = models.Position(
        symbol=payload.symbol.upper(),
        direction=payload.direction,
        quantity=payload.quantity,
        entry_price=round(entry, 2),
        stop_loss=payload.stop_loss,
        target_1=payload.target_1,
        target_2=payload.target_2 or 0.0,
        strategy=payload.strategy or "",
        signal_confidence=payload.signal_confidence or 0,
        mode=payload.mode,
        trailing_mode=payload.trailing_mode,
        trailing_value=payload.trailing_value,
        fees=fees,
    )
    db.add(pos)
    db.flush()
    db.add(
        models.Order(
            position_id=pos.id,
            symbol=pos.symbol,
            side="BUY" if pos.direction == "LONG" else "SELL",
            quantity=pos.quantity,
            price=pos.entry_price,
            mode=pos.mode,
        )
    )
    db.commit()
    db.refresh(pos)
    return pos


@router.get("", response_model=List[schemas.PositionLive])
def list_positions(status: str = "OPEN", db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Position).where(models.Position.status == status.upper()).order_by(models.Position.opened_at.desc())
    ).all()
    market = MockMarket.instance()
    out: List[schemas.PositionLive] = []
    for p in rows:
        q = market.get_quote(p.symbol)
        cp = q["price"] if q else p.entry_price
        sign = 1 if p.direction == "LONG" else -1
        unreal = sign * (cp - p.entry_price) * p.quantity
        unreal_pct = ((cp - p.entry_price) / p.entry_price * 100) * sign if p.entry_price else 0
        if p.status == "OPEN":
            rec = se.exit_recommendation(p.symbol, p.direction, p.entry_price, p.stop_loss, p.target_1, p.target_2)
        else:
            rec = {"recommendation": "CLOSED", "reason": ""}
        out.append(
            schemas.PositionLive(
                id=p.id,
                symbol=p.symbol,
                direction=p.direction,
                quantity=p.quantity,
                entry_price=p.entry_price,
                current_price=cp,
                stop_loss=p.stop_loss,
                target_1=p.target_1,
                target_2=p.target_2,
                unrealized_pnl=round(unreal, 2),
                unrealized_pnl_pct=round(unreal_pct, 2),
                status=p.status,
                recommendation=rec["recommendation"],
                recommendation_reason=rec["reason"],
            )
        )
    return out


@router.post("/{position_id}/exit", response_model=schemas.PositionOut)
def exit_position(position_id: int, payload: schemas.ExitPositionIn, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    pos = db.get(models.Position, position_id)
    if pos is None or pos.status != "OPEN":
        raise HTTPException(404, "Open position not found")
    market = MockMarket.instance()
    q = market.get_quote(pos.symbol)
    exit_price = payload.exit_price or (q["price"] if q else pos.entry_price)
    sign = 1 if pos.direction == "LONG" else -1
    gross = sign * (exit_price - pos.entry_price) * pos.quantity
    fees = pos.fees + settings.brokerage_per_order
    net = gross - fees
    pos.exit_price = round(exit_price, 2)
    pos.realized_pnl = round(net, 2)
    pos.fees = fees
    pos.status = "CLOSED"
    pos.closed_at = datetime.now(timezone.utc)
    pos.notes = payload.reason or pos.notes
    db.add(
        models.Order(
            position_id=pos.id,
            symbol=pos.symbol,
            side="SELL" if pos.direction == "LONG" else "BUY",
            quantity=pos.quantity,
            price=pos.exit_price,
            mode=pos.mode,
        )
    )
    # Auto journal entry
    db.add(
        models.TradeJournalEntry(
            position_id=pos.id,
            symbol=pos.symbol,
            direction=pos.direction,
            entry_time=pos.opened_at,
            entry_price=pos.entry_price,
            exit_time=pos.closed_at,
            exit_price=pos.exit_price,
            quantity=pos.quantity,
            stop_loss=pos.stop_loss,
            target=pos.target_1,
            pnl=pos.realized_pnl,
            pnl_pct=round((pos.exit_price - pos.entry_price) / pos.entry_price * 100 * sign, 2),
            strategy=pos.strategy,
            signal_confidence=pos.signal_confidence,
            entry_reason=pos.strategy,
            exit_reason=payload.reason or "manual",
        )
    )
    # Recompute daily
    risk_mod.recompute_daily(db, settings, {pos.symbol: exit_price})
    db.commit()
    db.refresh(pos)
    return pos
