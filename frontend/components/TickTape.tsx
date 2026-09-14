"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Tick } from "@/lib/types";
import { cx, fmtInr, fmtQty, fmtTime } from "@/lib/utils";

export default function TickTape({ symbol }: { symbol: string }) {
  const { data } = useSWR<Tick[]>(
    `/api/market/ticks/${symbol}?limit=20`,
    fetcher,
    { refreshInterval: 1500 },
  );
  const ticks = (data ?? []).slice().reverse();
  return (
    <div className="card">
      <div className="p-3 border-b border-border dark:border-border-dark font-semibold text-sm">
        Time &amp; sales
      </div>
      <div className="max-h-64 overflow-auto">
        <table className="w-full text-xs">
          <thead className="text-ink-muted">
            <tr className="[&>th]:py-1.5 [&>th]:px-3 text-left">
              <th>Time</th>
              <th className="text-right">Price</th>
              <th className="text-right">Qty</th>
              <th className="text-right">Side</th>
            </tr>
          </thead>
          <tbody>
            {ticks.map((t, i) => (
              <tr key={i} className="border-t border-border/60 dark:border-border-dark/60">
                <td className="py-1 px-3 num text-ink-muted">{fmtTime(t.timestamp)}</td>
                <td className="py-1 px-3 text-right num">{fmtInr(t.price)}</td>
                <td className="py-1 px-3 text-right num">{fmtQty(t.quantity)}</td>
                <td className={cx(
                  "py-1 px-3 text-right font-medium",
                  t.side === "BUY" ? "text-up" : "text-down",
                )}>
                  {t.side}
                </td>
              </tr>
            ))}
            {ticks.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center text-ink-muted">
                  No trades yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
