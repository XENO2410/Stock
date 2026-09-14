"""Zerodha Kite provider stub.

This is a real integration surface: it does NOT fabricate a connection.
When credentials are not present, `is_available()` returns False and the
router transparently falls back to demo mode. Wiring the real Kite SDK
here (kiteconnect) is a one-file change once the user has API credentials
and completes the login flow to obtain an access token.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..config import settings
from .base import BrokerProvider


class KiteProvider(BrokerProvider):
    name = "kite"

    # Kite Connect currently exposes 5-level market depth for equity via REST
    # and 20-level via the market-depth subscription for eligible clients.
    _MAX_DEPTH = 20

    def is_available(self) -> bool:
        return bool(settings.kite_api_key and settings.kite_api_secret and settings.kite_access_token)

    def universe(self) -> List[Dict]:
        # In a real implementation: fetch instruments dump and filter NSE cash.
        return []

    def get_quote(self, symbol: str) -> Optional[Dict]:
        raise NotImplementedError(
            "KiteProvider.get_quote requires kiteconnect SDK + valid access token. "
            "Configure KITE_* env vars and add integration code here."
        )

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Dict]:
        raise NotImplementedError

    def get_depth(self, symbol: str, levels: int) -> Optional[Dict]:
        raise NotImplementedError

    def get_ticks(self, symbol: str, limit: int = 50) -> List[Dict]:
        return []

    def max_depth_levels(self) -> int:
        return self._MAX_DEPTH
