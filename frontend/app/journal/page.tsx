"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { JournalOut } from "@/lib/types";
import { cx, fmtDateTime, fmtInrCurrency, fmtPct } from "@/lib/utils";

export default function JournalPage() {
  const { data } = useSWR<JournalOut[]>("/api/journal", fetcher, {
    refreshInterval: 5000,
  });
  const rows = data ?? [];
  return (
    <div className="card overflow-auto">
      <div className="p-3 border-b border-border dark:border-border-dark font-semibold">
        Trade journal
      </div>
      <table className="w-full text-sm">
        <thead className="text-xs text-ink-muted">
          <tr className="[&>th]:py-2 [&>th]:px-3 text-left">
            <th>Symbol</th>
            <th>Dir</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>Qty</th>
            <th className="text-right">P&amp;L</th>
            <th>Strategy</th>
            <th>Confidence</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((j) => (
            <tr key={j.id} className="border-t border-border/60 dark:border-border-dark/60">
              <td className="py-2 px-3 font-medium">{j.symbol}</td>
              <td className="py-2 px-3">
                <span className={cx("pill", j.direction === "LONG" ? "pill-up" : "pill-down")}>
                  {j.direction}
                </span>
              </td>
              <td className="py-2 px-3 text-xs">
                <div className="num">{fmtInrCurrency(j.entry_price)}</div>
                <div className="text-ink-muted">{fmtDateTime(j.entry_time)}</div>
              </td>
              <td className="py-2 px-3 text-xs">
                <div className="num">{j.exit_price ? fmtInrCurrency(j.exit_price) : "-"}</div>
                <div className="text-ink-muted">{j.exit_time ? fmtDateTime(j.exit_time) : ""}</div>
              </td>
              <td className="py-2 px-3 num">{j.quantity}</td>
              <td
                className={cx(
                  "py-2 px-3 text-right num font-medium",
                  j.pnl >= 0 ? "text-up" : "text-down",
                )}
              >
                {fmtInrCurrency(j.pnl)}
                <div className="text-[10px] text-ink-muted">{fmtPct(j.pnl_pct)}</div>
              </td>
              <td className="py-2 px-3 text-ink-soft">{j.strategy || "-"}</td>
              <td className="py-2 px-3 num">{j.signal_confidence || "-"}</td>
              <td className="py-2 px-3 text-xs text-ink-soft max-w-xs">{j.exit_reason || j.entry_reason}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={9} className="p-6 text-center text-ink-muted">
                No journal entries yet — close a paper trade to log one automatically.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
