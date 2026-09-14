"""Replay session model + MarketDataProvider view.

A ReplaySession loads a historical OHLCV dataset for a symbol and holds a
cursor pointing at the "current" candle on a primary timeframe. Any consumer
that reads through `ReplayProvider(session)` sees candles strictly up to
that cursor - never any future candle. This is the deterministic guarantee
the analysis engine relies on to avoid look-ahead bias.

The session lives only in memory (personal, single-user tool). Sessions are
created via the /api/replay/sessions endpoint and identified by a UUID.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..data.csv_provider import CsvProvider
from ..data.mock_adapter import MockAdapter
from ..data.models import Candle, DataSource, Instrument, OHLCVSeries, Quote
from ..data.provider import MarketDataProvider
from .aggregator import TF_MINUTES, aggregate

# Timeframes we try to have available for multi-timeframe analysis.
STANDARD_TFS: List[str] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


@dataclass
class ReplaySession:
    id: str
    symbol: str
    primary_tf: str
    candles_by_tf: Dict[str, List[Candle]] = field(default_factory=dict)
    cursor: int = 0                       # index into candles_by_tf[primary_tf]
    speed: float = 1.0
    status: str = "paused"                # paused | playing | finished
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_label: str = "CSV"             # CSV | SIMULATED
    train_frac: float = 0.7               # in-sample fraction for walk-forward view

    def primary(self) -> List[Candle]:
        return self.candles_by_tf.get(self.primary_tf, [])

    def total(self) -> int:
        return len(self.primary())

    def current_candle(self) -> Optional[Candle]:
        arr = self.primary()
        if not arr or self.cursor < 0:
            return None
        idx = min(self.cursor, len(arr) - 1)
        return arr[idx]

    def current_timestamp(self) -> Optional[datetime]:
        c = self.current_candle()
        return c.timestamp if c else None

    def is_out_of_sample(self) -> bool:
        n = self.total()
        if not n:
            return False
        split = int(n * self.train_frac)
        return self.cursor >= split

    def as_state(self) -> Dict:
        c = self.current_candle()
        return {
            "id": self.id,
            "symbol": self.symbol,
            "primary_timeframe": self.primary_tf,
            "cursor": self.cursor,
            "total_candles": self.total(),
            "current_timestamp": c.timestamp.isoformat() if c else None,
            "current_close": c.close if c else None,
            "status": self.status,
            "speed": self.speed,
            "available_timeframes": sorted(
                self.candles_by_tf.keys(), key=lambda t: TF_MINUTES.get(t, 999999)
            ),
            "source": self.source_label,
            "train_frac": self.train_frac,
            "in_sample_end_index": int(self.total() * self.train_frac),
            "in_sample": not self.is_out_of_sample(),
        }


# ---------------- Store (in-memory) ----------------

class _SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, ReplaySession] = {}
        self._lock = threading.RLock()

    def put(self, session: ReplaySession) -> None:
        with self._lock:
            self._sessions[session.id] = session

    def get(self, sid: str) -> Optional[ReplaySession]:
        with self._lock:
            return self._sessions.get(sid)

    def delete(self, sid: str) -> bool:
        with self._lock:
            return self._sessions.pop(sid, None) is not None

    def list(self) -> List[ReplaySession]:
        with self._lock:
            return list(self._sessions.values())


STORE = _SessionStore()


# ---------------- Factories ----------------

def _sorted_unique(candles: List[Candle]) -> List[Candle]:
    seen = {}
    for c in candles:
        seen[c.timestamp] = c            # last write wins on duplicate ts
    return [seen[k] for k in sorted(seen.keys())]


def _hydrate_all_tfs(base_tf: str, base_candles: List[Candle]) -> Dict[str, List[Candle]]:
    """Given one timeframe, derive every higher TF we can via aggregation.

    Smaller TFs (e.g. 1m from 5m) cannot be built - they simply aren't present.
    Multi-timeframe analysis handles missing TFs gracefully.
    """
    out: Dict[str, List[Candle]] = {base_tf: base_candles}
    for tf in STANDARD_TFS:
        if tf == base_tf:
            continue
        derived = aggregate(base_candles, base_tf, tf)
        if derived:
            out[tf] = derived
    return out


def create_from_csv(symbol: str, primary_tf: str) -> Optional[ReplaySession]:
    """Load a session from the on-disk CSV library.

    Prefers an exact match `<SYMBOL>_<TF>.csv`. If a lower-timeframe file
    (e.g. 1m) exists, higher timeframes are aggregated on the fly. Returns
    None if no data at all is available.
    """
    csv = CsvProvider()
    series = csv.get_ohlcv(symbol, primary_tf, limit=100_000)
    candles = _sorted_unique(series.candles) if series.candles else []
    base_tf = primary_tf
    # Fall back to the smallest available TF if the requested one is empty.
    if not candles:
        for tf in STANDARD_TFS:
            s = csv.get_ohlcv(symbol, tf, limit=100_000)
            if s.candles:
                candles = _sorted_unique(s.candles)
                base_tf = tf
                break
    if not candles:
        return None
    tfs = _hydrate_all_tfs(base_tf, candles)
    if primary_tf not in tfs:
        # requested TF not derivable - use the smallest available one instead
        primary_tf = base_tf
    session = ReplaySession(
        id=str(uuid.uuid4()),
        symbol=symbol.upper(),
        primary_tf=primary_tf,
        candles_by_tf=tfs,
        cursor=min(30, len(tfs[primary_tf]) - 1),   # seed the cursor past warm-up
        source_label="CSV",
    )
    STORE.put(session)
    return session


def create_from_mock(symbol: str, primary_tf: str) -> Optional[ReplaySession]:
    """Materialise a session from the deterministic simulator (research only)."""
    mock = MockAdapter()
    series = mock.get_ohlcv(symbol, primary_tf, limit=1000)
    if not series.candles:
        return None
    candles = _sorted_unique(series.candles)
    tfs = _hydrate_all_tfs(primary_tf, candles)
    session = ReplaySession(
        id=str(uuid.uuid4()),
        symbol=symbol.upper(),
        primary_tf=primary_tf,
        candles_by_tf=tfs,
        cursor=min(30, len(candles) - 1),
        source_label="SIMULATED",
    )
    STORE.put(session)
    return session


# ---------------- Provider view ----------------

class ReplayProvider(MarketDataProvider):
    """MarketDataProvider that never exposes candles beyond the cursor.

    All calls that ask for OHLCV are clipped to the session's current
    timestamp - the analysis engine calling this provider physically
    cannot see the future.
    """

    name = "replay"

    def __init__(self, session: ReplaySession) -> None:
        self._s = session
        self.source = (
            DataSource.HISTORICAL if session.source_label == "CSV" else DataSource.SIMULATED
        )

    def _slice_at_cursor(self, tf: str) -> List[Candle]:
        candles = self._s.candles_by_tf.get(tf, [])
        if not candles:
            return []
        cutoff = self._s.current_timestamp()
        if cutoff is None:
            return []
        # binary search would be nicer but linear is fine at these sizes
        clipped: List[Candle] = []
        for c in candles:
            if c.timestamp <= cutoff:
                clipped.append(c)
            else:
                break
        return clipped

    # ---- MarketDataProvider surface ----

    def search_instruments(self, query: str, limit: int = 20) -> List[Instrument]:
        return [self.get_instrument(self._s.symbol)] if self.get_instrument(self._s.symbol) else []

    def get_instrument(self, symbol: str) -> Optional[Instrument]:
        if symbol.upper() != self._s.symbol:
            return None
        return Instrument(
            symbol=self._s.symbol,
            exchange="NSE",
            trading_symbol=self._s.symbol,
            display_name=self._s.symbol,
            segment="CASH",
        )

    def get_quote(self, symbol: str) -> Optional[Quote]:
        c = self._s.current_candle()
        if not c or symbol.upper() != self._s.symbol:
            return None
        prev_arr = self._slice_at_cursor(self._s.primary_tf)
        prev = prev_arr[-2] if len(prev_arr) >= 2 else c
        change = c.close - prev.close
        pct = (change / prev.close * 100) if prev.close else 0.0
        return Quote(
            symbol=self._s.symbol,
            price=c.close,
            change=round(change, 2),
            change_pct=round(pct, 2),
            day_open=c.open,
            day_high=c.high,
            day_low=c.low,
            prev_close=prev.close,
            volume=c.volume,
            vwap=c.close,
            timestamp=c.timestamp,
            source=self.source,
        )

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 300) -> OHLCVSeries:
        if symbol.upper() != self._s.symbol:
            return OHLCVSeries(symbol=symbol.upper(), timeframe=timeframe, candles=[], source=self.source)
        clipped = self._slice_at_cursor(timeframe)
        return OHLCVSeries(
            symbol=self._s.symbol,
            timeframe=timeframe,
            candles=clipped[-limit:] if limit else clipped,
            source=self.source,
        )
