"""Settings endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from .deps import DEFAULT_WEIGHTS, get_or_create_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=schemas.UserSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    row = get_or_create_settings(db)
    db.commit()
    return row


@router.put("", response_model=schemas.UserSettingsOut)
def update_settings(payload: schemas.UserSettingsIn, db: Session = Depends(get_db)):
    row = get_or_create_settings(db)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    if row.signal_weights is None:
        row.signal_weights = DEFAULT_WEIGHTS.copy()
    db.commit()
    db.refresh(row)
    return row


@router.get("/default-weights")
def default_weights():
    return DEFAULT_WEIGHTS
