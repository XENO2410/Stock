"""MarketDataProvider protocol - the analysis engine's only view of data."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import DataSource, DepthSnapshot, Instrument, OHLCVSeries, Quote


class MarketDataProvider(ABC):
    """Abstract provider. Concrete providers return normalized models only."""

    #: identifier surfaced in the UI ("csv" / "mock" / "groww")
    name: str = "base"
    #: the tag associated with data produced by this provider
    source: DataSource = DataSource.DEMO

    @abstractmethod
    def search_instruments(self, query: str, limit: int = 20) -> List[Instrument]: ...

    @abstractmethod
    def get_instrument(self, symbol: str) -> Optional[Instrument]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Quote]: ...

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> OHLCVSeries: ...

    def get_depth(self, symbol: str, levels: int) -> Optional[DepthSnapshot]:
        # optional; providers without depth simply return None
        return None

    def timeframes(self) -> List[str]:
        return ["1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"]

    def has_live_feed(self) -> bool:
        return self.source is DataSource.LIVE
