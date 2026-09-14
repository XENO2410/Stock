"""Groww live market feeder.

Populates the shared MockMarket state container with real quotes, depth,
and historical candles from the Groww Trading API. This design lets the
signal engine, WebSocket, watchlist and UI keep working unchanged - only
the numbers now come from Groww instead of the random-walk simulator.

Polling strategy (well under Groww's 300 req/min Live-Data budget):
  * every 2s: batched LTP for all subscribed symbols (1 call regardless of count)
  * every 4s: full quote for each subscribed symbol (for depth + OHLC)
  * once per new symbol: historical candles for 1m/5m/15m/1h/1d timeframes

Historical candles are backfilled once; new 1m candles are appended in-place
as LTP updates arrive.
"""
from __future__ import annotations

import csv
import io
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from sqlalchemy import select

from ..brokers.groww_client import GrowwAPIError, GrowwAuthError, get_client
from ..db import SessionLocal
from ..models import WatchlistStock
from .mock_market import Candle, MockMarket, SymbolState, TIMEFRAMES

# Which timeframes we backfill from Groww history
BACKFILL_TFS: Dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "1d": 1440,
}

BACKFILL_LOOKBACK_MIN: Dict[str, int] = {
    # (~ up to Groww's per-interval max range documented in their docs)
    "1m": 60 * 24,             # last 24h of 1m
    "5m": 60 * 24 * 5,         # last 5 days of 5m
    "15m": 60 * 24 * 10,       # last 10 days of 15m
    "1h": 60 * 24 * 30,        # last 30 days of hourly
    "1d": 60 * 24 * 365,       # last 1y of daily
}


