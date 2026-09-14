"use client";

import { useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { AnalysisReport, AnalysisWeights } from "@/lib/types";
import { cx, fmtInrCurrency, fmtPct } from "@/lib/utils";

import StockSearch from "@/components/analysis/StockSearch";
import DataSourceBadge from "@/components/analysis/DataSourceBadge";
import AnalysisChart, { Overlays } from "@/components/analysis/AnalysisChart";
import OverlayToggles from "@/components/analysis/OverlayToggles";
import SignalCard from "@/components/analysis/SignalCard";
import ConfluenceBars from "@/components/analysis/ConfluenceBars";
import WhyPanel from "@/components/analysis/WhyPanel";
import TradePlanCard from "@/components/analysis/TradePlanCard";
import MultiTimeframeStrip from "@/components/analysis/MultiTimeframeStrip";
import AnalysisFactsGrid from "@/components/analysis/AnalysisFactsGrid";
import ZonesList from "@/components/analysis/ZonesList";

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"];

const DEFAULT_OVERLAYS: Overlays = {
  ema9: true,
  ema20: true,
  ema50: false,
  vwap: true,
  sma20: false,
  support: true,
  resistance: true,
  structure: true,
  bos_choch: true,
  trade_plan: true,
};

export default function AnalysisWorkspacePage({ params }: { params: { symbol: string } }) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const searchParams = useSearchParams();
  const router = useRouter();

  const source = (searchParams.get("source") ?? "mock").toLowerCase();
  const [timeframe, setTimeframe] = useState<string>(searchParams.get("timeframe") ?? "5m");
  const [overlays, setOverlays] = useState<Overlays>(DEFAULT_OVERLAYS);

  const analysisUrl = useMemo(
    () =>
      `/api/analysis/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(
        timeframe,
      )}&source=${encodeURIComponent(source)}`,
    [symbol, timeframe, source],
  );

  const { data: report, error, isLoading } = useSWR<AnalysisReport>(analysisUrl, fetcher, {
    refreshInterval: 8000,
    keepPreviousData: true,
  });
  const { data: weights } = useSWR<AnalysisWeights>("/api/analysis/weights", fetcher);

  const change = report ? report.price - report.trend.ema20 : 0;
  const changePct = report && report.trend.ema20 ? (change / report.trend.ema20) * 100 : 0;

  const setSource = (s: string) => {
    const p = new URLSearchParams(searchParams.toString());
    p.set("source", s);
    router.push(`/analysis/${encodeURIComponent(symbol)}?${p.toString()}`);
  };

  return (
    <div className="space-y-4">
      {/* --- Top bar --- */}
      <div className="card p-3 flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[260px] max-w-md">
          <StockSearch source={source} />
        </div>
        <div className="flex items-baseline gap-3">
          <div className="text-lg font-semibold tracking-tight">{symbol}</div>
          <div className="text-[11px] text-ink-muted">NSE · CASH</div>
        </div>
        {report && (
          <div className="flex items-baseline gap-3">
            <div className="num text-xl font-semibold">{fmtInrCurrency(report.price)}</div>
            <div className={cx("num text-sm", change >= 0 ? "text-up" : "text-down")}>
              {change >= 0 ? "+" : ""}
              {change.toFixed(2)} ({fmtPct(changePct)})
            </div>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex gap-1 text-[11px]">
            {(["mock", "csv"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSource(s)}
                className={
                  "px-2 py-0.5 rounded " +
                  (source === s ? "bg-brand text-white" : "bg-gray-100 dark:bg-white/5 text-ink-soft")
                }
              >
                {s.toUpperCase()}
              </button>
            ))}
          </div>
          {report && (
            <DataSourceBadge
              source={report.source}
              hint={
                report.source === "CSV"
                  ? `backend/data/csv/${symbol}_${timeframe}.csv`
                  : report.source === "SIMULATED" || report.source === "DEMO"
                  ? "deterministic simulator"
                  : undefined
              }
            />
          )}
        </div>
      </div>

      {/* --- Timeframe bar --- */}
      <div className="card p-2 flex flex-wrap items-center gap-1">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={cx(
              "px-2 py-1 rounded-md text-xs font-medium",
              tf === timeframe
                ? "bg-brand text-white"
                : "bg-gray-100 dark:bg-white/5 text-ink-soft hover:bg-gray-200 dark:hover:bg-white/10",
            )}
          >
            {tf}
          </button>
        ))}
        <div className="mx-3 h-4 w-px bg-border dark:bg-border-dark" />
        <OverlayToggles overlays={overlays} onChange={setOverlays} />
      </div>

      {/* --- Body: chart + right panel --- */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <div className="space-y-4 min-w-0">
          <div className="card p-0 overflow-hidden">
            {error && (
              <div className="p-4 text-sm text-down">
                Failed to load analysis: {(error as Error).message}
              </div>
            )}
            {!error && (
              <AnalysisChart
                symbol={symbol}
                timeframe={timeframe}
                overlays={overlays}
                report={report}
              />
            )}
          </div>

          {report && <AnalysisFactsGrid report={report} />}
          {report && <ZonesList report={report} />}
        </div>

        <div className="space-y-4">
          {isLoading && !report ? (
            <div className="card p-4 animate-pulse h-40" />
          ) : report ? (
            <>
              <SignalCard report={report} />
              <MultiTimeframeStrip report={report} />
              <ConfluenceBars report={report} weights={weights} />
              <WhyPanel report={report} />
              <TradePlanCard report={report} />
            </>
          ) : (
            <div className="card p-4 text-sm text-ink-muted">No analysis data.</div>
          )}
        </div>
      </div>
    </div>
  );
}
