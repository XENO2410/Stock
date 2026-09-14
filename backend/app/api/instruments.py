"""Instrument search endpoint (free — uses public data only)."""
from __future__ import annotations

from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Query

from ..data.registry import available_tags, get_data_provider


router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("/search")
def search(
    q: str = Query("", description="Case-insensitive substring on symbol / name."),
    source: str = Query("mock"),
    limit: int = Query(20, ge=1, le=100),
) -> List[dict]:
    provider = get_data_provider(source)
    return [asdict(i) for i in provider.search_instruments(q, limit=limit)]


@router.get("/sources")
def sources() -> List[str]:
    return available_tags()
