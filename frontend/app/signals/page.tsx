"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { SignalOut } from "@/lib/types";
import { cx, fmtInr, signalColor, signalLabel } from "@/lib/utils";

export default function SignalsPage() {
  const { data } = useSWR<SignalOut[]>("/api/signals?limit=30", fetcher, {
    refreshInterval: 5000,
  });
  const list = data ?? [];
  return (
    <div className="card">
      <div className="p-3 border-b border-border dark:border-border-dark flex items-center justify-between">
        <div className="font-semibold">Top signals</div>
        <div className="text-xs text-ink-muted">Ranked by confidence</div>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-ink-muted">
            <tr className="[&>th]:py-2 [&>th]:px-3 text-left">
              <th>Symbol</th>
              <th>Action</th>
              <th className="text-right">Confidence</th>
              <th className="text-right">Entry</th>
              <th className="text-right">SL</th>
              <th className="text-right">T1</th>
              <th className="text-right">R:R</th>
              <th>Strategy</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => (
              <tr
                key={s.symbol + s.id}
                className="border-t border-border/60 dark:border-border-dark/60"
              >
                <td className="py-2 px-3">
                  <Link href={`/stock/${s.symbol}`} className="font-medium">
                    {s.symbol}
                  </Link>
                </td>
                <td className="py-2 px-3">
                  <span className={cx("pill", signalColor(s.action))}>
                    {signalLabel(s.action)}
                  </span>
                </td>
                <td className="py-2 px-3 text-right num">{s.confidence}</td>
                <td className="py-2 px-3 text-right num">
                  {fmtInr(s.entry_low)}–{fmtInr(s.entry_high)}
                </td>
                <td className="py-2 px-3 text-right num text-down">{fmtInr(s.stop_loss)}</td>
                <td className="py-2 px-3 text-right num text-up">{fmtInr(s.target_1)}</td>
                <td className="py-2 px-3 text-right num">1 : {s.risk_reward.toFixed(2)}</td>
                <td className="py-2 px-3 text-ink-soft">{s.strategy}</td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr>
                <td colSpan={8} className="p-6 text-center text-ink-muted">
                  No signals yet — the engine needs enough candle history.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
