"""Mock/demo provider backed by MockMarket."""
from __future__ import annotations

from typing import Dict, List, Optional

from ..config import settings
from ..core.mock_market import MockMarket
from .base import BrokerProvider


class MockProvider(BrokerProvider):
    name = "demo"

    def __init__(self) -> None:
        self._m = MockMarket.instance()

    def is_available(self) -> bool:
        return True

    def universe(self) -> List[Dict]:
        return self._m.universe()

    def get_quote(self, symbol: str) -> Optional[Dict]:
        return self._m.get_quote(symbol)

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Dict]:
        candles = self._m.get_candles(symbol, timeframe, limit=limit)
        return [
            {
                "time": c.t,
                "open": c.o,
                "high": c.h,
                "low": c.l,
                "close": c.c,
                "volume": c.v,
            }
            for c in candles
        ]

    def get_depth(self, symbol: str, levels: int) -> Optional[Dict]:
        return self._m.get_depth(symbol, levels)

    def get_ticks(self, symbol: str, limit: int = 50) -> List[Dict]:
        return self._m.get_ticks(symbol, limit)

    def max_depth_levels(self) -> int:
        return int(settings.mock_depth_levels)
