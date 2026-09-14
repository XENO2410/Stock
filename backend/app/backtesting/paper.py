"""Paper-trade model + intra-candle fill rules used by replay and backtester.

Rule for the ambiguous case where a single candle's [low, high] contains
both the stop and the target:

    ASSUME THE STOP FILLS FIRST (pessimistic execution).

This is the safer assumption for a research tool - it never overstates
strategy performance. The choice is documented and returned in trade
records under `resolution` so the user can see when it was applied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..data.models import Candle


@dataclass
class PaperTrade:
    symbol: str
    timeframe: str
    direction: str                # LONG | SHORT
    entry_index: int
    entry_time: datetime
    entry_price: float
    stop: float
    target: float
    quantity: int
    signal_score: int = 0
    signal_reasons: List[str] = field(default_factory=list)

    exit_index: Optional[int] = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    reason: Optional[str] = None      # target | stop | eod | manual
    resolution: str = "clean"          # clean | both_touched_stop_first

    fees: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    r_multiple: float = 0.0

    def is_open(self) -> bool:
        return self.exit_index is None

    def risk_per_share(self) -> float:
        return abs(self.entry_price - self.stop)


def _apply_slippage(price: float, direction: str, side: str, slippage_bps: float) -> float:
    """Move price against us on entry and exit."""
    slip = price * slippage_bps / 10000.0
    if (direction == "LONG" and side == "entry") or (direction == "SHORT" and side == "exit"):
        return price + slip
    return price - slip


def open_trade(
    *,
    symbol: str,
    timeframe: str,
    direction: str,
    entry_index: int,
    entry_time: datetime,
    entry_price: float,
    stop: float,
    target: float,
    quantity: int,
    signal_score: int,
    signal_reasons: List[str],
    brokerage: float,
    slippage_bps: float,
) -> PaperTrade:
    price = _apply_slippage(entry_price, direction, "entry", slippage_bps)
    trade = PaperTrade(
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        entry_index=entry_index,
        entry_time=entry_time,
        entry_price=round(price, 4),
        stop=stop,
        target=target,
        quantity=quantity,
        signal_score=signal_score,
        signal_reasons=list(signal_reasons),
        fees=brokerage,
        slippage=abs(price - entry_price) * quantity,
    )
    return trade


def try_close_on_candle(
    trade: PaperTrade,
    candle: Candle,
    idx: int,
    brokerage: float,
    slippage_bps: float,
) -> bool:
    """Check whether the candle triggers stop or target for an open trade."""
    if not trade.is_open():
        return False

    if trade.direction == "LONG":
        hit_stop = candle.low <= trade.stop
        hit_target = candle.high >= trade.target
    else:
        hit_stop = candle.high >= trade.stop
        hit_target = candle.low <= trade.target

    if not (hit_stop or hit_target):
        return False

    # Pessimistic: if both touched in the same candle, assume stop fills first.
    if hit_stop and hit_target:
        exit_price = trade.stop
        reason = "stop"
        trade.resolution = "both_touched_stop_first"
    elif hit_stop:
        exit_price = trade.stop
        reason = "stop"
    else:
        exit_price = trade.target
        reason = "target"

    exit_price = _apply_slippage(exit_price, trade.direction, "exit", slippage_bps)
    trade.exit_index = idx
    trade.exit_time = candle.timestamp
    trade.exit_price = round(exit_price, 4)
    trade.reason = reason
    trade.fees += brokerage
    trade.slippage += abs(exit_price - (trade.stop if reason == "stop" else trade.target)) * trade.quantity

    sign = 1 if trade.direction == "LONG" else -1
    gross = sign * (trade.exit_price - trade.entry_price) * trade.quantity
    trade.pnl = round(gross - trade.fees, 2)
    risk = trade.risk_per_share() * trade.quantity
    trade.r_multiple = round(trade.pnl / risk, 3) if risk > 0 else 0.0
    return True


def force_close(trade: PaperTrade, candle: Candle, idx: int, brokerage: float, slippage_bps: float, reason: str = "eod") -> None:
    if not trade.is_open():
        return
    exit_price = _apply_slippage(candle.close, trade.direction, "exit", slippage_bps)
    trade.exit_index = idx
    trade.exit_time = candle.timestamp
    trade.exit_price = round(exit_price, 4)
    trade.reason = reason
    trade.fees += brokerage
    sign = 1 if trade.direction == "LONG" else -1
    gross = sign * (trade.exit_price - trade.entry_price) * trade.quantity
    trade.pnl = round(gross - trade.fees, 2)
    risk = trade.risk_per_share() * trade.quantity
    trade.r_multiple = round(trade.pnl / risk, 3) if risk > 0 else 0.0
