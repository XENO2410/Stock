"""Provider factory with graceful fallback to demo."""
from __future__ import annotations

from ..config import settings
from .base import BrokerProvider
from .groww import GrowwProvider
from .kite import KiteProvider
from .mock import MockProvider


_provider: BrokerProvider | None = None


def get_provider() -> BrokerProvider:
    global _provider
    if _provider is not None:
        return _provider
    choice = settings.data_provider
    if choice == "kite":
        p = KiteProvider()
        _provider = p if p.is_available() else MockProvider()
    elif choice == "groww":
        p = GrowwProvider()
        _provider = p if p.is_available() else MockProvider()
    else:
        _provider = MockProvider()
    return _provider


def provider_info() -> dict:
    p = get_provider()
    info: dict = {
        "configured": settings.data_provider,
        "active": p.name,
        "max_depth_levels": p.max_depth_levels(),
        "is_demo": p.name == "demo",
        "status": "ok",
    }
    if p.name == "groww":
        try:
            from ..core.groww_feeder import GrowwFeeder
            f = GrowwFeeder.instance()
            info["status"] = f.status
            info["last_error"] = f.last_error
            # If the feeder decided to fall back to demo, reflect that
            if f.status in ("forbidden", "auth_failed"):
                info["effective"] = "demo (groww unavailable)"
        except Exception:
            pass
    return info
