"""Normalized market-data models used by the analysis engine.

The analysis engine never touches provider-specific shapes. Providers
translate their native payloads into these dataclasses so that a change of
data source (Mock -> CSV -> Groww live) does not touch downstream code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class DataSource(str, Enum):
    DEMO = "DEMO"              # deterministic simulator, not real
    SIMULATED = "SIMULATED"    # random walk / synthetic, not real
    HISTORICAL = "HISTORICAL"  # persisted OHLCV from disk / DB
    CSV = "CSV"                # user-provided file
    LIVE = "LIVE"              # authenticated live feed

    def is_realtime(self) -> bool:
        return self is DataSource.LIVE


@dataclass(frozen=True)
class Instrument:
    symbol: str            # our canonical: uppercase, no exchange prefix
    exchange: str          # NSE / BSE / MCX ...
    trading_symbol: str    # exchange-native trading symbol
    display_name: str
    segment: str           # CASH / FNO / COMMODITY
    instrument_token: Optional[str] = None
    isin: Optional[str] = None
    currency: str = "INR"


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0

    @property
    def is_bull(self) -> bool:
        return self.close >= self.open

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class OHLCVSeries:
    """A chronologically ordered series of candles for one symbol/timeframe."""
    symbol: str
    timeframe: str
    candles: List[Candle] = field(default_factory=list)
    source: DataSource = DataSource.DEMO

    def __len__(self) -> int:
        return len(self.candles)

    def last(self) -> Optional[Candle]:
        return self.candles[-1] if self.candles else None

    def slice(self, n: int) -> "OHLCVSeries":
        return OHLCVSeries(
            symbol=self.symbol,
            timeframe=self.timeframe,
            candles=self.candles[-n:],
            source=self.source,
        )


@dataclass
class Quote:
    symbol: str
    price: float
    change: float
    change_pct: float
    day_open: float
    day_high: float
    day_low: float
    prev_close: float
    volume: int
    vwap: float
    timestamp: datetime
    source: DataSource = DataSource.DEMO


@dataclass
class DepthLevel:
    price: float
    quantity: int
    orders: int = 1


@dataclass
class DepthSnapshot:
    symbol: str
    bids: List[DepthLevel]
    asks: List[DepthLevel]
    timestamp: datetime
    source: DataSource = DataSource.DEMO
