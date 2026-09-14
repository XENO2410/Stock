"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { AnalyticsOverview } from "@/lib/types";
import { cx, fmtInrCurrency } from "@/lib/utils";

export default function AnalyticsPage() {
  const { data } = useSWR<AnalyticsOverview>("/api/analytics/overview", fetcher, {
    refreshInterval: 8000,
  });
  if (!data)
    return <div className="card p-6 animate-pulse h-64" />;

  const stat = [
    { label: "Total P&L", value: fmtInrCurrency(data.total_pnl), tone: data.total_pnl >= 0 ? "up" : "down" },
    { label: "Today", value: fmtInrCurrency(data.today_pnl), tone: data.today_pnl >= 0 ? "up" : "down" },
    { label: "This week", value: fmtInrCurrency(data.week_pnl), tone: data.week_pnl >= 0 ? "up" : "down" },
    { label: "This month", value: fmtInrCurrency(data.month_pnl), tone: data.month_pnl >= 0 ? "up" : "down" },
    { label: "Total trades", value: String(data.total_trades) },
    { label: "Win rate", value: `${data.win_rate.toFixed(1)}%` },
    { label: "Avg win", value: fmtInrCurrency(data.average_win), tone: "up" as const },
    { label: "Avg loss", value: fmtInrCurrency(data.average_loss), tone: "down" as const },
    { label: "Profit factor", value: data.profit_factor.toFixed(2) },
    { label: "Largest win", value: fmtInrCurrency(data.largest_win), tone: "up" as const },
    { label: "Largest loss", value: fmtInrCurrency(data.largest_loss), tone: "down" as const },
    { label: "Max drawdown", value: fmtInrCurrency(data.max_drawdown), tone: "down" as const },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {stat.map((s) => (
          <div key={s.label} className="card p-3">
            <div className="text-[11px] uppercase text-ink-muted">{s.label}</div>
            <div className={cx(
              "text-xl font-semibold num mt-0.5",
              s.tone === "up" && "text-up",
              s.tone === "down" && "text-down",
            )}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-3">
          <div className="font-semibold mb-2">Performance by strategy</div>
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-muted">
              <tr className="[&>th]:py-1.5 [&>th]:px-2 text-left">
                <th>Strategy</th>
                <th className="text-right">Trades</th>
                <th className="text-right">Win rate</th>
                <th className="text-right">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {data.by_strategy.map((s) => (
                <tr key={s.strategy} className="border-t border-border/60 dark:border-border-dark/60">
                  <td className="py-1.5 px-2">{s.strategy}</td>
                  <td className="py-1.5 px-2 text-right num">{s.trades}</td>
                  <td className="py-1.5 px-2 text-right num">{s.win_rate}%</td>
                  <td className={cx("py-1.5 px-2 text-right num", s.pnl >= 0 ? "text-up" : "text-down")}>
                    {fmtInrCurrency(s.pnl)}
                  </td>
                </tr>
              ))}
              {data.by_strategy.length === 0 && (
                <tr><td colSpan={4} className="p-3 text-center text-ink-muted">No data yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card p-3">
          <div className="font-semibold mb-2">Performance by hour</div>
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-muted">
              <tr className="[&>th]:py-1.5 [&>th]:px-2 text-left">
                <th>Hour (UTC)</th>
                <th className="text-right">Trades</th>
                <th className="text-right">Win rate</th>
                <th className="text-right">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {data.by_hour.map((h) => (
                <tr key={h.hour} className="border-t border-border/60 dark:border-border-dark/60">
                  <td className="py-1.5 px-2">{h.hour.toString().padStart(2, "0")}:00</td>
                  <td className="py-1.5 px-2 text-right num">{h.trades}</td>
                  <td className="py-1.5 px-2 text-right num">{h.win_rate}%</td>
                  <td className={cx("py-1.5 px-2 text-right num", h.pnl >= 0 ? "text-up" : "text-down")}>
                    {fmtInrCurrency(h.pnl)}
                  </td>
                </tr>
              ))}
              {data.by_hour.length === 0 && (
                <tr><td colSpan={4} className="p-3 text-center text-ink-muted">No data yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
