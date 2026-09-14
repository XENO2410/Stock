"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { MarketOverview } from "@/lib/types";
import { cx, fmtPct } from "@/lib/utils";

export default function MarketOverviewCard() {
  const { data } = useSWR<MarketOverview>("/api/market/overview", fetcher, {
    refreshInterval: 4000,
  });
  if (!data) return <div className="card p-4 animate-pulse h-40" />;
  const total = data.advances + data.declines + data.unchanged || 1;
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="font-semibold">Market overview</div>
        <div className="text-xs text-ink-muted">Breadth</div>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-md bg-brand/10 py-2">
          <div className="text-lg font-semibold text-brand-dark dark:text-up num">{data.advances}</div>
          <div className="text-[11px] text-ink-muted">Advances</div>
        </div>
        <div className="rounded-md bg-down/10 py-2">
          <div className="text-lg font-semibold text-down num">{data.declines}</div>
          <div className="text-[11px] text-ink-muted">Declines</div>
        </div>
        <div className="rounded-md bg-gray-100 dark:bg-white/5 py-2">
          <div className="text-lg font-semibold num">{data.unchanged}</div>
          <div className="text-[11px] text-ink-muted">Unchanged</div>
        </div>
      </div>
      <div className="mt-4">
        <div className="text-xs uppercase text-ink-muted mb-1">Top gainers</div>
        <ul className="text-sm">
          {data.top_gainers.slice(0, 3).map((q) => (
            <li key={q.symbol} className="flex justify-between py-0.5">
              <span>{q.symbol}</span>
              <span className={cx(q.change >= 0 ? "text-up" : "text-down", "num")}>
                {fmtPct(q.change_pct)}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-3">
        <div className="text-xs uppercase text-ink-muted mb-1">Top losers</div>
        <ul className="text-sm">
          {data.top_losers.slice(0, 3).map((q) => (
            <li key={q.symbol} className="flex justify-between py-0.5">
              <span>{q.symbol}</span>
              <span className={cx(q.change >= 0 ? "text-up" : "text-down", "num")}>
                {fmtPct(q.change_pct)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
