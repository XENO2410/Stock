"use client";

import type { AnalysisReport } from "@/lib/types";
import { cx } from "@/lib/utils";

const OVERALL_LABEL: Record<AnalysisReport["multi_timeframe"]["overall"], string> = {
  aligned_up: "ALIGNED BULLISH",
  aligned_down: "ALIGNED BEARISH",
  mixed: "MIXED",
  undecided: "UNDECIDED",
};

export default function MultiTimeframeStrip({ report }: { report: AnalysisReport }) {
  const mtf = report.multi_timeframe;
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-ink-muted">Multi-timeframe</div>
        <div
          className={cx(
            "text-[11px] px-2 py-0.5 rounded",
            mtf.overall === "aligned_up" && "bg-brand/15 text-brand-dark dark:text-up",
            mtf.overall === "aligned_down" && "bg-down/15 text-down",
            mtf.overall === "mixed" && "bg-yellow-100 text-yellow-800 dark:bg-yellow-500/10 dark:text-yellow-300",
            mtf.overall === "undecided" && "bg-gray-100 text-ink-soft dark:bg-white/5",
          )}
        >
          {OVERALL_LABEL[mtf.overall]}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {mtf.per_timeframe.length === 0 && (
          <div className="text-xs text-ink-muted">No timeframe data available.</div>
        )}
        {mtf.per_timeframe.map((tf) => (
          <div
            key={tf.timeframe}
            className={cx(
              "rounded-md px-2.5 py-1 text-xs border",
              tf.direction === "up" && "bg-brand/5 border-brand/30 text-brand-dark dark:text-up",
              tf.direction === "down" && "bg-down/5 border-down/30 text-down",
              tf.direction === "sideways" && "bg-gray-50 dark:bg-white/5 border-border dark:border-border-dark text-ink-soft",
            )}
          >
            <span className="font-medium">{tf.timeframe}</span>
            <span className="mx-1 text-ink-muted">·</span>
            <span className="capitalize">{tf.direction}</span>
            <span className="text-ink-muted ml-1">({tf.strength})</span>
          </div>
        ))}
      </div>
    </div>
  );
}
