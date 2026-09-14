"""Aggregate lower-timeframe candles into higher timeframes.

Used by the replay engine when the user has only uploaded, say, 5m candles
but the analysis engine also wants 15m / 1h / 4h / 1d for multi-timeframe
alignment. Aggregation is deterministic and only ever combines closed
candles - never fabricates data past the visible cursor.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Sequence

from ..data.models import Candle


TF_MINUTES: Dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def can_aggregate(base_tf: str, target_tf: str) -> bool:
    if base_tf not in TF_MINUTES or target_tf not in TF_MINUTES:
        return False
    if target_tf == base_tf:
        return True
    b = TF_MINUTES[base_tf]
    t = TF_MINUTES[target_tf]
    return t > b and (t % b == 0)


def aggregate(candles: Sequence[Candle], base_tf: str, target_tf: str) -> List[Candle]:
    """Aggregate candles from base_tf to target_tf. Returns [] if impossible."""
    if not candles:
        return []
    if target_tf == base_tf:
        return list(candles)
    if not can_aggregate(base_tf, target_tf):
        return []
    bucket_min = TF_MINUTES[target_tf]

    buckets: Dict[datetime, List[Candle]] = defaultdict(list)
    for c in candles:
        epoch_min = int(c.timestamp.timestamp() // 60)
        bucket_start_min = epoch_min - (epoch_min % bucket_min)
        bt = datetime.fromtimestamp(bucket_start_min * 60, tz=c.timestamp.tzinfo)
        buckets[bt].append(c)

    out: List[Candle] = []
    for bt in sorted(buckets):
        items = buckets[bt]
        out.append(
            Candle(
                timestamp=bt,
                open=items[0].open,
                high=max(x.high for x in items),
                low=min(x.low for x in items),
                close=items[-1].close,
                volume=sum(x.volume for x in items),
            )
        )
    return out
