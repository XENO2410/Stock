"use client";

import type { AnalysisReport, AnalysisWeights } from "@/lib/types";
import { cx } from "@/lib/utils";

const GROUP_LABELS: Record<string, string> = {
  trend_and_momentum: "Trend & Momentum",
  structure: "Market Structure",
  price_action: "Price Action",
  support_resistance: "Support / Resistance",
  volume: "Volume",
  multi_timeframe: "Multi-Timeframe",
  breakout: "Breakout",
};

export default function ConfluenceBars({
  report,
  weights,
}: {
  report: AnalysisReport;
  weights?: AnalysisWeights;
}) {
  const groups = report.group_scores ?? {};
  const max = weights?.groups ?? {};
  const entries = Object.entries(groups).sort((a, b) => (max[b[0]] ?? 0) - (max[a[0]] ?? 0));
  const total = Object.values(groups).reduce((s, v) => s + v, 0);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-ink-muted">Confluence</div>
        <div className="text-sm num">
          Total <span className="font-semibold">{total}</span>
          <span className="text-ink-muted"> / {Object.values(max).reduce((a, b) => a + b, 0) || 100}</span>
        </div>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        {entries.map(([key, val]) => {
          const cap = max[key] ?? 20;
          const pct = cap > 0 ? Math.max(0, Math.min(100, (val / cap) * 100)) : 0;
          return (
            <div key={key} className="grid grid-cols-[10rem_1fr_2.5rem] items-center gap-3">
              <div className="text-ink-soft text-xs truncate">{GROUP_LABELS[key] ?? key}</div>
              <div className="h-1.5 rounded bg-gray-100 dark:bg-white/5 overflow-hidden">
                <div
                  className={cx(
                    "h-full rounded",
                    val > 0 ? "bg-brand" : "bg-gray-300 dark:bg-white/10",
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="text-right num text-xs">
                {val}
                <span className="text-ink-muted">/{cap}</span>
              </div>
            </div>
          );
        })}
        {entries.length === 0 && <div className="text-xs text-ink-muted">No group scores yet.</div>}
      </div>
    </div>
  );
}
