"""WebSocket streaming: broadcasts ticks + top signals to connected clients."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..core.mock_market import MockMarket
from ..core import signal_engine as se

router = APIRouter(tags=["ws"])


@router.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    market = MockMarket.instance()
    queue = market.subscribe()
    last_signals = 0.0
    try:
        while True:
            try:
                # Wait up to 1s for a tick batch
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await ws.send_text(json.dumps(msg, default=str))
            except asyncio.TimeoutError:
                pass

            # Every ~5 seconds, push a compact top-signals snapshot
            now = datetime.now(timezone.utc).timestamp()
            if now - last_signals >= 5:
                results = se.evaluate_universe(min_confidence=0)
                results.sort(key=lambda r: r.confidence, reverse=True)
                payload = [
                    {
                        "symbol": r.symbol,
                        "action": r.action,
                        "direction": r.direction,
                        "confidence": r.confidence,
                        "strategy": r.strategy,
                    }
                    for r in results[:10]
                ]
                await ws.send_text(json.dumps({"type": "top_signals", "data": payload}))
                last_signals = now
    except WebSocketDisconnect:
        pass
    finally:
        market.unsubscribe(queue)
