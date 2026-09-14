export type Quote = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  day_open: number;
  day_high: number;
  day_low: number;
  prev_close: number;
  volume: number;
  avg_volume: number;
  vwap: number;
  upper_circuit: number;
  lower_circuit: number;
  timestamp: string;
};

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type DepthLevel = {
  price: number;
  quantity: number;
  orders: number;
};

export type DepthSnapshot = {
  symbol: string;
  timestamp: string;
  bids: DepthLevel[];
  asks: DepthLevel[];
  bid_total: number;
  ask_total: number;
  spread: number;
  imbalance_pct: number;
  dominant_side: "BUY" | "SELL" | "NEUTRAL";
  available_levels: number;
};

export type Tick = {
  symbol: string;
  price: number;
  quantity: number;
  side: "BUY" | "SELL";
  timestamp: string;
};

export type SignalOut = {
  id: number;
  symbol: string;
  direction: "LONG" | "SHORT" | "NONE";
  action:
    | "STRONG_BUY"
    | "BUY"
    | "NO_TRADE"
    | "SELL"
    | "STRONG_SELL";
  confidence: number;
  entry_low: number;
  entry_high: number;
  stop_loss: number;
  target_1: number;
  target_2: number;
  risk_reward: number;
  strategy: string;
  timeframe: string;
  valid_until: string | null;
  invalidation: string;
  breakdown: Record<string, { verdict: string; score: number; max: number }>;
  reasons: string[];
  created_at: string;
};

export type WatchlistRow = {
  symbol: string;
  name: string;
  exchange: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  relative_volume: number;
  above_vwap: boolean;
  vwap: number;
  signal_action: SignalOut["action"];
  signal_confidence: number;
  trend: string;
  is_favourite: boolean;
};

export type DailyGoal = {
  trade_date: string;
  daily_target: number;
  daily_max_loss: number;
  realized_pnl: number;
  unrealized_pnl: number;
  remaining_target: number;
  progress_pct: number;
  trades_count: number;
  max_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  target_reached: boolean;
  loss_limit_hit: boolean;
  conservative_mode: boolean;
  active_confidence_threshold: number;
};

export type IndexQuote = {
  symbol: string;
  name: string;
  value: number;
  change: number;
  change_pct: number;
};

export type MarketOverview = {
  status: "LIVE" | "CLOSED" | "PRE_OPEN";
  server_time: string;
  indices: IndexQuote[];
  advances: number;
  declines: number;
  unchanged: number;
  top_gainers: Quote[];
  top_losers: Quote[];
  top_volume: Quote[];
};

export type PositionLive = {
  id: number;
  symbol: string;
  direction: "LONG" | "SHORT";
  quantity: number;
  entry_price: number;
  current_price: number;
  stop_loss: number;
  target_1: number;
  target_2: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  status: string;
  recommendation: string;
  recommendation_reason: string;
};

export type PositionSize = {
  risk_per_share: number;
  max_quantity_by_risk: number;
  capital_required: number;
  available_capital: number;
  suggested_quantity: number;
  risk_amount: number;
  warnings: string[];
};

export type UserSettings = {
  id: number;
  capital: number;
  daily_profit_target: number;
  daily_max_loss: number;
  max_loss_per_trade: number;
  max_trades_per_day: number;
  max_open_positions: number;
  min_risk_reward: number;
  intraday_only: boolean;
  min_confidence: number;
  conservative_after_target: boolean;
  conservative_confidence: number;
  brokerage_per_order: number;
  slippage_bps: number;
  auto_order_execution: boolean;
  preferred_timeframes: string;
  preferred_strategies: string;
  signal_weights: Record<string, number>;
  updated_at: string;
};

export type JournalOut = {
  id: number;
  symbol: string;
  direction: string;
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number;
  quantity: number;
  stop_loss: number;
  target: number;
  pnl: number;
  pnl_pct: number;
  strategy: string;
  signal_confidence: number;
  market_conditions: string;
  entry_reason: string;
  exit_reason: string;
  what_went_well: string;
  what_went_wrong: string;
  followed_signal: boolean;
  broke_rules: boolean;
  emotion: string;
  notes: string;
  created_at: string;
};

export type AnalyticsOverview = {
  total_pnl: number;
  today_pnl: number;
  week_pnl: number;
  month_pnl: number;
  total_trades: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  largest_win: number;
  largest_loss: number;
  max_drawdown: number;
  by_strategy: Array<{ strategy: string; trades: number; win_rate: number; pnl: number }>;
  by_hour: Array<{ hour: number; trades: number; win_rate: number; pnl: number }>;
};

export type ProviderInfo = {
  configured: string;
  active: string;
  max_depth_levels: number;
  is_demo: boolean;
  status?: string;
  last_error?: string;
  effective?: string;
};