class GrowwFeeder:
    """Background thread that keeps MockMarket state populated from Groww."""

    _instance: Optional["GrowwFeeder"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._client = get_client()
        self._market = MockMarket.instance()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._symbols: Set[str] = set()
        self._instrument_index: Dict[str, Dict[str, str]] = {}
        self._backfilled: Set[str] = set()
        self._last_full_quote: Dict[str, float] = {}
        self._last_ltp_call = 0.0
        self._status: str = "starting"
        self._last_error: str = ""

    @classmethod
    def instance(cls) -> "GrowwFeeder":
        with cls._lock:
            if cls._instance is None:
                cls._instance = GrowwFeeder()
            return cls._instance

    @property
    def status(self) -> str:
        return self._status

    @property
    def last_error(self) -> str:
        return self._last_error

    def diagnose(self) -> Dict[str, Any]:
        d = self._client.diagnose()
        d["feeder_status"] = self._status
        d["feeder_last_error"] = self._last_error
        d["symbols"] = sorted(self._symbols)
        return d

    # ---------------- Instruments ----------------

    def _load_instruments(self) -> None:
        try:
            text = self._client.download_instruments_csv()
        except Exception as e:
            logger.warning("Could not download Groww instruments CSV: {}", e)
            return
        reader = csv.DictReader(io.StringIO(text))
        n = 0
        for row in reader:
            if row.get("segment") != "CASH":
                continue
            if row.get("instrument_type") not in ("EQ", "IDX"):
                continue
            sym = (row.get("trading_symbol") or "").strip()
            if not sym:
                continue
            self._instrument_index[sym.upper()] = {
                "exchange": row.get("exchange") or "NSE",
                "name": row.get("name") or sym,
                "instrument_type": row.get("instrument_type") or "EQ",
                "isin": row.get("isin") or "",
            }
            n += 1
        logger.info("Loaded {} Groww equity instruments", n)

    # ---------------- Symbols ----------------

    def _refresh_symbols(self) -> None:
        with SessionLocal() as db:
            rows = db.scalars(select(WatchlistStock)).all()
            self._symbols = {r.symbol.upper() for r in rows}
        # Also always include our display indices even if they aren't in the watchlist
        # (Groww returns index quotes via CASH segment as well)
        for idx in ("NIFTY", "BANKNIFTY", "SENSEX"):
            self._symbols.add(idx)

    def add_symbol(self, symbol: str) -> None:
        self._symbols.add(symbol.upper())

    # ---------------- State helpers ----------------

    def _ensure_state(self, symbol: str) -> SymbolState:
        st = self._market.get_symbol_state(symbol)
        if st is None:
            meta = self._instrument_index.get(symbol.upper()) or {}
            st = SymbolState(
                symbol=symbol.upper(),
                name=str(meta.get("name") or symbol),
                base_price=0.0,
                daily_volatility=0.0,
                avg_volume=0,
            )
            # Register into MockMarket's internal dict as an equity (not an index)
            self._market._state[symbol.upper()] = st  # type: ignore[attr-defined]
        return st

    def _exchange_for(self, symbol: str) -> str:
        return (self._instrument_index.get(symbol.upper()) or {}).get("exchange") or "NSE"

    # ---------------- Backfill ----------------

    def _backfill_symbol(self, symbol: str) -> None:
        st = self._ensure_state(symbol)
        exch = self._exchange_for(symbol)
        now = datetime.now(timezone.utc)
        for tf, mins in BACKFILL_TFS.items():
            look = BACKFILL_LOOKBACK_MIN[tf]
            start = now - timedelta(minutes=look)
            try:
                rows = self._client.get_historical_candles(
                    trading_symbol=symbol,
                    start_time=start,
                    end_time=now,
                    interval_minutes=mins,
                    exchange=exch,
                )
            except (GrowwAuthError, GrowwAPIError) as e:
                logger.warning("Groww history {} {}: {}", symbol, tf, e)
                continue
            except Exception as e:
                logger.warning("Groww history {} {}: unexpected {}", symbol, tf, e)
                continue
            dq: deque = deque(maxlen=1000)
            for row in rows:
                try:
                    ts = int(row[0])
                    dq.append(
                        Candle(
                            t=datetime.fromtimestamp(ts, tz=timezone.utc),
                            o=float(row[1]),
                            h=float(row[2]),
                            l=float(row[3]),
                            c=float(row[4]),
                            v=int(row[5]),
                        )
                    )
                except (IndexError, TypeError, ValueError):
                    continue
            if dq:
                st.candles[tf] = dq
                last = dq[-1]
                st.price = last.c
                if not st.day_open:
                    st.day_open = last.o
                st.day_high = max(st.day_high or last.h, last.h)
                st.day_low = min(st.day_low or last.l, last.l) if st.day_low else last.l
        # Aggregate other TFs (3m/10m/30m) from 1m for chart consistency
        if st.candles.get("1m"):
            self._market._rebuild_higher_tfs(st)  # type: ignore[attr-defined]

    # ---------------- Polling ----------------

    def _tick_ltp(self) -> bool:
        if not self._symbols:
            return True
        syms_by_exchange: Dict[str, List[str]] = {"NSE": [], "BSE": []}
        for s in self._symbols:
            exch = self._exchange_for(s)
            syms_by_exchange.setdefault(exch, []).append(f"{exch}_{s}")
        any_ok = False
        for exch, ex_syms in syms_by_exchange.items():
            if not ex_syms:
                continue
            # batch 50 at a time (Groww limit)
            for i in range(0, len(ex_syms), 50):
                batch = ex_syms[i : i + 50]
                try:
                    ltps = self._client.get_ltp(batch)
                except (GrowwAuthError, GrowwAPIError) as e:
                    self._last_error = str(e)
                    logger.warning("Groww LTP batch failed: {}", e)
                    continue
                except Exception as e:
                    self._last_error = str(e)
                    logger.warning("Groww LTP batch unexpected: {}", e)
                    continue
                any_ok = True
                now = datetime.now(timezone.utc)
                for key, ltp in ltps.items():
                    sym = key.split("_", 1)[1] if "_" in key else key
                    self._apply_ltp(sym, float(ltp), now)
        return any_ok

    def _apply_ltp(self, symbol: str, price: float, now: datetime) -> None:
        st = self._ensure_state(symbol)
        old = st.price or price
        st.price = price
        st.updated_at = now
        st.day_high = max(st.day_high or price, price)
        st.day_low = min(st.day_low or price, price) if st.day_low else price
        if not st.day_open:
            st.day_open = price

        # Update current 1m candle
        minute = now.replace(second=0, microsecond=0)
        dq = st.candles.setdefault("1m", deque(maxlen=1000))
        if dq and dq[-1].t == minute:
            c = dq[-1]
            c.h = max(c.h, price)
            c.l = min(c.l, price)
            c.c = price
        else:
            dq.append(Candle(t=minute, o=old, h=price, l=price, c=price, v=0))
            self._market._rebuild_higher_tfs(st)  # type: ignore[attr-defined]

        # Trade tape (synthetic side from tick direction; qty unknown from LTP alone)
        side = "BUY" if price >= old else "SELL"
        st.ticks.append(
            {
                "symbol": symbol.upper(),
                "price": price,
                "quantity": 0,
                "side": side,
                "timestamp": now.isoformat(),
            }
        )

    def _tick_full_quote(self) -> None:
        if not self._symbols:
            return
        # Rate-limit ourselves: one symbol per 400 ms
        now_s = time.time()
        due = [s for s in self._symbols if now_s - self._last_full_quote.get(s, 0) >= 4.0]
        due = due[:5]  # cap per cycle
        for s in due:
            exch = self._exchange_for(s)
            try:
                data = self._client.get_quote(trading_symbol=s, exchange=exch)
            except (GrowwAuthError, GrowwAPIError) as e:
                logger.debug("Groww quote {}: {}", s, e)
                continue
            except Exception as e:
                logger.debug("Groww quote {}: unexpected {}", s, e)
                continue
            self._apply_full_quote(s, data)
            self._last_full_quote[s] = now_s

    def _apply_full_quote(self, symbol: str, data: Dict) -> None:
        st = self._ensure_state(symbol)
        now = datetime.now(timezone.utc)
        # Prices
        last = data.get("last_price") or data.get("price")
        if last is not None:
            st.price = float(last)
        # OHLC (nested in "ohlc" or flat)
        ohlc = data.get("ohlc") or {}
        if isinstance(ohlc, dict):
            if ohlc.get("open") is not None:
                st.day_open = float(ohlc["open"])
            if ohlc.get("high") is not None:
                st.day_high = float(ohlc["high"])
            if ohlc.get("low") is not None:
                st.day_low = float(ohlc["low"])
            if ohlc.get("close") is not None:
                st.prev_close = float(ohlc["close"])
        st.volume = int(data.get("volume") or st.volume or 0)
        if data.get("average_price"):
            avg = float(data["average_price"])
            # Approximate VWAP by using avg_price as running vwap
            st.vwap_num = avg * max(st.volume, 1)
            st.vwap_den = max(st.volume, 1)
        st.updated_at = now

        # Depth
        depth = data.get("depth") or {}
        buys = depth.get("buy") or []
        sells = depth.get("sell") or []
        st.depth_bids = [(float(b["price"]), int(b["quantity"])) for b in buys if b.get("price") is not None]
        st.depth_asks = [(float(a["price"]), int(a["quantity"])) for a in sells if a.get("price") is not None]

    # ---------------- Main loop ----------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="groww-feeder")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _startup_probe(self) -> bool:
        """Verify auth + live-data reachability. Returns False on failure."""
        try:
            self._client._ensure_token()
        except Exception as e:
            self._status = "auth_failed"
            self._last_error = str(e)
            logger.error("Groww auth failed on startup: {}", e)
            return False
        # Probe a single LTP call - cheapest way to know live-data works.
        try:
            self._client.get_ltp(["NSE_RELIANCE"])
            self._status = "ok"
            self._last_error = ""
            return True
        except Exception as e:
            self._status = "forbidden"
            self._last_error = str(e)
            logger.error(
                "\n"
                "================================================================\n"
                " Groww API probe failed: {}\n"
                " Common causes:\n"
                "   - No active Trading API subscription\n"
                "     Purchase at https://groww.in/user/profile/trading-apis\n"
                "   - Daily 'Approve' click on API keys page not done today\n"
                "     https://groww.in/trade-api/api-keys\n"
                "   - Access token pasted in GROWW_API_KEY instead of\n"
                "     GROWW_ACCESS_TOKEN\n"
                " Falling back to demo data so the UI keeps working.\n"
                " Hit GET /api/market/provider/diagnose for the raw response.\n"
                "================================================================",
                e,
            )
            return False

    def _loop(self) -> None:
        if not self._startup_probe():
            # Fall back to the mock ticker so the UI stays useful.
            self._market.start()
            self._running = False
            return
        self._load_instruments()
        self._refresh_symbols()
        for s in list(self._symbols):
            if s in self._backfilled:
                continue
            try:
                self._backfill_symbol(s)
            except Exception as e:
                logger.warning("Backfill {} failed: {}", s, e)
            self._backfilled.add(s)

        watchlist_refresh_every = 30.0
        last_watchlist = time.time()
        ltp_every = 2.0
        last_ltp = 0.0
        quote_every = 1.0
        last_quote = 0.0
        consecutive_403 = 0

        while self._running:
            now = time.time()

            if now - last_watchlist >= watchlist_refresh_every:
                try:
                    self._refresh_symbols()
                    for s in list(self._symbols):
                        if s not in self._backfilled:
                            self._backfill_symbol(s)
                            self._backfilled.add(s)
                except Exception as e:
                    logger.debug("Watchlist refresh: {}", e)
                last_watchlist = now

            if now - last_ltp >= ltp_every:
                ok = self._tick_ltp()
                self._push_ticks()
                last_ltp = now
                consecutive_403 = 0 if ok else consecutive_403 + 1

            if now - last_quote >= quote_every:
                self._tick_full_quote()
                last_quote = now

            # If we keep getting rejected, stop hammering Groww and fall back
            if consecutive_403 >= 10:
                self._status = "forbidden"
                self._last_error = "Repeated 403 responses from Groww; feeder halted"
                logger.error(self._last_error + ". Falling back to demo data.")
                self._market.start()
                self._running = False
                return

            time.sleep(0.5)

    def _push_ticks(self) -> None:
        """Fan-out latest prices to WebSocket subscribers (same shape as mock)."""
        payloads = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for sym in self._symbols:
            st = self._market.get_symbol_state(sym)
            if not st or not st.price:
                continue
            change = st.price - (st.prev_close or st.price)
            pct = (change / st.prev_close * 100) if st.prev_close else 0.0
            payloads.append(
                {
                    "symbol": sym,
                    "price": round(st.price, 2),
                    "change": round(change, 2),
                    "change_pct": round(pct, 2),
                    "volume": st.volume,
                    "day_high": st.day_high,
                    "day_low": st.day_low,
                    "vwap": self._market.vwap(st),
                }
            )
        with self._market._sub_lock:  # type: ignore[attr-defined]
            subs = list(self._market._subscribers)  # type: ignore[attr-defined]
        import asyncio  # local import to avoid circulars at module import time
        for q in subs:
            try:
                q.put_nowait({"type": "ticks", "data": payloads, "ts": now_iso})
            except asyncio.QueueFull:
                pass
