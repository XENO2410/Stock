"use client";

import StockSearch from "@/components/analysis/StockSearch";
import DataSourceBadge from "@/components/analysis/DataSourceBadge";
import { useState } from "react";

export default function AnalysisIndexPage() {
  const [source, setSource] = useState<"mock" | "csv">("mock");
  return (
    <div className="max-w-3xl mx-auto py-10 space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Analysis workspace</h1>
        <p className="text-sm text-ink-soft">
          Search a stock to open its full analysis workspace: chart, market structure, support/resistance
          zones, confluence score and a decision. All computed from the deterministic engine — the data
          source is always labelled and never hidden.
        </p>
      </div>

      <div className="card p-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className="text-xs uppercase tracking-wider text-ink-muted">Research mode</div>
          <div className="flex gap-1">
            {(["mock", "csv"] as const).map((tag) => (
              <button
                key={tag}
                onClick={() => setSource(tag)}
                className={
                  "px-2 py-0.5 rounded text-xs " +
                  (source === tag
                    ? "bg-brand text-white"
                    : "bg-gray-100 dark:bg-white/5 text-ink-soft")
                }
              >
                {tag.toUpperCase()}
              </button>
            ))}
          </div>
          <DataSourceBadge
            source={source === "csv" ? "CSV" : "SIMULATED"}
            hint={source === "csv" ? "backend/data/csv/*" : "deterministic simulator"}
          />
        </div>

        <StockSearch source={source} placeholder="Search RELIANCE, TCS, INFY…" autoFocus />

        <div className="text-xs text-ink-muted">
          Live market data is only enabled when a legitimate live feed is connected. Simulated and CSV
          sources are for research only — no data is presented as LIVE unless it truly is.
        </div>
      </div>
    </div>
  );
}
