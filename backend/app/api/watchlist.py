"""Watchlist endpoints (enriched with live snapshot + signal)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core import signal_engine as se
from ..core.mock_market import MockMarket
from ..db import get_db
from .deps import get_or_create_settings

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=List[schemas.WatchlistRow])
def list_watchlist(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.WatchlistStock).order_by(models.WatchlistStock.added_at)).all()
    if not rows:
        _seed_default(db)
        db.commit()
        rows = db.scalars(select(models.WatchlistStock).order_by(models.WatchlistStock.added_at)).all()

    settings = get_or_create_settings(db)
    market = MockMarket.instance()
    result: List[schemas.WatchlistRow] = []
    for w in rows:
        q = market.get_quote(w.symbol)
        if not q:
            continue
        sig = se.evaluate(
            w.symbol,
            weights=settings.signal_weights,
            min_confidence=settings.min_confidence,
        )
        pack = se.build_indicator_pack(w.symbol)
        rvol = pack.relative_volume if pack else 1.0
        vwap = pack.vwap if pack else q["price"]
        trend = pack.trend_overall if pack else "Neutral"
        result.append(
            schemas.WatchlistRow(
                symbol=w.symbol,
                name=w.name,
                exchange=w.exchange,
                price=q["price"],
                change=q["change"],
                change_pct=q["change_pct"],
                volume=q["volume"],
                relative_volume=rvol,
                above_vwap=q["price"] >= vwap,
                vwap=vwap,
                signal_action=sig.action if sig else "NO_TRADE",
                signal_confidence=sig.confidence if sig else 0,
                trend=trend,
                is_favourite=w.is_favourite,
            )
        )
    return result


def _seed_default(db: Session) -> None:
    """Seed a starter watchlist if empty."""
    from ..config import settings as app_settings
    if app_settings.data_provider != "demo":
        # In live-provider mode, seed a small NSE starter list without relying
        # on mock quotes. The feeder will backfill real data.
        for sym in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]:
            db.add(models.WatchlistStock(symbol=sym, name=sym, exchange="NSE"))
        return
    for sym in ["RATNAVEER", "INDIGOPN", "WELSPUNIND", "MENONBE", "LUMINO", "RELIANCE"]:
        q = MockMarket.instance().get_quote(sym)
        if not q:
            continue
        db.add(models.WatchlistStock(symbol=sym, name=q["name"], exchange="NSE"))


@router.post("", response_model=schemas.WatchlistOut, status_code=201)
def add_watchlist(payload: schemas.WatchlistIn, db: Session = Depends(get_db)):
    from ..config import settings as app_settings
    sym = payload.symbol.upper()
    existing = db.scalar(select(models.WatchlistStock).where(models.WatchlistStock.symbol == sym))
    if existing:
        raise HTTPException(400, "Symbol already in watchlist")
    q = MockMarket.instance().get_quote(sym)
    name = payload.name or (q["name"] if q else sym)
    row = models.WatchlistStock(symbol=sym, name=name, exchange=payload.exchange, is_favourite=payload.is_favourite)
    db.add(row)
    db.commit()
    db.refresh(row)
    # In Groww mode, ask the feeder to start tracking this symbol immediately
    if app_settings.data_provider == "groww":
        try:
            from ..core.groww_feeder import GrowwFeeder
            GrowwFeeder.instance().add_symbol(sym)
        except Exception:
            pass
    return row


@router.delete("/{symbol}", status_code=204)
def remove(symbol: str, db: Session = Depends(get_db)):
    sym = symbol.upper()
    row = db.scalar(select(models.WatchlistStock).where(models.WatchlistStock.symbol == sym))
    if row is None:
        raise HTTPException(404, "Not in watchlist")
    db.delete(row)
    db.commit()


@router.patch("/{symbol}/favourite", response_model=schemas.WatchlistOut)
def favourite(symbol: str, is_favourite: bool, db: Session = Depends(get_db)):
    sym = symbol.upper()
    row = db.scalar(select(models.WatchlistStock).where(models.WatchlistStock.symbol == sym))
    if row is None:
        raise HTTPException(404, "Not in watchlist")
    row.is_favourite = is_favourite
    db.commit()
    db.refresh(row)
    return row
