"""SQLAlchemy ORM models for the trading assistant.

Covers: user settings, watchlists, signals, positions/orders/trades,
daily P&L & goals, trade journal, strategy configs, and backtests.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ------------------------ Settings / profile ------------------------

class UserSettings(Base):
    """Single-user configuration (personal application)."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capital: Mapped[float] = mapped_column(Float, default=50000.0)
    daily_profit_target: Mapped[float] = mapped_column(Float, default=1000.0)
    daily_max_loss: Mapped[float] = mapped_column(Float, default=750.0)
    max_loss_per_trade: Mapped[float] = mapped_column(Float, default=250.0)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=5)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=3)
    min_risk_reward: Mapped[float] = mapped_column(Float, default=1.5)
    intraday_only: Mapped[bool] = mapped_column(Boolean, default=True)
    min_confidence: Mapped[int] = mapped_column(Integer, default=70)
    conservative_after_target: Mapped[bool] = mapped_column(Boolean, default=True)
    conservative_confidence: Mapped[int] = mapped_column(Integer, default=85)
    brokerage_per_order: Mapped[float] = mapped_column(Float, default=20.0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=5.0)
    auto_order_execution: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_timeframes: Mapped[str] = mapped_column(String, default="5m,15m")
    preferred_strategies: Mapped[str] = mapped_column(
        String, default="trend_vwap,breakout,pullback,orb"
    )
    signal_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


# ------------------------ Watchlist ------------------------

class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    exchange: Mapped[str] = mapped_column(String(16), default="NSE")
    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ------------------------ Signals ------------------------

class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # LONG / SHORT / NONE
    action: Mapped[str] = mapped_column(String(24))  # STRONG_BUY / BUY / NO_TRADE / SELL / STRONG_SELL
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    entry_low: Mapped[float] = mapped_column(Float, default=0.0)
    entry_high: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.0)
    target_1: Mapped[float] = mapped_column(Float, default=0.0)
    target_2: Mapped[float] = mapped_column(Float, default=0.0)
    risk_reward: Mapped[float] = mapped_column(Float, default=0.0)
    strategy: Mapped[str] = mapped_column(String(48))
    timeframe: Mapped[str] = mapped_column(String(8), default="5m")
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invalidation: Mapped[str] = mapped_column(Text, default="")
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_signals_symbol_created", "symbol", "created_at"),
    )


# ------------------------ Positions / Orders / Trades ------------------------

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # LONG / SHORT
    quantity: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.0)
    target_1: Mapped[float] = mapped_column(Float, default=0.0)
    target_2: Mapped[float] = mapped_column(Float, default=0.0)
    trailing_mode: Mapped[str] = mapped_column(String(24), default="fixed_rupees")
    trailing_value: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", index=True)
    mode: Mapped[str] = mapped_column(String(8), default="PAPER")  # PAPER / LIVE
    strategy: Mapped[str] = mapped_column(String(48), default="")
    signal_confidence: Mapped[int] = mapped_column(Integer, default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exit_price: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("positions.id"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))  # BUY / SELL
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    order_type: Mapped[str] = mapped_column(String(16), default="MARKET")
    mode: Mapped[str] = mapped_column(String(8), default="PAPER")
    status: Mapped[str] = mapped_column(String(16), default="FILLED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ------------------------ Daily P&L and goals ------------------------

class DailyPnL(Base):
    __tablename__ = "daily_pnl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    daily_target: Mapped[float] = mapped_column(Float, default=0.0)
    daily_max_loss: Mapped[float] = mapped_column(Float, default=0.0)
    target_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    loss_limit_hit: Mapped[bool] = mapped_column(Boolean, default=False)


# ------------------------ Trade journal ------------------------

class TradeJournalEntry(Base):
    __tablename__ = "trade_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("positions.id"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    entry_time: Mapped[datetime] = mapped_column(DateTime)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exit_price: Mapped[float] = mapped_column(Float, default=0.0)
    quantity: Mapped[int] = mapped_column(Integer)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.0)
    target: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    strategy: Mapped[str] = mapped_column(String(48), default="")
    signal_confidence: Mapped[int] = mapped_column(Integer, default=0)
    market_conditions: Mapped[str] = mapped_column(Text, default="")
    entry_reason: Mapped[str] = mapped_column(Text, default="")
    exit_reason: Mapped[str] = mapped_column(Text, default="")
    what_went_well: Mapped[str] = mapped_column(Text, default="")
    what_went_wrong: Mapped[str] = mapped_column(Text, default="")
    followed_signal: Mapped[bool] = mapped_column(Boolean, default=True)
    broke_rules: Mapped[bool] = mapped_column(Boolean, default=False)
    emotion: Mapped[str] = mapped_column(String(48), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ------------------------ Strategy configs ------------------------

class StrategyConfig(Base):
    __tablename__ = "strategy_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


# ------------------------ Backtests ------------------------

class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    strategy: Mapped[str] = mapped_column(String(48))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    capital: Mapped[float] = mapped_column(Float)
    risk_per_trade: Mapped[float] = mapped_column(Float)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    net_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(ForeignKey("backtests.id"), index=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime)
    exit_time: Mapped[datetime] = mapped_column(DateTime)
    direction: Mapped[str] = mapped_column(String(8))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    pnl: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(128), default="")


# ------------------------ Market data (persisted snapshots) ------------------------

class Candle(Base):
    __tablename__ = "market_candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_candle_key"),
        Index("ix_candle_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )
