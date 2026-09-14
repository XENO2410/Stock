"""Data provider registry.

Chooses a MarketDataProvider by tag. Never asks for money.
"""
from __future__ import annotations

from typing import Dict, Optional

from .csv_provider import CsvProvider
from .mock_adapter import MockAdapter
from .provider import MarketDataProvider

_providers: Dict[str, MarketDataProvider] = {}


def get_data_provider(tag: str = "mock") -> MarketDataProvider:
    tag = (tag or "mock").lower()
    if tag not in _providers:
        if tag == "csv":
            _providers[tag] = CsvProvider()
        elif tag == "mock":
            _providers[tag] = MockAdapter()
        else:
            # Unknown tag falls back to mock (never to a paid provider).
            _providers[tag] = MockAdapter()
    return _providers[tag]


def available_tags() -> list[str]:
    return ["mock", "csv"]
