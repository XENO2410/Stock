"""Adapter that exposes the existing MockProvider via MarketDataProvider."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..brokers.mock import MockProvider
from ..core.mock_market import DEMO_UNIVERSE
from .models import Candle, DataSource, DepthLevel, DepthSnapshot, Instrument, OHLCVSeries, Quote
from .provider import MarketDataProvider


class MockAdapter(MarketDataProvider):
    name = "mock"
    source = DataSource.SIMULATED

    def __init__(self) -> None:
        self._m = MockProvider()

    # ---------------- instruments ----------------

    def _instruments(self) -> List[Instrument]:
        out = []
        for u in DEMO_UNIVERSE:
            out.append(
                Instrument(
                    symbol=str(u["symbol"]).upper(),
                    exchange="NSE",
                    trading_symbol=str(u["symbol"]).upper(),
                    display_name=str(u["name"]),
                    segment="CASH",
                )
            )
        return out

    def search_instruments(self, query: str, limit: int = 20) -> List[Instrument]:
        q = query.upper().strip()
        if not q:
            return self._instruments()[:limit]
        hits = [i for i in self._instruments() if q in i.symbol or q in i.display_name.upper()]
        return hits[:limit]

    def get_instrument(self, symbol: str) -> Optional[Instrument]:
        for i in self._instruments():
            if i.symbol == symbol.upper():
                return i
        return None

    # ---------------- quotes / candles ----------------

    def get_quote(self, symbol: str) -> Optional[Quote]:
        raw = self._m.get_quote(symbol.upper())
        if not raw:
            return None
        ts = raw["timestamp"]
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                ts = datetime.now(timezone.utc)
        return Quote(
            symbol=raw["symbol"],
            price=float(raw["price"]),
            change=float(raw["change"]),
            change_pct=float(raw["change_pct"]),
            day_open=float(raw["day_open"]),
            day_high=float(raw["day_high"]),
            day_low=float(raw["day_low"]),
            prev_close=float(raw["prev_close"]),
            volume=int(raw["volume"]),
            vwap=float(raw["vwap"]),
            timestamp=ts,
            source=self.source,
        )

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> OHLCVSeries:
        raw = self._m.get_candles(symbol.upper(), timeframe, limit=limit)
        candles = [
            Candle(
                timestamp=c["time"] if isinstance(c["time"], datetime) else datetime.fromisoformat(str(c["time"])),
                open=float(c["open"]),
                high=float(c["high"]),
                low=float(c["low"]),
                close=float(c["close"]),
                volume=int(c["volume"]),
            )
            for c in raw
        ]
        return OHLCVSeries(symbol=symbol.upper(), timeframe=timeframe, candles=candles, source=self.source)

    def get_depth(self, symbol: str, levels: int) -> Optional[DepthSnapshot]:
        raw = self._m.get_depth(symbol.upper(), levels)
        if not raw:
            return None
        ts = raw["timestamp"]
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                ts = datetime.now(timezone.utc)
        return DepthSnapshot(
            symbol=raw["symbol"],
            bids=[DepthLevel(price=b["price"], quantity=b["quantity"], orders=b.get("orders", 1)) for b in raw["bids"]],
            asks=[DepthLevel(price=a["price"], quantity=a["quantity"], orders=a.get("orders", 1)) for a in raw["asks"]],
            timestamp=ts,
            source=self.source,
        )
