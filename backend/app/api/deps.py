"""Helpers shared across routers."""
from __future__ import annotations

from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models


DEFAULT_WEIGHTS: Dict[str, int] = {
    "trend": 20,
    "vwap": 15,
    "ema": 12,
    "volume": 15,
    "price_action": 15,
    "order_book": 10,
    "momentum": 8,
    "mtf": 5,
}


def get_or_create_settings(db: Session) -> models.UserSettings:
    row = db.scalar(select(models.UserSettings).limit(1))
    if row is None:
        row = models.UserSettings(signal_weights=DEFAULT_WEIGHTS.copy())
        db.add(row)
        db.flush()
    if not row.signal_weights:
        row.signal_weights = DEFAULT_WEIGHTS.copy()
    return row
