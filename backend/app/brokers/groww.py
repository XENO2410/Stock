"""Groww trading data provider.

Reads are served from the shared MockMarket state container, which the
background GrowwFeeder keeps populated with live Groww data when
DATA_PROVIDER=groww. Keeping REST reads cache-backed keeps the UI
snappy and stays well under Groww's rate limits.

Live order placement is delegated to GrowwClient (opt-in).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..config import settings
from ..core.mock_market import MockMarket
from .base import BrokerProvider
from .groww_client import get_client


class GrowwProvider(BrokerProvider):
    name = "groww"
    _MAX_DEPTH = 5  # Groww exposes 5 depth levels in the quote payload

    def __init__(self) -> None:
        self._m = MockMarket.instance()

    def is_available(self) -> bool:
        # Either an explicit access token OR api key + secret (for auto-refresh)
        if settings.groww_access_token:
            return True
        return bool(settings.groww_api_key and settings.groww_api_secret)

    def universe(self) -> List[Dict]:
        return [{"symbol": st.symbol, "name": st.name} for st in list(self._m._state.values())]  # type: ignore[attr-defined]

    def get_quote(self, symbol: str) -> Optional[Dict]:
        return self._m.get_quote(symbol)

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Dict]:
        candles = self._m.get_candles(symbol, timeframe, limit=limit)
        return [
            {"time": c.t, "open": c.o, "high": c.h, "low": c.l, "close": c.c, "volume": c.v}
            for c in candles
        ]

    def get_depth(self, symbol: str, levels: int) -> Optional[Dict]:
        return self._m.get_depth(symbol, min(levels, self._MAX_DEPTH))

    def get_ticks(self, symbol: str, limit: int = 50) -> List[Dict]:
        return self._m.get_ticks(symbol, limit)

    def max_depth_levels(self) -> int:
        return self._MAX_DEPTH

    # ---------- Optional live order surface ----------

    def place_order(self, **kwargs) -> Dict:
        return get_client().place_order(kwargs)

    def cancel_order(self, order_id: str) -> Dict:
        return get_client().cancel_order(order_id)
