"""CSV upload + library endpoints for the historical data manager.

  POST /api/csv/upload            multipart/form-data: symbol, timeframe, file
  GET  /api/csv/library           list files currently in backend/data/csv/
  DELETE /api/csv/library/{name}  remove a file (name only, no path traversal)

Validation:
  * Required columns: timestamp, open, high, low, close, volume
  * Rows with missing / non-numeric OHLC are rejected
  * Timestamps parsed as ISO 8601 or epoch (s / ms)
  * Duplicate timestamps de-duplicated (last wins)
  * Rows re-sorted chronologically
  * Empty files rejected
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile


CSV_ROOT = Path(__file__).resolve().parents[2] / "data" / "csv"
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
SAFE_NAME = re.compile(r"^[A-Z0-9_.\-]+\.csv$")

router = APIRouter(prefix="/api/csv", tags=["csv"])


def _parse_ts(value: str) -> datetime:
    v = value.strip()
    if not v:
        raise ValueError("empty timestamp")
    try:
        n = float(v)
        if n > 1e12:
            n = n / 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    except ValueError:
        pass
    s = v.replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/upload")
async def upload(
    symbol: str = Form(...),
    timeframe: str = Form(...),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "File must be a .csv")
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset({f.lower() for f in reader.fieldnames}):
        raise HTTPException(400, f"CSV must have columns: {sorted(REQUIRED_COLUMNS)}")

    seen: Dict[datetime, Dict[str, Any]] = {}
    rejected = 0
    total = 0
    for row in reader:
        total += 1
        try:
            ts = _parse_ts(row["timestamp"])
            o = float(row["open"])
            h = float(row["high"])
            lo = float(row["low"])
            c = float(row["close"])
            v = int(float(row.get("volume") or 0))
            if not (h >= max(o, c) >= min(o, c) >= lo):
                raise ValueError("OHLC invariant violated")
        except (KeyError, ValueError):
            rejected += 1
            continue
        seen[ts] = {"timestamp": ts.isoformat(), "open": o, "high": h, "low": lo, "close": c, "volume": v}
    if not seen:
        raise HTTPException(400, "No valid rows found in the CSV.")

    sym = re.sub(r"[^A-Z0-9]", "", symbol.upper())
    tf = re.sub(r"[^a-zA-Z0-9]", "", timeframe.lower())
    if not sym or not tf:
        raise HTTPException(400, "Invalid symbol or timeframe.")

    CSV_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = CSV_ROOT / f"{sym}_{tf}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for ts in sorted(seen):
            writer.writerow(seen[ts])

    first = min(seen)
    last = max(seen)
    return {
        "saved_as": out_path.name,
        "symbol": sym,
        "timeframe": tf,
        "total_rows": total,
        "accepted_rows": len(seen),
        "rejected_rows": rejected,
        "duplicates_dropped": max(0, total - rejected - len(seen)),
        "first_timestamp": first.isoformat(),
        "last_timestamp": last.isoformat(),
    }


@router.get("/library")
def library() -> List[Dict[str, Any]]:
    if not CSV_ROOT.exists():
        return []
    out = []
    for p in sorted(CSV_ROOT.glob("*.csv")):
        stat = p.stat()
        name = p.stem
        parts = name.split("_", 1)
        sym = parts[0] if parts else name
        tf = parts[1] if len(parts) > 1 else ""
        out.append({
            "file": p.name,
            "symbol": sym,
            "timeframe": tf,
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return out


@router.delete("/library/{filename}", status_code=204)
def remove(filename: str):
    if not SAFE_NAME.match(filename):
        raise HTTPException(400, "Illegal filename")
    path = CSV_ROOT / filename
    if not path.exists() or not path.is_file() or path.parent.resolve() != CSV_ROOT.resolve():
        raise HTTPException(404, "File not found")
    path.unlink()
