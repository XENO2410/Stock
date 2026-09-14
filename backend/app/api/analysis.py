"""Analysis endpoints.

Free-mode routes that use the new confluence engine on top of the
provider-agnostic MarketDataProvider abstraction.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..data.registry import available_tags, get_data_provider
from ..signals.engine import run
from ..signals.scoring import bands, default_weights


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/sources")
def list_sources() -> dict:
    """List the free data sources the analysis engine can consume."""
    return {
        "available": available_tags(),
        "notes": {
            "mock": "Deterministic simulated data. Labelled SIMULATED in the UI.",
            "csv":  "User-provided OHLCV files at backend/data/csv/<SYMBOL>_<TF>.csv.",
        },
    }


@router.get("/weights")
def weights() -> dict:
    return {"groups": default_weights(), "bands": bands()}


@router.get("/{symbol}")
def analyze(
    symbol: str,
    timeframe: str = Query("5m"),
    source: str = Query("mock"),
    min_risk_reward: float = Query(1.5, ge=0.0),
) -> dict:
    provider = get_data_provider(source)
    inst = provider.get_instrument(symbol)
    if inst is None and provider.name == "csv":
        raise HTTPException(404, f"No CSV file for {symbol}. Drop <SYMBOL>_<TIMEFRAME>.csv into backend/data/csv/.")
    report = run(provider, symbol, timeframe=timeframe, min_risk_reward=min_risk_reward)
    return asdict(report)
