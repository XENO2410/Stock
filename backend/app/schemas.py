"""Pydantic schemas for the trading assistant API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------- Common ----------------

class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- Settings ----------------

class UserSettingsIn(BaseModel):
    capital: Optional[float] = None
    daily_profit_target: Optional[float] = None
    daily_max_loss: Optional[float] = None
    max_loss_per_trade: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    max_open_positions: Optional[int] = None
    min_risk_reward: Optional[float] = None
    intraday_only: Optional[bool] = None
    min_confidence: Optional[int] = None
    conservative_after_target: Optional[bool] = None
    conservative_confidence: Optional[int] = None
    brokerage_per_order: Optional[float] = None
    slippage_bps: Optional[float] = None
    auto_order_execution: Optional[bool] = None
    preferred_timeframes: Optional[str] = None
    preferred_strategies: Optional[str] = None
    signal_weights: Optional[Dict[str, int]] = None


class UserSettingsOut(OrmModel):
    id: int
    capital: float
    daily_profit_target: float
    daily_max_loss: float
    max_loss_per_trade: float
    max_trades_per_day: int
    max_open_positions: int
    min_risk_reward: float
    intraday_only: bool
    min_confidence: int
    conservative_after_target: bool
    conservative_confidence: int
    brokerage_per_order: float
    slippage_bps: float
    auto_order_execution: bool
    preferred_timeframes: str
    preferred_strategies: str
    signal_weights: Dict[str, int]
    updated_at: datetime


# ---------------- Watchlist ----------------

class WatchlistIn(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: str = "NSE"
    is_favourite: bool = False


class WatchlistOut(OrmModel):
    id: int
    symbol: str
    name: str
    exchange: str
    is_favourite: bool
    added_at: datetime


class WatchlistRow(BaseModel):
    """Enriched watchlist row with live snapshot + signal."""
    symbol: str
    name: str
    exchange: str
    price: float
    change: float
    change_pct: float
    volume: int
    relative_volume: float
    above_vwap: bool
    vwap: float
    signal_action: str
    signal_confidence: int
    trend: str
    is_favourite: bool


# ---------------- Market data ----------------

class Quote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    day_open: float
    day_high: float
    day_low: float
    prev_close: float
    volume: int
    avg_volume: int
    vwap: float
    upper_circuit: float
    lower_circuit: float
    timestamp: datetime


class CandleOut(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class DepthLevel(BaseModel):
    price: float
    quantity: int
    orders: int = 1


class DepthSnapshot(BaseModel):
    symbol: str
    timestamp: datetime
    bids: List[DepthLevel]
    asks: List[DepthLevel]
    bid_total: int
    ask_total: int
    spread: float
    imbalance_pct: float
    dominant_side: str  # BUY / SELL / NEUTRAL
    available_levels: int


class Tick(BaseModel):
    symbol: str
    price: float
    quantity: int
    side: Literal["BUY", "SELL"]
    timestamp: datetime


# ---------------- Indicators ----------------

class IndicatorSnapshot(BaseModel):
    symbol: str
    timeframe: str
    price: float
    vwap: float
    ema9: float
    ema20: float
    ema50: float
    sma20: float
    rsi14: float
    macd: float
    macd_signal: float
    macd_hist: float
    atr14: float
    prev_day_high: float
    prev_day_low: float
    day_open: float
    opening_range_high: float
    opening_range_low: float
    support: List[float]
    resistance: List[float]
    pivot: float
    relative_volume: float
    trend_1m: str
    trend_5m: str
    trend_15m: str
    trend_overall: str


# ---------------- Signals ----------------

class SignalBreakdownItem(BaseModel):
    category: str
    verdict: str
    score: int
    max_score: int


class SignalOut(OrmModel):
    id: int
    symbol: str
    direction: str
    action: str
    confidence: int
    entry_low: float
    entry_high: float
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    strategy: str
    timeframe: str
    valid_until: Optional[datetime]
    invalidation: str
    breakdown: Dict[str, Any]
    reasons: List[str]
    created_at: datetime


# ---------------- Positions / orders ----------------

class PositionIn(BaseModel):
    symbol: str
    direction: Literal["LONG", "SHORT"]
    quantity: int = Field(..., gt=0)
    entry_price: Optional[float] = None  # market if None
    stop_loss: float
    target_1: float
    target_2: Optional[float] = 0.0
    strategy: Optional[str] = ""
    signal_confidence: Optional[int] = 0
    mode: Literal["PAPER", "LIVE"] = "PAPER"
    trailing_mode: str = "fixed_rupees"
    trailing_value: float = 0.0


class PositionOut(OrmModel):
    id: int
    symbol: str
    direction: str
    quantity: int
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    trailing_mode: str
    trailing_value: float
    status: str
    mode: str
    strategy: str
    signal_confidence: int
    opened_at: datetime
    closed_at: Optional[datetime]
    exit_price: float
    realized_pnl: float
    fees: float
    notes: str


class PositionLive(BaseModel):
    """Position enriched with live price + recommendation."""
    id: int
    symbol: str
    direction: str
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target_1: float
    target_2: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    status: str
    recommendation: str  # HOLD / BOOK_PARTIAL / EXIT
    recommendation_reason: str


class ExitPositionIn(BaseModel):
    exit_price: Optional[float] = None
    reason: Optional[str] = ""


# ---------------- Position sizing ----------------

class PositionSizeIn(BaseModel):
    symbol: Optional[str] = None
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    direction: Literal["LONG", "SHORT"] = "LONG"
    override_risk: Optional[float] = None


class PositionSizeOut(BaseModel):
    risk_per_share: float
    max_quantity_by_risk: int
    capital_required: float
    available_capital: float
    suggested_quantity: int
    risk_amount: float
    warnings: List[str]


# ---------------- Daily P&L ----------------

class DailyGoalOut(BaseModel):
    trade_date: date
    daily_target: float
    daily_max_loss: float
    realized_pnl: float
    unrealized_pnl: float
    remaining_target: float
    progress_pct: float
    trades_count: int
    max_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    target_reached: bool
    loss_limit_hit: bool
    conservative_mode: bool
    active_confidence_threshold: int


# ---------------- Journal ----------------

class JournalIn(BaseModel):
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = 0.0
    quantity: int
    stop_loss: Optional[float] = 0.0
    target: Optional[float] = 0.0
    strategy: Optional[str] = ""
    signal_confidence: Optional[int] = 0
    market_conditions: Optional[str] = ""
    entry_reason: Optional[str] = ""
    exit_reason: Optional[str] = ""
    what_went_well: Optional[str] = ""
    what_went_wrong: Optional[str] = ""
    followed_signal: Optional[bool] = True
    broke_rules: Optional[bool] = False
    emotion: Optional[str] = ""
    notes: Optional[str] = ""


class JournalOut(OrmModel):
    id: int
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime]
    exit_price: float
    quantity: int
    stop_loss: float
    target: float
    pnl: float
    pnl_pct: float
    strategy: str
    signal_confidence: int
    market_conditions: str
    entry_reason: str
    exit_reason: str
    what_went_well: str
    what_went_wrong: str
    followed_signal: bool
    broke_rules: bool
    emotion: str
    notes: str
    created_at: datetime


# ---------------- Analytics ----------------

class AnalyticsOverview(BaseModel):
    total_pnl: float
    today_pnl: float
    week_pnl: float
    month_pnl: float
    total_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    by_strategy: List[Dict[str, Any]]
    by_hour: List[Dict[str, Any]]


# ---------------- Backtest ----------------

class BacktestIn(BaseModel):
    symbol: str
    timeframe: str = "5m"
    strategy: Literal["trend_vwap", "breakout", "pullback", "orb"] = "trend_vwap"
    days: int = 30
    capital: float = 50000
    risk_per_trade: float = 250


class BacktestOut(OrmModel):
    id: int
    symbol: str
    timeframe: str
    strategy: str
    start_date: date
    end_date: date
    capital: float
    risk_per_trade: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    net_pnl: float
    max_drawdown: float
    profit_factor: float
    win_rate: float
    params: Dict[str, Any]
    created_at: datetime


# ---------------- Market overview ----------------

class IndexQuote(BaseModel):
    symbol: str
    name: str
    value: float
    change: float
    change_pct: float


class MarketOverview(BaseModel):
    status: Literal["LIVE", "CLOSED", "PRE_OPEN"]
    server_time: datetime
    indices: List[IndexQuote]
    advances: int
    declines: int
    unchanged: int
    top_gainers: List[Quote]
    top_losers: List[Quote]
    top_volume: List[Quote]
