"""Realistic mock market engine.

Generates ticks, aggregates them into candles across multiple timeframes,
maintains a market depth ladder (bid/ask levels) and simulates recent trades.
Everything is deterministic given the seed so the demo behaves consistently.

This is used when DATA_PROVIDER=demo (default). A real provider (Kite/Groww)
plugs into the same interface via the broker abstraction.
"""
from __future__ import annotations

import asyncio
import math
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from ..config import settings

# NSE-inspired demo universe. Realistic-ish names but purely synthetic prices.
DEMO_UNIVERSE: List[Dict[str, float | str]] = [
    {"symbol": "RATNAVEER", "name": "Ratnaveer Precision", "base": 228.0, "vol": 0.018},
    {"symbol": "INDIGOPN",  "name": "Indigo Paints",       "base": 1420.0, "vol": 0.014},
    {"symbol": "WELSPUNIND","name": "Welspun India",       "base": 152.0, "vol": 0.020},
    {"symbol": "MENONBE",   "name": "Menon Bearings",      "base": 108.0, "vol": 0.022},
    {"symbol": "LUMINO",    "name": "Lumino Industries",   "base": 118.0, "vol": 0.025},
    {"symbol": "TATASTEEL", "name": "Tata Steel",          "base": 148.0, "vol": 0.015},
    {"symbol": "INFY",      "name": "Infosys",             "base": 1620.0, "vol": 0.011},
    {"symbol": "HDFCBANK",  "name": "HDFC Bank",           "base": 1685.0, "vol": 0.009},
    {"symbol": "RELIANCE",  "name": "Reliance Industries", "base": 2960.0, "vol": 0.010},
    {"symbol": "TCS",       "name": "Tata Consultancy",    "base": 3980.0, "vol": 0.009},
    {"symbol": "SBIN",      "name": "State Bank of India", "base": 820.0, "vol": 0.013},
    {"symbol": "ITC",       "name": "ITC Ltd",             "base": 462.0, "vol": 0.012},
    {"symbol": "AXISBANK",  "name": "Axis Bank",           "base": 1140.0, "vol": 0.012},
    {"symbol": "ICICIBANK", "name": "ICICI Bank",          "base": 1225.0, "vol": 0.011},
    {"symbol": "ADANIENT",  "name": "Adani Enterprises",   "base": 2740.0, "vol": 0.024},
]

TIMEFRAMES: Dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "1d": 86400,
}

# Indian market indices (simulated)
DEMO_INDICES = [
    {"symbol": "NIFTY",     "name": "NIFTY 50",       "base": 22150.0, "vol": 0.006},
    {"symbol": "BANKNIFTY", "name": "BANK NIFTY",     "base": 48200.0, "vol": 0.008},
    {"symbol": "SENSEX",    "name": "SENSEX",         "base": 73200.0, "vol": 0.006},
    {"symbol": "INDIAVIX",  "name": "India VIX",      "base": 13.4,    "vol": 0.030},
]


@dataclass
class Candle:
    t: datetime
    o: float
    h: float
    l: float
    c: float
    v: int


