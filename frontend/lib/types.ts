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

// ================ Analysis workspace (Phase 2) ================

export type DataSource = "DEMO" | "SIMULATED" | "HISTORICAL" | "CSV" | "LIVE";

export type AnalysisInstrument = {
  symbol: string;
  exchange: string;
  trading_symbol: string;
  display_name: string;
  segment: string;
  instrument_token?: string | null;
  isin?: string | null;
  currency: string;
};

export type TradePlan = {
  entry_low: number;
  entry_high: number;
  stop: number;
  target_1: number;
  target_2: number;
  risk_reward: number;
};

export type StructureEvent = {
  timestamp: string;
  type: "HH" | "HL" | "LH" | "LL" | "BOS_UP" | "BOS_DOWN" | "CHOCH_UP" | "CHOCH_DOWN";
  price: number;
  confidence: number;
  reason: string;
};

export type Zone = {
  price_low: number;
  price_high: number;
  strength: number;
  reasons: string[];
};

export type TFEntry = {
  timeframe: string;
  direction: "up" | "down" | "sideways";
  strength: number;
};

export type AnalysisReport = {
  symbol: string;
  timeframe: string;
  source: DataSource;
  price: number;
  signal: "BUY" | "SELL" | "WAIT";
  score: number;
  bias: "up" | "down" | "neutral";
  positive_evidence: string[];
  negative_evidence: string[];
  warnings: string[];
  group_scores: Record<string, number>;
  trade_plan: TradePlan | null;
  summary: string;

  trend: {
    direction: "up" | "down" | "sideways";
    strength: number;
    ema9: number;
    ema20: number;
    ema50: number;
    slope_pct: number;
    reasons: string[];
  };
  momentum: {
    rsi14: number;
    macd: number;
    macd_signal: number;
    macd_hist: number;
    roc10: number;
    verdict: "bullish" | "bearish" | "neutral" | "overextended_up" | "overextended_down";
    divergence: "bullish" | "bearish" | null;
    reasons: string[];
  };
  volume: {
    relative_volume: number;
    is_spike: boolean;
    trend: "expanding" | "contracting" | "steady";
    confirms_move: boolean;
    reasons: string[];
  };
  structure: {
    bias: "up" | "down" | "undecided";
    last_swing_high: number | null;
    last_swing_low: number | null;
    events: StructureEvent[];
  };
  breakout: {
    kind?: "breakout_up" | "breakdown" | "retest" | "failed_breakout";
    zone_mid?: number;
    strength?: number;
    reasons?: string[];
  };
  reversal: {
    direction: "up" | "down" | null;
    strength: number;
    reasons: string[];
  };
  multi_timeframe: {
    overall: "aligned_up" | "aligned_down" | "mixed" | "undecided";
    alignment_score: number;
    per_timeframe: TFEntry[];
  };
  support: Zone[];
  resistance: Zone[];
  candle_patterns: { name: string; bias: string; strength: number }[];
};

export type AnalysisWeights = {
  groups: Record<string, number>;
  bands: Record<string, [number, number]>;
};

// ================ Replay + Backtest (Phase 3) ================

export type ReplaySessionState = {
  id: string;
  symbol: string;
  primary_timeframe: string;
  cursor: number;
  total_candles: number;
  current_timestamp: string | null;
  current_close: number | null;
  status: "paused" | "playing" | "finished";
  speed: number;
  available_timeframes: string[];
  source: "CSV" | "SIMULATED";
  train_frac: number;
  in_sample_end_index: number;
  in_sample: boolean;
};

export type CsvFile = {
  file: string;
  symbol: string;
  timeframe: string;
  size_bytes: number;
  modified: string;
};

export type BacktestMetrics = {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_profit: number;
  gross_loss: number;
  net_pnl: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  expectancy: number;
  max_drawdown: number;
  max_consecutive_losses: number;
  max_consecutive_wins: number;
  average_trade: number;
  average_r: number;
  median_r: number;
  r_distribution: Record<string, number>;
  buy_signals: number;
  sell_signals: number;
  wait_signals: number;
  total_fees: number;
  total_slippage: number;
};

export type BacktestTradeRow = {
  symbol: string;
  timeframe: string;
  direction: "LONG" | "SHORT";
  entry_index: number;
  entry_time: string;
  entry_price: number;
  stop: number;
  target: number;
  quantity: number;
  signal_score: number;
  signal_reasons: string[];
  exit_index: number | null;
  exit_time: string | null;
  exit_price: number | null;
  reason: string | null;
  resolution: string;
  fees: number;
  slippage: number;
  pnl: number;
  r_multiple: number;
  in_sample: boolean;
};

export type BacktestResult = {
  symbol: string;
  timeframe: string;
  total_candles: number;
  warmup_bars: number;
  train_frac: number;
  train_end_index: number;
  config: Record<string, unknown>;
  overall: BacktestMetrics;
  in_sample: BacktestMetrics;
  out_of_sample: BacktestMetrics;
  trades: BacktestTradeRow[];
  signals_timeline: Array<{
    index: number;
    timestamp: string;
    signal: "BUY" | "SELL" | "WAIT";
    score: number;
    bias: "up" | "down" | "neutral";
    in_sample: boolean;
  }>;
  assumptions: Record<string, unknown>;
};
