"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from loguru import logger

from . import __version__
from .api import analytics, backtest, goal, journal, market, positions, signals, watchlist, ws
from .api import settings_api as settings_router
from .brokers.factory import provider_info
from .config import settings
from .core.mock_market import MockMarket
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    m = MockMarket.instance()
    info = provider_info()
    if info["active"] == "groww":
        # Real market feeder takes over; leave MockMarket as the shared state
        # container but do not start the random-walk ticker.
        from .core.groww_feeder import GrowwFeeder
        try:
            feeder = GrowwFeeder.instance()
            feeder.start()
            logger.info("Groww live feeder started")
        except Exception as e:
            logger.error("Groww feeder failed to start, falling back to demo: {}", e)
            m.start()
    else:
        m.start()
    yield
    m.stop()


app = FastAPI(
    title="Personal Intraday Trading Assistant",
    version=__version__,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "server_time": datetime.now(timezone.utc),
        "provider": provider_info(),
        "environment": settings.app_env,
    }


app.include_router(market.router)
app.include_router(watchlist.router)
app.include_router(signals.router)
app.include_router(positions.router)
app.include_router(goal.router)
app.include_router(journal.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)
app.include_router(backtest.router)
app.include_router(ws.router)
