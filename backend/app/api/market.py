"""Market data endpoints: quotes, candles, depth, ticks, indices, overview."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from .. import schemas
from ..brokers.factory import get_provider, provider_info
from ..core.mock_market import TIMEFRAMES, MockMarket

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/provider")
def provider() -> dict:
    return provider_info()


@router.get("/provider/diagnose")
def provider_diagnose() -> dict:
    """Run a live probe against the configured provider.

    Useful when Groww is returning 403 to see the raw response body and
    figure out whether it is a subscription, daily-approval, or credential
    issue. Never raises - always returns a structured dict.
    """
    info = provider_info()
    if info["active"] == "groww":
        try:
            from ..core.groww_feeder import GrowwFeeder
            probe = GrowwFeeder.instance().diagnose()
        except Exception as e:
            probe = {"ok": False, "error": str(e)}
        info["probe"] = probe
    return info


@router.get("/universe")
def universe() -> List[dict]:
    return get_provider().universe()


@router.get("/timeframes")
def timeframes() -> List[str]:
    return list(TIMEFRAMES.keys())


@router.get("/overview", response_model=schemas.MarketOverview)
def overview():
    return MockMarket.instance().market_overview()


@router.get("/indices", response_model=List[schemas.IndexQuote])
def indices():
    return MockMarket.instance().indices()


@router.get("/quote/{symbol}", response_model=schemas.Quote)
def quote(symbol: str):
    q = get_provider().get_quote(symbol.upper())
    if not q:
        raise HTTPException(404, f"Unknown symbol {symbol}")
    return q


@router.get("/candles/{symbol}", response_model=List[schemas.CandleOut])
def candles(symbol: str, timeframe: str = Query("5m"), limit: int = Query(300, ge=10, le=1000)):
    tf = timeframe if timeframe in TIMEFRAMES else "5m"
    data = get_provider().get_candles(symbol.upper(), tf, limit=limit)
    return data


@router.get("/depth/{symbol}", response_model=schemas.DepthSnapshot)
def depth(symbol: str, levels: int = Query(10, ge=1, le=50)):
    prov = get_provider()
    max_levels = prov.max_depth_levels()
    levels = min(levels, max_levels)
    d = prov.get_depth(symbol.upper(), levels)
    if not d:
        raise HTTPException(404, f"No depth for {symbol}")
    return d


@router.get("/ticks/{symbol}", response_model=List[schemas.Tick])
def ticks(symbol: str, limit: int = Query(50, ge=1, le=200)):
    return get_provider().get_ticks(symbol.upper(), limit)
