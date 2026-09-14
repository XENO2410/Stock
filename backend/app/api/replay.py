"""Replay session HTTP surface.

Endpoints exposed under /api/replay/*:

  POST   /sessions                          create a session from CSV or mock
  GET    /sessions                          list all in-memory sessions
  GET    /sessions/{id}                     current cursor + status
  DELETE /sessions/{id}
  POST   /sessions/{id}/step?count=1        move cursor forward n candles
  POST   /sessions/{id}/back?count=1        move cursor backward (research aid)
  POST   /sessions/{id}/goto                jump to index or timestamp
  POST   /sessions/{id}/reset               back to warm-up
  POST   /sessions/{id}/play                mark status=playing (client drives ticks)
  POST   /sessions/{id}/pause               mark status=paused
  POST   /sessions/{id}/speed?value=1.0
  GET    /sessions/{id}/candles?tf=5m       visible candles up to cursor
  GET    /sessions/{id}/analysis?tf=5m      full AnalysisReport at cursor
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..signals.engine import run as run_analysis
from ..backtesting.replay_session import (
    ReplayProvider,
    STANDARD_TFS,
    STORE,
    create_from_csv,
    create_from_mock,
)


router = APIRouter(prefix="/api/replay", tags=["replay"])


class CreateSessionIn(BaseModel):
    symbol: str
    timeframe: str = "5m"
    source: Literal["csv", "mock"] = "csv"


@router.post("/sessions")
def create_session(payload: CreateSessionIn) -> dict:
    if payload.source == "csv":
        session = create_from_csv(payload.symbol.upper(), payload.timeframe)
        if session is None:
            raise HTTPException(
                404,
                f"No CSV data for {payload.symbol}. Drop a file at "
                f"backend/data/csv/{payload.symbol.upper()}_<TIMEFRAME>.csv.",
            )
    else:
        session = create_from_mock(payload.symbol.upper(), payload.timeframe)
        if session is None:
            raise HTTPException(500, "Simulator produced no candles for this symbol.")
    return session.as_state()


@router.get("/sessions")
def list_sessions() -> List[dict]:
    return [s.as_state() for s in STORE.list()]


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    return s.as_state()


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    if not STORE.delete(session_id):
        raise HTTPException(404, "Session not found")


@router.post("/sessions/{session_id}/step")
def step(session_id: str, count: int = Query(1, ge=1, le=1000)) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    total = s.total()
    if not total:
        raise HTTPException(400, "Empty session")
    s.cursor = min(total - 1, s.cursor + count)
    if s.cursor >= total - 1:
        s.status = "finished"
    return s.as_state()


@router.post("/sessions/{session_id}/back")
def back(session_id: str, count: int = Query(1, ge=1, le=1000)) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    s.cursor = max(0, s.cursor - count)
    if s.status == "finished":
        s.status = "paused"
    return s.as_state()


class GotoIn(BaseModel):
    index: Optional[int] = None
    timestamp: Optional[str] = None


@router.post("/sessions/{session_id}/goto")
def goto(session_id: str, payload: GotoIn) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    total = s.total()
    if not total:
        raise HTTPException(400, "Empty session")
    if payload.index is not None:
        s.cursor = max(0, min(total - 1, payload.index))
    elif payload.timestamp:
        try:
            ts = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(400, "Invalid timestamp")
        arr = s.primary()
        # First index whose candle timestamp >= requested ts
        idx = 0
        for i, c in enumerate(arr):
            if c.timestamp >= ts:
                idx = i
                break
            idx = i
        s.cursor = idx
    else:
        raise HTTPException(400, "Provide index or timestamp")
    s.status = "paused" if s.cursor < total - 1 else "finished"
    return s.as_state()


@router.post("/sessions/{session_id}/reset")
def reset(session_id: str) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    s.cursor = min(30, s.total() - 1)
    s.status = "paused"
    return s.as_state()


@router.post("/sessions/{session_id}/play")
def play(session_id: str) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    s.status = "playing"
    return s.as_state()


@router.post("/sessions/{session_id}/pause")
def pause(session_id: str) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    s.status = "paused"
    return s.as_state()


@router.post("/sessions/{session_id}/speed")
def set_speed(session_id: str, value: float = Query(1.0, gt=0)) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    s.speed = value
    return s.as_state()


@router.get("/sessions/{session_id}/candles")
def candles(session_id: str, tf: str = Query("5m"), limit: int = Query(500, ge=10, le=5000)) -> List[dict]:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    if tf not in s.candles_by_tf:
        return []
    provider = ReplayProvider(s)
    series = provider.get_ohlcv(s.symbol, tf, limit=limit)
    return [
        {"time": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
        for c in series.candles
    ]


@router.get("/sessions/{session_id}/analysis")
def analysis(session_id: str, tf: str = Query("5m"), min_risk_reward: float = Query(1.5, ge=0.0)) -> dict:
    s = STORE.get(session_id)
    if s is None:
        raise HTTPException(404, "Session not found")
    provider = ReplayProvider(s)
    report = run_analysis(provider, s.symbol, timeframe=tf, min_risk_reward=min_risk_reward)
    return asdict(report)


@router.get("/timeframes")
def timeframes() -> List[str]:
    return STANDARD_TFS
