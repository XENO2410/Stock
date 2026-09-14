"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import { cx, fmtInrCurrency } from "@/lib/utils";

const STRATEGIES = ["trend_vwap", "breakout", "pullback", "orb"] as const;
const TIMEFRAMES = ["1m", "3m", "5m", "10m", "15m", "30m", "1h"];

export default function BacktestPage() {
  const { data: universe } = useSWR<{ symbol: string; name: string }[]>(
    "/api/market/universe",
    fetcher,
  );
  const [symbol, setSymbol] = useState("RATNAVEER");
  const [timeframe, setTimeframe] = useState("5m");
  const [strategy, setStrategy] = useState<(typeof STRATEGIES)[number]>("trend_vwap");
  const [capital, setCapital] = useState(50000);
  const [risk, setRisk] = useState(250);
  const [result, setResult] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const res = await api.post("/api/backtest", {
        symbol,
        timeframe,
        strategy,
        capital,
        risk_per_trade: risk,
        days: 1,
      });
      setResult(res);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="font-semibold">Backtest</div>
        <div className="mt-3 grid grid-cols-2 md:grid-cols-6 gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-ink-muted">Symbol</span>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 bg-transparent"
            >
              {universe?.map((u) => <option key={u.symbol}>{u.symbol}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-ink-muted">Timeframe</span>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 bg-transparent"
            >
              {TIMEFRAMES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-ink-muted">Strategy</span>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as any)}
              className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 bg-transparent"
            >
              {STRATEGIES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-ink-muted">Capital</span>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 bg-transparent num"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-ink-muted">Risk/trade</span>
            <input
              type="number"
              value={risk}
              onChange={(e) => setRisk(Number(e.target.value))}
              className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 bg-transparent num"
            />
          </label>
          <button className="button button-primary self-end" onClick={run} disabled={busy}>
            {busy ? "Running…" : "Run"}
          </button>
        </div>
        {err && <div className="mt-2 text-xs text-down">{err}</div>}
        <div className="mt-2 text-xs text-ink-muted">
          Note: demo mode uses the mock market's in-memory candle history. Extend the backtester
          to load a persisted historical dataset for multi-day backtests.
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Trades", value: result.total_trades },
            { label: "Win rate", value: `${result.win_rate.toFixed(1)}%` },
            { label: "Net P&L", value: fmtInrCurrency(result.net_pnl), tone: result.net_pnl >= 0 ? "up" : "down" },
            { label: "Max drawdown", value: fmtInrCurrency(result.max_drawdown), tone: "down" },
            { label: "Profit factor", value: result.profit_factor.toFixed(2) },
            { label: "Wins", value: result.winning_trades, tone: "up" },
            { label: "Losses", value: result.losing_trades, tone: "down" },
            { label: "Strategy", value: result.strategy },
          ].map((s: any) => (
            <div key={s.label} className="card p-3">
              <div className="text-[11px] uppercase text-ink-muted">{s.label}</div>
              <div className={cx(
                "text-lg font-semibold num mt-0.5",
                s.tone === "up" && "text-up",
                s.tone === "down" && "text-down",
              )}>{s.value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
