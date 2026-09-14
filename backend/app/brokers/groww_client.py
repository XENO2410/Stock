"""Groww Trading API HTTP client.

Implements the official Groww Trading API surface documented at
https://groww.in/trade-api/docs/curl. Auth via the API-Key + Secret
checksum flow: SHA-256(secret + epoch_seconds) submitted to
POST /v1/token/api/access. The returned access token is cached until
its expiry (Groww tokens reset daily at 06:00 IST).

Only official endpoints are called. No private URLs are scraped.
"""
from __future__ import annotations

import hashlib
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from ..config import settings

BASE_URL = "https://api.groww.in"
API_VERSION = "1.0"
INSTRUMENT_CSV_URL = "https://growwapi-assets.groww.in/instruments/instrument.csv"


class GrowwAuthError(RuntimeError):
    pass


class GrowwAPIError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class GrowwClient:
    """Thread-safe client that lazily refreshes its access token."""

    def __init__(self, api_key: str, api_secret: str, access_token: Optional[str] = None) -> None:
        self._key = api_key
        self._secret = api_secret
        self._token: Optional[str] = access_token or None
        self._token_expiry: float = 0.0 if not access_token else time.time() + 60 * 60 * 6
        self._lock = threading.Lock()
        self._http = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # ---------------- Auth ----------------

    def _checksum(self, ts: int) -> str:
        return hashlib.sha256((self._secret + str(ts)).encode("utf-8")).hexdigest()

    def _refresh_token(self) -> None:
        if not self._key or not self._secret:
            raise GrowwAuthError("Missing GROWW_API_KEY / GROWW_API_SECRET")
        ts = int(time.time())
        checksum = self._checksum(ts)
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-VERSION": API_VERSION,
        }
        body = {"key_type": "approval", "checksum": checksum, "timestamp": str(ts)}
        r = self._http.post("/v1/token/api/access", headers=headers, json=body)
        if r.status_code != 200:
            raise GrowwAuthError(
                f"Token endpoint returned {r.status_code}: {r.text[:400]}"
            )
        try:
            data = r.json()
        except Exception:
            raise GrowwAuthError(f"Token endpoint returned non-JSON: {r.text[:400]}")
        # Groww's token response is documented as {token, expiry, ...} but some
        # deployments wrap it as {status, payload:{token, expiry, ...}}.
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        token = payload.get("token") or payload.get("access_token")
        expiry = payload.get("expiry")
        if not token:
            raise GrowwAuthError(
                f"Token endpoint response missing 'token': {str(data)[:400]}"
            )
        self._token = token
        if expiry:
            try:
                dt = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
                self._token_expiry = dt.timestamp()
            except Exception:
                self._token_expiry = time.time() + 60 * 60 * 20
        else:
            self._token_expiry = time.time() + 60 * 60 * 20
        logger.info(
            "Groww access token refreshed; expires at {}",
            datetime.fromtimestamp(self._token_expiry, tz=timezone.utc),
        )

    # ---------------- Diagnostics ----------------

    def diagnose(self) -> Dict[str, Any]:
        """Run a minimal auth+data probe and return a structured result.

        Never raises; always returns a dict with `ok`, `stage`, and details.
        """
        out: Dict[str, Any] = {
            "has_key": bool(self._key),
            "has_secret": bool(self._secret),
            "has_static_token": bool(self._token and self._token_expiry > time.time()),
        }
        try:
            token = self._ensure_token()
            out["token_stage"] = "ok"
            out["token_preview"] = (token[:6] + "…" + token[-4:]) if token else ""
        except Exception as e:
            out["token_stage"] = "failed"
            out["error"] = str(e)
            out["ok"] = False
            return out
        # Try a tiny LTP call
        try:
            r = self._http.get(
                "/v1/live-data/ltp",
                headers=self._headers(),
                params={"segment": "CASH", "exchange_symbols": "NSE_RELIANCE"},
            )
            out["probe_status"] = r.status_code
            out["probe_body"] = r.text[:400]
            out["ok"] = r.status_code == 200
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    def _ensure_token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._token_expiry - 60:
                return self._token
            self._refresh_token()
            return self._token or ""

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Accept": "application/json",
            "X-API-VERSION": API_VERSION,
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        r = self._http.get(path, headers=self._headers(), params=params)
        return self._parse(r)

    def _post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {**self._headers(), "Content-Type": "application/json"}
        r = self._http.post(path, headers=headers, json=body or {})
        return self._parse(r)

    @staticmethod
    def _parse(r: httpx.Response) -> Dict[str, Any]:
        try:
            data = r.json()
        except Exception:
            raise GrowwAPIError("HTTP", f"{r.status_code}: {r.text[:200]}")
        if r.status_code >= 400 or data.get("status") == "FAILURE":
            err = data.get("error") or {}
            raise GrowwAPIError(str(err.get("code", r.status_code)), err.get("message") or r.text[:200])
        return data.get("payload") or {}

    # ---------------- Public endpoints ----------------

    def get_quote(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> Dict[str, Any]:
        return self._get(
            "/v1/live-data/quote",
            params={"exchange": exchange, "segment": segment, "trading_symbol": trading_symbol},
        )

    def get_ltp(self, exchange_symbols: List[str], segment: str = "CASH") -> Dict[str, float]:
        if not exchange_symbols:
            return {}
        # up to 50 per call
        payload = self._get(
            "/v1/live-data/ltp",
            params={"segment": segment, "exchange_symbols": ",".join(exchange_symbols)},
        )
        return {k: float(v) for k, v in payload.items()}

    def get_ohlc(self, exchange_symbols: List[str], segment: str = "CASH") -> Dict[str, Dict[str, float]]:
        if not exchange_symbols:
            return {}
        payload = self._get(
            "/v1/live-data/ohlc",
            params={"segment": segment, "exchange_symbols": ",".join(exchange_symbols)},
        )
        return payload

    def get_historical_candles(
        self,
        trading_symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> List[List[float]]:
        fmt = "%Y-%m-%d %H:%M:%S"
        payload = self._get(
            "/v1/historical/candle/range",
            params={
                "exchange": exchange,
                "segment": segment,
                "trading_symbol": trading_symbol,
                "start_time": start_time.strftime(fmt),
                "end_time": end_time.strftime(fmt),
                "interval_in_minutes": str(interval_minutes),
            },
        )
        return payload.get("candles") or []

    # ---------------- Orders (available but not called from UI yet) ----------------

    def place_order(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/v1/order/create", body)

    def cancel_order(self, groww_order_id: str, segment: str = "CASH") -> Dict[str, Any]:
        return self._post("/v1/order/cancel", {"groww_order_id": groww_order_id, "segment": segment})

    def modify_order(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/v1/order/modify", body)

    def list_orders(self, segment: str = "CASH", page: int = 0, page_size: int = 100) -> Dict[str, Any]:
        return self._get("/v1/order/list", params={"segment": segment, "page": page, "page_size": page_size})

    # ---------------- Instruments ----------------

    def download_instruments_csv(self) -> str:
        with httpx.Client(timeout=30.0) as c:
            r = c.get(INSTRUMENT_CSV_URL)
        r.raise_for_status()
        return r.text


_client: Optional[GrowwClient] = None
_client_lock = threading.Lock()


def get_client() -> GrowwClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = GrowwClient(
                api_key=settings.groww_api_key,
                api_secret=settings.groww_api_secret,
                access_token=settings.groww_access_token or None,
            )
        return _client