@dataclass
class SymbolState:
    symbol: str
    name: str
    base_price: float
    daily_volatility: float
    price: float = 0.0
    day_open: float = 0.0
    prev_close: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    volume: int = 0
    avg_volume: int = 0
    vwap_num: float = 0.0
    vwap_den: int = 0
    # candles keyed by timeframe -> deque of Candle
    candles: Dict[str, Deque[Candle]] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=1000)))
    ticks: Deque[Dict] = field(default_factory=lambda: deque(maxlen=200))
    depth_bids: List[Tuple[float, int]] = field(default_factory=list)
    depth_asks: List[Tuple[float, int]] = field(default_factory=list)
    # Drift chosen once per day per symbol
    drift: float = 0.0
    trend_strength: float = 0.0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MockMarket:
    """Thread-safe singleton mock market with a background tick loop."""

    _instance: Optional["MockMarket"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._rand = random.Random(settings.mock_seed)
        self._state: Dict[str, SymbolState] = {}
        self._indices: Dict[str, SymbolState] = {}
        self._subscribers: List[asyncio.Queue] = []
        self._sub_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._max_depth = int(settings.mock_depth_levels)
        # Skip synthetic seeding when a real provider will feed live data.
        # The MockMarket then serves purely as the shared state container.
        if settings.data_provider == "demo":
            self._init_universe()
            self._seed_history()

    # ---------- Singleton ----------
    @classmethod
    def instance(cls) -> "MockMarket":
        with cls._lock:
            if cls._instance is None:
                cls._instance = MockMarket()
            return cls._instance

    # ---------- Init ----------
    def _init_universe(self) -> None:
        for s in DEMO_UNIVERSE:
            self._state[s["symbol"]] = self._make_state(
                symbol=str(s["symbol"]),
                name=str(s["name"]),
                base=float(s["base"]),
                vol=float(s["vol"]),
            )
        for s in DEMO_INDICES:
            self._indices[s["symbol"]] = self._make_state(
                symbol=str(s["symbol"]),
                name=str(s["name"]),
                base=float(s["base"]),
                vol=float(s["vol"]),
                is_index=True,
            )

    def _make_state(self, symbol: str, name: str, base: float, vol: float, is_index: bool = False) -> SymbolState:
        rng = random.Random(hash((settings.mock_seed, symbol)) & 0xFFFFFFFF)
        prev_close = base * (1 + rng.uniform(-0.01, 0.01))
        day_open = prev_close * (1 + rng.uniform(-0.005, 0.005))
        price = day_open
        drift = rng.uniform(-1.0, 1.0) * vol * 0.35
        trend_strength = rng.uniform(0.2, 0.9)
        avg_vol = int(rng.uniform(4_00_000, 40_00_000)) if not is_index else 0
        st = SymbolState(
            symbol=symbol,
            name=name,
            base_price=base,
            daily_volatility=vol,
            price=price,
            day_open=day_open,
            prev_close=prev_close,
            day_high=price,
            day_low=price,
            volume=0,
            avg_volume=avg_vol,
            drift=drift,
            trend_strength=trend_strength,
        )
        return st

    def _seed_history(self) -> None:
        """Backfill candles so charts and indicators have real history.

        Always seeds a full 375-minute session worth of 1m candles so that
        higher timeframes (5m/15m/1h) have enough bars for indicators. This
        is synthetic time — the timestamps trail up to "now" so charts look
        live regardless of wall-clock trading hours.
        """
        now = datetime.now(timezone.utc)
        minutes = 375  # ~one NSE session

        for st in list(self._state.values()) + list(self._indices.values()):
            rng = random.Random(hash((settings.mock_seed, st.symbol, "hist")) & 0xFFFFFFFF)
            price = st.day_open
            st.day_high = price
            st.day_low = price
            for i in range(minutes):
                t = now - timedelta(minutes=(minutes - i))
                o = price
                # trending random walk
                step_vol = st.daily_volatility / math.sqrt(375)
                shock = rng.gauss(0, 1) * step_vol * price
                trend = st.drift * price * step_vol * st.trend_strength
                # add a bit of intraday mean reversion around VWAP-ish base
                mean_pull = (st.day_open - price) * 0.002
                c = max(0.5, o + shock + trend + mean_pull)
                h = max(o, c) + abs(rng.gauss(0, 1)) * step_vol * price * 0.3
                l = min(o, c) - abs(rng.gauss(0, 1)) * step_vol * price * 0.3
                v = 0
                if st not in self._indices.values() and st.avg_volume:
                    v = max(0, int(rng.gauss(st.avg_volume / 375, st.avg_volume / 750)))
                    st.volume += v
                    st.vwap_num += ((h + l + c) / 3.0) * v
                    st.vwap_den += v
                st.day_high = max(st.day_high, h)
                st.day_low = min(st.day_low, l)
                candle = Candle(t=t.replace(second=0, microsecond=0), o=o, h=h, l=l, c=c, v=v)
                st.candles["1m"].append(candle)
                price = c
            st.price = price
            self._rebuild_higher_tfs(st)
            self._rebuild_depth(st)

    # ---------- Depth ----------
    def _rebuild_depth(self, st: SymbolState) -> None:
        """Build a depth ladder centred on current price."""
        rng = random.Random(hash((settings.mock_seed, st.symbol, "depth", int(time.time() // 3))) & 0xFFFFFFFF)
        tick = self._tick_size(st.price)
        bids: List[Tuple[float, int]] = []
        asks: List[Tuple[float, int]] = []
        base_qty = max(100, int(st.avg_volume / 800) or 300)
        # Slight asymmetry -> reflects market bias
        bid_bias = 1.0 + rng.uniform(-0.15, 0.25) * (1 if st.drift >= 0 else -0.5)
        ask_bias = 1.0 + rng.uniform(-0.15, 0.25) * (1 if st.drift < 0 else -0.5)
        for i in range(1, self._max_depth + 1):
            b_price = round(st.price - tick * i, 2)
            a_price = round(st.price + tick * i, 2)
            # more liquidity near touch, decay outward
            decay = math.exp(-i / (self._max_depth / 2.5))
            b_qty = max(1, int(base_qty * decay * (0.5 + rng.random()) * bid_bias))
            a_qty = max(1, int(base_qty * decay * (0.5 + rng.random()) * ask_bias))
            bids.append((b_price, b_qty))
            asks.append((a_price, a_qty))
        st.depth_bids = bids
        st.depth_asks = asks

    def _tick_size(self, price: float) -> float:
        if price >= 500:
            return 0.05
        if price >= 50:
            return 0.05
        return 0.01

    # ---------- Aggregation ----------
    def _rebuild_higher_tfs(self, st: SymbolState) -> None:
        """Rebuild higher timeframes from 1m candles."""
        ones = list(st.candles["1m"])
        if not ones:
            return
        for tf, seconds in TIMEFRAMES.items():
            if tf == "1m":
                continue
            bucket_min = seconds // 60
            buckets: Dict[datetime, List[Candle]] = defaultdict(list)
            for c in ones:
                # Anchor to epoch-aligned buckets
                epoch_min = int(c.t.timestamp() // 60)
                bucket_start_min = epoch_min - (epoch_min % bucket_min)
                bt = datetime.fromtimestamp(bucket_start_min * 60, tz=timezone.utc)
                buckets[bt].append(c)
            agg: Deque[Candle] = deque(maxlen=1000)
            for bt in sorted(buckets):
                items = buckets[bt]
                agg.append(
                    Candle(
                        t=bt,
                        o=items[0].o,
                        h=max(x.h for x in items),
                        l=min(x.l for x in items),
                        c=items[-1].c,
                        v=sum(x.v for x in items),
                    )
                )
            st.candles[tf] = agg

    # ---------- Tick loop ----------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="mock-market")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        interval = max(0.05, settings.mock_tick_interval_ms / 1000.0)
        while self._running:
            try:
                self._tick_all()
            except Exception:
                # never let the ticker die
                pass
            time.sleep(interval)

    def _tick_all(self) -> None:
        now = datetime.now(timezone.utc)
        payloads = []
        for st in list(self._state.values()) + list(self._indices.values()):
            self._advance(st, now)
            payloads.append(self._snapshot_payload(st))
        # Fan-out to subscribers
        with self._sub_lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait({"type": "ticks", "data": payloads, "ts": now.isoformat()})
            except asyncio.QueueFull:
                pass

    def _advance(self, st: SymbolState, now: datetime) -> None:
        rng = random.Random(hash((settings.mock_seed, st.symbol, int(now.timestamp() * 10))) & 0xFFFFFFFF)
        step_vol = st.daily_volatility / math.sqrt(375 * 60)  # per second
        shock = rng.gauss(0, 1) * step_vol * st.price
        trend = st.drift * st.price * step_vol * st.trend_strength * 60
        mean_pull = (st.day_open - st.price) * 0.0005
        new_price = max(0.05, st.price + shock + trend + mean_pull)
        # Round to tick size
        tick = self._tick_size(new_price)
        new_price = round(round(new_price / tick) * tick, 2)

        st.day_high = max(st.day_high, new_price)
        st.day_low = min(st.day_low, new_price)

        # Volume increment (only real stocks, not indices)
        is_index = st.symbol in self._indices
        vol_inc = 0
        if not is_index and st.avg_volume:
            per_sec = st.avg_volume / (375 * 60)
            vol_inc = max(0, int(rng.gauss(per_sec, per_sec * 0.6)))
            st.volume += vol_inc
            st.vwap_num += new_price * vol_inc
            st.vwap_den += vol_inc

        side = "BUY" if new_price >= st.price else "SELL"
        st.price = new_price
        st.updated_at = now

        # Append to 1m candle bucket
        minute = now.replace(second=0, microsecond=0)
        deque_1m = st.candles["1m"]
        if deque_1m and deque_1m[-1].t == minute:
            c = deque_1m[-1]
            c.h = max(c.h, new_price)
            c.l = min(c.l, new_price)
            c.c = new_price
            c.v += vol_inc
        else:
            deque_1m.append(Candle(t=minute, o=new_price, h=new_price, l=new_price, c=new_price, v=vol_inc))
            # rebuild higher TFs cheaply every ~30s by rebuilding whenever a new 1m closes
            self._rebuild_higher_tfs(st)

        # Trade tape
        if not is_index and vol_inc > 0:
            st.ticks.append({
                "symbol": st.symbol,
                "price": new_price,
                "quantity": max(1, vol_inc),
                "side": side,
                "timestamp": now.isoformat(),
            })

        # Refresh depth occasionally
        if rng.random() < 0.15:
            self._rebuild_depth(st)

    def _snapshot_payload(self, st: SymbolState) -> Dict:
        change = st.price - st.prev_close
        change_pct = (change / st.prev_close) * 100 if st.prev_close else 0.0
        return {
            "symbol": st.symbol,
            "price": st.price,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": st.volume,
            "day_high": st.day_high,
            "day_low": st.day_low,
            "vwap": self.vwap(st),
        }

    # ---------- Public queries ----------
    def is_index(self, symbol: str) -> bool:
        return symbol in self._indices

    def universe(self) -> List[Dict]:
        return [{"symbol": s["symbol"], "name": s["name"]} for s in DEMO_UNIVERSE]

    def get_symbol_state(self, symbol: str) -> Optional[SymbolState]:
        return self._state.get(symbol) or self._indices.get(symbol)

    def vwap(self, st: SymbolState) -> float:
        if st.vwap_den <= 0:
            return round(st.price, 2)
        return round(st.vwap_num / st.vwap_den, 2)

    def get_quote(self, symbol: str) -> Optional[Dict]:
        st = self.get_symbol_state(symbol)
        if not st:
            return None
        change = st.price - st.prev_close
        change_pct = (change / st.prev_close) * 100 if st.prev_close else 0.0
        return {
            "symbol": st.symbol,
            "name": st.name,
            "price": round(st.price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "day_open": round(st.day_open, 2),
            "day_high": round(st.day_high, 2),
            "day_low": round(st.day_low, 2),
            "prev_close": round(st.prev_close, 2),
            "volume": st.volume,
            "avg_volume": st.avg_volume,
            "vwap": self.vwap(st),
            "upper_circuit": round(st.prev_close * 1.20, 2),
            "lower_circuit": round(st.prev_close * 0.80, 2),
            "timestamp": st.updated_at,
        }

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> List[Candle]:
        st = self.get_symbol_state(symbol)
        if not st:
            return []
        tf = timeframe if timeframe in TIMEFRAMES else "5m"
        candles = list(st.candles.get(tf, []))
        return candles[-limit:]

    def get_depth(self, symbol: str, levels: int) -> Optional[Dict]:
        st = self.get_symbol_state(symbol)
        if not st:
            return None
        levels = max(1, min(levels, self._max_depth))
        bids = st.depth_bids[:levels]
        asks = st.depth_asks[:levels]
        bid_total = sum(q for _, q in bids)
        ask_total = sum(q for _, q in asks)
        spread = round((asks[0][0] - bids[0][0]) if bids and asks else 0.0, 2)
        total = bid_total + ask_total
        imbalance = ((bid_total - ask_total) / total * 100) if total else 0.0
        dom = "BUY" if imbalance > 5 else "SELL" if imbalance < -5 else "NEUTRAL"
        return {
            "symbol": st.symbol,
            "timestamp": st.updated_at,
            "bids": [{"price": p, "quantity": q, "orders": max(1, q // 100)} for p, q in bids],
            "asks": [{"price": p, "quantity": q, "orders": max(1, q // 100)} for p, q in asks],
            "bid_total": bid_total,
            "ask_total": ask_total,
            "spread": spread,
            "imbalance_pct": round(imbalance, 2),
            "dominant_side": dom,
            "available_levels": self._max_depth,
        }

    def get_ticks(self, symbol: str, limit: int = 50) -> List[Dict]:
        st = self.get_symbol_state(symbol)
        if not st:
            return []
        return list(st.ticks)[-limit:]

    def indices(self) -> List[Dict]:
        out = []
        for st in self._indices.values():
            change = st.price - st.prev_close
            pct = (change / st.prev_close) * 100 if st.prev_close else 0
            out.append({
                "symbol": st.symbol,
                "name": st.name,
                "value": round(st.price, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
            })
        return out

    def market_overview(self) -> Dict:
        quotes = [self.get_quote(s["symbol"]) for s in DEMO_UNIVERSE]
        quotes = [q for q in quotes if q]
        advances = sum(1 for q in quotes if q["change"] > 0)
        declines = sum(1 for q in quotes if q["change"] < 0)
        unchanged = len(quotes) - advances - declines
        gainers = sorted(quotes, key=lambda q: q["change_pct"], reverse=True)[:5]
        losers = sorted(quotes, key=lambda q: q["change_pct"])[:5]
        volume = sorted(quotes, key=lambda q: q["volume"], reverse=True)[:5]
        return {
            "status": "LIVE",
            "server_time": datetime.now(timezone.utc),
            "indices": self.indices(),
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
            "top_gainers": gainers,
            "top_losers": losers,
            "top_volume": volume,
        }

    # ---------- Pub-sub for websockets ----------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._sub_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass
