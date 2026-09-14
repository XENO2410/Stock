"""Confluence-based backtester endpoints.

Distinct from the existing /api/backtest which runs a small hand-written
strategy. This one runs the SAME analysis+confluence engine used by the
UI - a strict requirement of Phase 3.

  POST /api/backtest/v2/run       run an end-to-end backtest, return metrics
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..backtesting.engine import BacktestConfig, run_backtest
from ..backtesting.replay_session import create_from_csv, create_from_mock


router = APIRouter(prefix="/api/backtest/v2", tags=["backtest-v2"])


class RunIn(BaseModel):
    symbol: str
    timeframe: str = "5m"
    source: Literal["csv", "mock"] = "csv"
    train_frac: float = 0.7
    warmup_bars: int = 30
    max_bars: Optional[int] = None
    risk_per_trade: float = 250.0
    brokerage_per_order: float = 20.0
    slippage_bps: float = 5.0
    min_risk_reward: float = 1.5
    close_at_end: bool = True


@router.post("/run")
def run(payload: RunIn) -> dict:
    if payload.source == "csv":
        session = create_from_csv(payload.symbol.upper(), payload.timeframe)
        if session is None:
            raise HTTPException(
                404,
                f"No CSV data for {payload.symbol}. Drop <SYMBOL>_<TIMEFRAME>.csv "
                f"into backend/data/csv/ first.",
            )
    else:
        session = create_from_mock(payload.symbol.upper(), payload.timeframe)
        if session is None:
            raise HTTPException(500, "Simulator produced no candles.")

    cfg = BacktestConfig(
        timeframe=payload.timeframe,
        train_frac=payload.train_frac,
        warmup_bars=payload.warmup_bars,
        max_bars=payload.max_bars,
        risk_per_trade=payload.risk_per_trade,
        brokerage_per_order=payload.brokerage_per_order,
        slippage_bps=payload.slippage_bps,
        min_risk_reward=payload.min_risk_reward,
        close_at_end=payload.close_at_end,
    )
    result = run_backtest(session, cfg)
    # Session was only needed for the backtest run; drop it to keep the store lean.
    from ..backtesting.replay_session import STORE
    STORE.delete(session.id)
    return asdict(result)
