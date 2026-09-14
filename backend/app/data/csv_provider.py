"""CSV historical provider.

Reads OHLCV files from `<repo>/backend/data/csv/<SYMBOL>_<TIMEFRAME>.csv`.

Standard format (header required):
    timestamp,open,high,low,close,volume

Timestamp accepted formats:
    ISO 8601 (`2026-09-10T09:15:00+00:00` or `2026-09-10 09:15:00`)
    Epoch seconds (integer)
    Epoch milliseconds (integer > 10^12)
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Candle, DataSource, Instrument, OHLCVSeries, Quote
from .provider import MarketDataProvider


DEFAULT_CSV_ROOT = Path(__file__).resolve().parents[2] / "data" / "csv"


def _parse_ts(value: str) -> datetime:
    value = value.strip()
    if not value:
        raise ValueError("empty timestamp")
    # try epoch
    try:
        n = float(value)
        if n > 1e12:
            n = n / 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    except ValueError:
        pass
    # ISO 8601 or 'YYYY-MM-DD HH:MM:SS'
    v = value.replace("Z", "+00:00")
    if " " in v and "T" not in v:
        v = v.replace(" ", "T", 1)
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class CsvProvider(MarketDataProvider):
    name = "csv"
    source = DataSource.CSV

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else DEFAULT_CSV_ROOT
        self._instruments: Dict[str, Instrument] = {}
        self._scan_instruments()

    # ---------------- instrument catalogue ----------------

    def _scan_instruments(self) -> None:
        if not self.root.exists():
            return
        seen: Dict[str, Instrument] = {}
        for path in self.root.glob("*.csv"):
            name = path.stem  # SYMBOL or SYMBOL_TIMEFRAME
            sym = name.split("_", 1)[0].upper()
            if sym in seen:
                continue
            seen[sym] = Instrument(
                symbol=sym,
                exchange="NSE",
                trading_symbol=sym,
                display_name=sym,
                segment="CASH",
            )
        self._instruments = seen

    def search_instruments(self, query: str, limit: int = 20) -> List[Instrument]:
        q = query.upper().strip()
        items = list(self._instruments.values())
        if not q:
            return items[:limit]
        return [i for i in items if q in i.symbol][:limit]

    def get_instrument(self, symbol: str) -> Optional[Instrument]:
        return self._instruments.get(symbol.upper())

    # ---------------- data reads ----------------

    def _find_file(self, symbol: str, timeframe: str) -> Optional[Path]:
        symbol = symbol.upper()
        candidates = [
            self.root / f"{symbol}_{timeframe}.csv",
            self.root / f"{symbol}.csv",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def _read(self, path: Path, limit: int) -> List[Candle]:
        rows: List[Candle] = []
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append(
                        Candle(
                            timestamp=_parse_ts(row["timestamp"]),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=int(float(row.get("volume") or 0)),
                        )
                    )
                except (KeyError, ValueError):
                    # skip malformed rows silently; the file may have header oddities
                    continue
        rows.sort(key=lambda c: c.timestamp)
        return rows[-limit:] if limit else rows

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> OHLCVSeries:
        path = self._find_file(symbol, timeframe)
        candles: List[Candle] = self._read(path, limit) if path else []
        return OHLCVSeries(symbol=symbol.upper(), timeframe=timeframe, candles=candles, source=self.source)

    def get_quote(self, symbol: str) -> Optional[Quote]:
        # Synthesise a quote from the last candle in the smallest available TF.
        for tf in ("1m", "5m", "15m", "1h", "1d"):
            series = self.get_ohlcv(symbol, tf, limit=2)
            if not series.candles:
                continue
            last = series.candles[-1]
            prev = series.candles[-2] if len(series.candles) >= 2 else last
            change = last.close - prev.close
            pct = (change / prev.close * 100) if prev.close else 0.0
            return Quote(
                symbol=symbol.upper(),
                price=last.close,
                change=round(change, 2),
                change_pct=round(pct, 2),
                day_open=last.open,
                day_high=last.high,
                day_low=last.low,
                prev_close=prev.close,
                volume=last.volume,
                vwap=last.close,
                timestamp=last.timestamp,
                source=self.source,
            )
        return None
