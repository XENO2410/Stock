"use client";

import type { AnalysisReport } from "@/lib/types";
import { cx } from "@/lib/utils";

const SIGNAL_STYLE: Record<AnalysisReport["signal"], { label: string; wrap: string; text: string }> = {
  BUY: {
    label: "BUY",
    wrap: "bg-brand/10 border border-brand/40",
    text: "text-brand-dark dark:text-up",
  },
  SELL: {
    label: "SELL",
    wrap: "bg-down/10 border border-down/40",
    text: "text-down",
  },
  WAIT: {
    label: "WAIT",
    wrap: "bg-gray-100 dark:bg-white/[0.04] border border-border dark:border-border-dark",
    text: "text-ink-soft dark:text-ink-inverse",
  },
};

const BIAS_LABEL: Record<AnalysisReport["bias"], string> = {
  up: "Bullish",
  down: "Bearish",
  neutral: "Neutral",
};

export default function SignalCard({ report }: { report: AnalysisReport }) {
  const s = SIGNAL_STYLE[report.signal] ?? SIGNAL_STYLE.WAIT;
  const band =
    report.score >= 85 ? "Strong" : report.score >= 65 ? "Valid" : report.score >= 45 ? "Watch" : "No trade";
  return (
    <div className={cx("rounded-xl p-4", s.wrap)}>
      <div className="flex items-baseline justify-between">
        <div className={cx("text-3xl font-semibold tracking-tight", s.text)}>{s.label}</div>
        <div className="text-right">
          <div className="text-2xl font-semibold num">{report.score}</div>
          <div className="text-[10px] uppercase tracking-wider text-ink-muted">/ 100 · {band}</div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-ink-soft">
        <span>
          Bias{" "}
          <span
            className={cx(
              "font-medium",
              report.bias === "up" && "text-up",
              report.bias === "down" && "text-down",
            )}
          >
            {BIAS_LABEL[report.bias]}
          </span>
        </span>
        <span className="text-ink-muted">·</span>
        <span>Timeframe {report.timeframe}</span>
        <span className="text-ink-muted">·</span>
        <span className="num">₹{report.price.toFixed(2)}</span>
      </div>
    </div>
  );
}
