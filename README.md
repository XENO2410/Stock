# Personal Intraday Trading Assistant

A working end-to-end intraday **decision-support** application for the Indian
stock market (NSE), inspired by the clean Groww UX. It watches the stocks
you care about, evaluates multi-factor signals (trend + VWAP + volume +
price action + order-book + momentum) and clearly recommends
**ENTRY / EXIT / STOP LOSS / TARGET** — or an explicit **NO TRADE**.

> This is **not** financial advice and it does not guarantee profit.
> Every signal shows exactly *why* it was generated and what would
> invalidate it, so you stay in control of every decision.

---

## Quick start (demo, no broker credentials needed)

```powershell
# From the repo root
copy .env.example .env
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend docs (OpenAPI): http://localhost:8000/docs
- Health: http://localhost:8000/api/health

You will see live-updating charts, watchlists, signals, market depth and paper
trading — all backed by a realistic **mock market engine**. No external API
credentials are required for demo mode.

### Run without Docker (local dev)

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Both services read the shared `.env` at the repo root.

---

## Highlights

- **Realistic demo mode.** In-process mock market engine generates ticks,
  candles across 8 timeframes (1m…1d), a 25-level depth ladder, a trade
  tape and market indices — deterministically seeded so demos are
  reproducible.
- **Multi-factor signal engine.** Weighted, transparent scoring across
  Trend, VWAP, EMA stack, Volume, Price Action, Order Book, Momentum
  (RSI/MACD) and Multi-Timeframe alignment. Every signal explains itself.
- **First-class `NO TRADE`.** The engine will refuse to force a trade
  when quality is poor; the UI clearly explains why.
- **Daily goal system.** Configurable daily profit target and max loss
  with a live progress panel and automatic **conservative mode** once
  the target is achieved.
- **Risk-first position sizing.** Given entry, stop loss and capital,
  the app tells you exactly how many shares meet your per-trade risk.
  It never suggests increasing quantity to hit a daily goal.
- **Flexible market depth.** Level count is user-configurable
  (5/10/20/25/MAX). The provider factory exposes the true maximum the
  active data source can deliver — never fabricated.
- **Paper trading.** Full paper broker with brokerage/slippage
  assumptions, live recommendation (HOLD / BOOK_PARTIAL / EXIT), and
  auto-journal entry on close.
- **Trade journal + analytics.** By-strategy and by-hour performance,
  win rate, profit factor, max drawdown.
- **Backtesting.** Bar-by-bar simulation using only info available at
  each bar — no look-ahead.
- **Broker abstraction.** Modular provider layer (`demo`, `kite`,
  `groww`) with graceful fallback. Real integrations require your own
  credentials — the app never fabricates a connection.

---

## Feature status

| Area | Status |
| --- | --- |
| Dashboard, daily goal, watchlist, top signals | Fully working (demo) |
| Stock detail page (chart, depth, signal, ticks, trade controls) | Fully working (demo) |
| Signal engine (weighted, configurable) | Fully working |
| Position sizing + safety gates | Fully working |
| Paper trading, auto trade journal | Fully working |
| Analytics dashboard | Fully working |
| Backtesting | Working on in-memory demo candles; wire your own historical dataset for multi-day backtests |
| WebSocket live tick + top-signal stream | Fully working |
| Kite / Groww live integrations | **Adapter stubs.** Provider layer + `is_available()` gate implemented; real HTTP wiring intentionally left blank until you plug in your credentials/SDK |
| Dark mode | CSS ready; toggle can be added trivially via a class on `<html>` |
| Alerts (Telegram/email) | Notification hook points ready; not wired |
| News / event feed | Not wired (requires a licensed feed) |

---

## Configuring a real broker

The demo works out of the box. To switch to a live provider:

1. Set `DATA_PROVIDER=kite` (or `groww`) in `.env`.
2. Fill in the credential fields (`KITE_API_KEY`, `KITE_API_SECRET`,
   `KITE_ACCESS_TOKEN`, or the Groww equivalents).
3. Implement the actual HTTP/SDK calls inside
   [backend/app/brokers/kite.py](backend/app/brokers/kite.py) or
   [backend/app/brokers/groww.py](backend/app/brokers/groww.py).
   Both classes already implement the shared `BrokerProvider` protocol
   defined in [backend/app/brokers/base.py](backend/app/brokers/base.py).
4. If `is_available()` returns `False`, the factory transparently falls
   back to demo mode — features that depend on the live feed will simply
   remain in demo, so the app never lies about connection status.

Never scrape private endpoints or bypass broker security. Use each
provider's officially documented API and observe rate limits.

---

## Switching to real Groww data (fully implemented)

The Groww Trading API is wired end-to-end. To use it:

1. Get an API subscription: https://groww.in/user/profile/trading-apis
2. On https://groww.in/trade-api/api-keys click **Generate API key** and
   copy the **API Key** and **Secret**. Groww requires you to click
   "Approve" once per day on that page — this is a Groww policy, not
   this app.
3. In `.env`:
   ```
   DATA_PROVIDER=groww
   GROWW_API_KEY=your-key
   GROWW_API_SECRET=your-secret
   ```
   The app auto-generates an access token via the checksum flow
   (`POST /v1/token/api/access`) and refreshes it before the daily 06:00
   IST reset. Alternatively, paste an access token straight into
   `GROWW_ACCESS_TOKEN` and leave the secret blank.
4. Restart the backend. The header chip changes from `DEMO` to `GROWW`.

### What happens under the hood

- [backend/app/brokers/groww_client.py](backend/app/brokers/groww_client.py)
  is the low-level HTTP client (auth, quote, LTP, OHLC, historical
  candles, orders, instruments CSV).
- [backend/app/core/groww_feeder.py](backend/app/core/groww_feeder.py) is
  a background thread that on startup downloads the instrument list,
  backfills 1m / 5m / 15m / 1h / 1d candles for every watchlist symbol,
  and then keeps them fresh by polling:
  - LTP for all watchlist symbols every 2s (one call for up to 50 syms)
  - full quote (incl. 5-level depth) round-robin every ~4s per symbol
- The rest of the app — signal engine, watchlist, WebSocket stream,
  paper trading, journal — reads from the same in-memory state, so
  everything runs on real prices with no other code changes.

### What Groww exposes vs. what the UI supports

| Feature | Groww | UI behaviour |
| --- | --- | --- |
| Live LTP + OHLC | Yes | Ticks, watchlist, quote card |
| 5-level market depth | Yes | Depth ladder auto-caps to 5; `20/25/MAX` buttons disable |
| Historical candles (1/5/15/60/240/1440 min) | Yes | Chart timeframes 1m…1d work; 3m/10m/30m aggregated from 1m locally |
| Full trade tape (side + qty) | No public feed | Approximated from LTP direction; qty shows 0 |
| WebSocket stream | Not in current public API | We poll — see cadence above |
| Live order placement | Yes | Not auto-wired to the paper trade button (safer). Call `GrowwProvider.place_order(...)` from a route to enable |

### Rate limits (built-in)

The feeder stays well below Groww's published limits (300 req/min for
Live Data, 500 req/min for non-trading). If your watchlist grows past
about 40 symbols, tune the poll intervals inside
[backend/app/core/groww_feeder.py](backend/app/core/groww_feeder.py).

### If credentials are missing or the token flow fails

The provider factory returns the demo provider and the header chip stays
on `DEMO`, so you always know exactly what data you're looking at.

---

## Project structure

```
Stock/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                  FastAPI app + router wiring
│   │   ├── config.py                Settings via pydantic-settings
│   │   ├── db.py                    SQLAlchemy engine/session
│   │   ├── models.py                All ORM models
│   │   ├── schemas.py               Pydantic response/request models
│   │   ├── api/                     REST + WebSocket routers
│   │   │   ├── market.py            quotes, candles, depth, ticks, overview
│   │   │   ├── watchlist.py         CRUD + enriched watchlist rows
│   │   │   ├── signals.py           per-symbol + top-N signals
│   │   │   ├── positions.py         paper trading + sizing + safety
│   │   │   ├── goal.py              daily goal + conservative mode
│   │   │   ├── journal.py           trade journal
│   │   │   ├── analytics.py         performance dashboard
│   │   │   ├── settings_api.py      user settings + weights
│   │   │   ├── backtest.py          strategy backtester
│   │   │   └── ws.py                /ws/stream WebSocket
│   │   ├── brokers/
│   │   │   ├── base.py              BrokerProvider protocol
│   │   │   ├── mock.py              demo provider (backed by MockMarket)
│   │   │   ├── kite.py              Zerodha Kite stub
│   │   │   ├── groww.py             Groww stub
│   │   │   └── factory.py           provider selection + graceful fallback
│   │   └── core/
│   │       ├── mock_market.py       tick / candle / depth simulator
│   │       ├── indicators.py        EMA/SMA/RSI/MACD/VWAP/ATR/pivots/S-R
│   │       ├── signal_engine.py     multi-factor signal + exit engine
│   │       └── risk.py              sizing + daily P&L + safety gates
│   └── tests/                       pytest suite for indicators / risk / signals
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── app/                         Next.js App Router pages
    │   ├── page.tsx                 dashboard
    │   ├── watchlist/page.tsx
    │   ├── signals/page.tsx
    │   ├── positions/page.tsx
    │   ├── journal/page.tsx
    │   ├── analytics/page.tsx
    │   ├── backtest/page.tsx
    │   ├── settings/page.tsx
    │   └── stock/[symbol]/page.tsx  detailed stock view
    ├── components/
    │   ├── Header.tsx               nav + indices + provider chip
    │   ├── DailyGoalPanel.tsx
    │   ├── Watchlist.tsx
    │   ├── TopSignals.tsx
    │   ├── MarketOverviewCard.tsx
    │   ├── PriceChart.tsx           lightweight-charts candlestick + overlays + signal lines
    │   ├── MarketDepth.tsx          5/10/20/25/MAX depth ladder
    │   ├── SignalPanel.tsx          entry / SL / T1 / T2 / R:R + why breakdown
    │   ├── TradeControls.tsx        BUY/SELL paper with live sizing
    │   └── TickTape.tsx             time & sales
    └── lib/
        ├── api.ts                   fetch wrapper (SWR)
        ├── ws.ts                    /ws/stream React hook
        ├── types.ts                 shared TS types
        └── utils.ts                 formatters + signal colors
