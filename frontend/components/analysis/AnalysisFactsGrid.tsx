"use client";

import type { AnalysisReport } from "@/lib/types";
import { cx } from "@/lib/utils";

type Fact = {
  label: string;
  verdict: string;
  tone: "up" | "down" | "neutral" | "warn";
  hint?: string;
};

function toneClass(t: Fact["tone"]) {
  switch (t) {
    case "up":
      return "text-brand-dark dark:text-up";
    case "down":
      return "text-down";
    case "warn":
      return "text-yellow-700 dark:text-yellow-300";
    default:
      return "text-ink-soft";
  }
}

function dot(t: Fact["tone"]) {
  return cx(
    "inline-block w-1.5 h-1.5 rounded-full",
    t === "up" && "bg-brand",
    t === "down" && "bg-down",
    t === "warn" && "bg-yellow-500",
    t === "neutral" && "bg-neutral",
  );
}

export default function AnalysisFactsGrid({ report }: { report: AnalysisReport }) {
  const trendTone: Fact["tone"] =
    report.trend.direction === "up" ? "up" : report.trend.direction === "down" ? "down" : "neutral";
  const structureTone: Fact["tone"] =
    report.structure.bias === "up" ? "up" : report.structure.bias === "down" ? "down" : "neutral";
  const momentumTone: Fact["tone"] =
    report.momentum.verdict === "bullish"
      ? "up"
      : report.momentum.verdict === "bearish"
      ? "down"
      : report.momentum.verdict.startsWith("overextended")
      ? "warn"
      : "neutral";
  const volumeTone: Fact["tone"] =
    report.volume.trend === "expanding"
      ? "up"
      : report.volume.trend === "contracting"
      ? "warn"
      : "neutral";
  const vwapTone: Fact["tone"] = report.price >= report.trend.ema20 ? "up" : "down";
  const breakoutTone: Fact["tone"] = report.breakout.kind
    ? report.breakout.kind === "breakout_up" || report.breakout.kind === "retest"
      ? "up"
      : report.breakout.kind === "breakdown"
      ? "down"
      : "warn"
    : "neutral";
  const mtfTone: Fact["tone"] =
    report.multi_timeframe.overall === "aligned_up"
      ? "up"
      : report.multi_timeframe.overall === "aligned_down"
      ? "down"
      : report.multi_timeframe.overall === "mixed"
      ? "warn"
      : "neutral";

  const items: Fact[] = [
    { label: "Trend", verdict: report.trend.direction, tone: trendTone, hint: report.trend.reasons.join(", ") },
    { label: "Structure", verdict: report.structure.bias, tone: structureTone },
    { label: "Momentum", verdict: report.momentum.verdict, tone: momentumTone, hint: `RSI ${report.momentum.rsi14}` },
    { label: "Volume", verdict: report.volume.trend, tone: volumeTone, hint: `${report.volume.relative_volume}x RVol` },
    { label: "VWAP", verdict: report.price >= report.trend.ema20 ? "above" : "below", tone: vwapTone },
    { label: "Breakout", verdict: report.breakout.kind ?? "none", tone: breakoutTone },
    { label: "Multi-TF", verdict: report.multi_timeframe.overall.replace("_", " "), tone: mtfTone },
  ];

  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-ink-muted mb-2">Analysis facts</div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {items.map((f) => (
          <div key={f.label} className="p-2 rounded-md bg-gray-50 dark:bg-white/[0.03]" title={f.hint}>
            <div className="text-[10px] uppercase tracking-wider text-ink-muted">{f.label}</div>
            <div className={cx("mt-0.5 flex items-center gap-1.5 text-sm font-medium capitalize", toneClass(f.tone))}>
              <span className={dot(f.tone)} />
              {f.verdict}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
