"""Broker/data-provider protocol."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BrokerProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def universe(self) -> List[Dict]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Dict]: ...

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Dict]: ...

    @abstractmethod
    def get_depth(self, symbol: str, levels: int) -> Optional[Dict]: ...

    @abstractmethod
    def get_ticks(self, symbol: str, limit: int = 50) -> List[Dict]: ...

    @abstractmethod
    def max_depth_levels(self) -> int: ...

    def place_order(self, **kwargs) -> Dict:  # pragma: no cover - default no-op
        raise NotImplementedError("Live order placement not supported for this provider")

    def cancel_order(self, order_id: str) -> Dict:  # pragma: no cover
        raise NotImplementedError

    def get_positions(self) -> List[Dict]:  # pragma: no cover
        return []

    def get_orders(self) -> List[Dict]:  # pragma: no cover
        return []