```

---

## Environment variables

See [.env.example](.env.example) — every field is annotated. Highlights:

| Variable | Meaning | Default |
| --- | --- | --- |
| `DATA_PROVIDER` | `demo` / `kite` / `groww` | `demo` |
| `DATABASE_URL` | SQLAlchemy URL | SQLite in `backend/data/trading.db` |
| `REDIS_ENABLED` | Enable Redis-backed cache | `false` |
| `MOCK_DEPTH_LEVELS` | Max depth levels demo will expose | `25` |
| `MOCK_TICK_INTERVAL_MS` | Demo tick rate | `500` |
| `NEXT_PUBLIC_API_BASE_URL` | Where the frontend calls the API | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_BASE_URL` | WebSocket base URL | `ws://localhost:8000` |

---

## Tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

The suite covers the highest-leverage math (indicators, position sizing,
signal engine happy paths and threshold behaviour).

---

## Known limitations

- The demo mock market is deterministic, not a market replay. It exists
  so the whole app runs end-to-end without any external dependency.
- Kite / Groww providers include the correct abstraction surface but not
  the actual HTTP calls — those must be filled in with your own
  credentials and the official SDKs. Refusal to fabricate this is
  intentional.
- The backtester simulates on the mock market's in-memory candles.
  For real historical backtests, load a persisted OHLCV dataset in
  [backend/app/api/backtest.py](backend/app/api/backtest.py) — the
  simulation loop already avoids look-ahead.
- No authentication. This is a personal-use application; if exposed
  beyond localhost, put it behind a reverse proxy with auth.
- Alerts are in-app only; browser/mobile/telegram/email delivery are
  intentionally left as extension points.

---

## Suggested next development priorities

1. Wire real Kite Connect (`kiteconnect` package) — token refresh flow,
   WebSocket ticker, orderbook subscription.
2. Persist mock ticks / candles into Postgres so backtests can span
   many days.
3. Add trailing-stop management to the exit engine (ATR / previous
   candle low / EMA-based).
4. Add browser notifications + optional Telegram alerter using the
   provider layer.
5. Add a lightweight news adapter with configurable sources and gated
   confidence adjustment (never overriding data alone).
6. Add authentication + rate limiting before deploying beyond
   localhost.