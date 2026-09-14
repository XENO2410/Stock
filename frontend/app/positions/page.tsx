"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api, fetcher } from "@/lib/api";
import type { PositionLive } from "@/lib/types";
import { cx, fmtInr, fmtInrCurrency, fmtPct } from "@/lib/utils";

export default function PositionsPage() {
  const [tab, setTab] = useState<"OPEN" | "CLOSED">("OPEN");
  const { data, mutate } = useSWR<PositionLive[]>(
    `/api/positions?status=${tab}`,
    fetcher,
    { refreshInterval: 2000 },
  );

  async function close(id: number) {
    if (!confirm("Close this paper position at current market price?")) return;
    await api.post(`/api/positions/${id}/exit`, { reason: "manual close" });
    mutate();
  }

  const rows = data ?? [];
  const totalUnrealized = rows.reduce((a, r) => a + r.unrealized_pnl, 0);

  return (
    <div className="space-y-4">
      <div className="card p-4 flex items-center justify-between">
        <div className="flex gap-2">
          {(["OPEN", "CLOSED"] as const).map((t) => (
            <button
              key={t}
              className={cx(
                "px-3 py-1.5 rounded-md text-sm",
                tab === t
                  ? "bg-brand text-white"
                  : "bg-gray-100 dark:bg-white/5 text-ink-soft",
              )}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="text-sm">
          <span className="text-ink-muted">Total unrealized</span>{" "}
          <span className={cx("num font-semibold", totalUnrealized >= 0 ? "text-up" : "text-down")}>
            {fmtInrCurrency(totalUnrealized)}
          </span>
        </div>
      </div>

      <div className="card overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-ink-muted">
            <tr className="[&>th]:py-2 [&>th]:px-3 text-left">
              <th>Symbol</th>
              <th>Dir</th>
              <th className="text-right">Qty</th>
              <th className="text-right">Entry</th>
              <th className="text-right">Current</th>
              <th className="text-right">SL</th>
              <th className="text-right">T1</th>
              <th className="text-right">P&amp;L</th>
              <th>Recommendation</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr
                key={p.id}
                className="border-t border-border/60 dark:border-border-dark/60"
              >
                <td className="py-2 px-3">
                  <Link href={`/stock/${p.symbol}`} className="font-medium">
                    {p.symbol}
                  </Link>
                </td>
                <td className="py-2 px-3">
                  <span
                    className={cx(
                      "pill",
                      p.direction === "LONG" ? "pill-up" : "pill-down",
                    )}
                  >
                    {p.direction}
                  </span>
                </td>
                <td className="py-2 px-3 text-right num">{p.quantity}</td>
                <td className="py-2 px-3 text-right num">{fmtInrCurrency(p.entry_price)}</td>
                <td className="py-2 px-3 text-right num">{fmtInrCurrency(p.current_price)}</td>
                <td className="py-2 px-3 text-right num text-down">{fmtInrCurrency(p.stop_loss)}</td>
                <td className="py-2 px-3 text-right num text-up">{fmtInrCurrency(p.target_1)}</td>
                <td
                  className={cx(
                    "py-2 px-3 text-right num font-medium",
                    p.unrealized_pnl >= 0 ? "text-up" : "text-down",
                  )}
                >
                  {fmtInrCurrency(p.unrealized_pnl)}
                  <div className="text-[10px] text-ink-muted">
                    {fmtPct(p.unrealized_pnl_pct)}
                  </div>
                </td>
                <td className="py-2 px-3">
                  <span
                    className={cx(
                      "pill",
                      p.recommendation === "EXIT"
                        ? "pill-down"
                        : p.recommendation === "BOOK_PARTIAL"
                        ? "pill-neutral"
                        : "pill-up",
                    )}
                  >
                    {p.recommendation}
                  </span>
                  <div className="text-[10px] text-ink-muted">{p.recommendation_reason}</div>
                </td>
                <td className="py-2 px-3 text-right">
                  {tab === "OPEN" && (
                    <button
                      onClick={() => close(p.id)}
                      className="text-xs text-down hover:underline"
                    >
                      exit
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={10} className="p-6 text-center text-ink-muted">
                  No {tab.toLowerCase()} positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
