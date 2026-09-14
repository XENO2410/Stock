"use client";

import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { WatchlistRow } from "@/lib/types";
import { cx, fmtInrCurrency, fmtPct, signalColor, signalLabel } from "@/lib/utils";
import { useMemo, useState } from "react";

const SORTS = [
  { key: "confidence_desc", label: "Highest Confidence" },
  { key: "gain_desc", label: "Biggest Gainers" },
  { key: "gain_asc", label: "Biggest Losers" },
  { key: "rvol_desc", label: "Highest Rel. Volume" },
  { key: "buys", label: "Strongest Buys" },
  { key: "sells", label: "Strongest Sells" },
  { key: "favourites", label: "Favourites" },
];

export default function Watchlist() {
  const { data, mutate } = useSWR<WatchlistRow[]>("/api/watchlist", fetcher, {
    refreshInterval: 4000,
  });
  const [sort, setSort] = useState("confidence_desc");

  const rows = useMemo(() => {
    if (!data) return [];
    let r = [...data];
    switch (sort) {
      case "confidence_desc":
        r.sort((a, b) => b.signal_confidence - a.signal_confidence);
        break;
      case "gain_desc":
        r.sort((a, b) => b.change_pct - a.change_pct);
        break;
      case "gain_asc":
        r.sort((a, b) => a.change_pct - b.change_pct);
        break;
      case "rvol_desc":
        r.sort((a, b) => b.relative_volume - a.relative_volume);
        break;
      case "buys":
        r = r
          .filter((x) => x.signal_action.includes("BUY"))
          .sort((a, b) => b.signal_confidence - a.signal_confidence);
        break;
      case "sells":
        r = r
          .filter((x) => x.signal_action.includes("SELL"))
          .sort((a, b) => b.signal_confidence - a.signal_confidence);
        break;
      case "favourites":
        r = r.filter((x) => x.is_favourite);
        break;
    }
    return r;
  }, [data, sort]);

  return (
    <div className="card">
      <div className="p-3 flex items-center justify-between border-b border-border dark:border-border-dark">
        <div className="font-semibold">Watchlist</div>
        <select
          className="text-sm bg-transparent border border-border dark:border-border-dark rounded-md px-2 py-1"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
      </div>
      <div className="max-h-[540px] overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-ink-muted text-xs">
            <tr className="[&>th]:py-2 [&>th]:px-3 text-left">
              <th>Symbol</th>
              <th className="text-right">Price</th>
              <th className="text-right">Change</th>
              <th className="text-right">RVol</th>
              <th className="text-right">VWAP</th>
              <th className="text-right">Signal</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.symbol}
                className="hover:bg-gray-50 dark:hover:bg-white/[0.03] border-t border-border/60 dark:border-border-dark/60"
              >
                <td className="py-2 px-3">
                  <Link href={`/stock/${r.symbol}`} className="font-medium">
                    {r.symbol}
                  </Link>
                  <div className="text-[11px] text-ink-muted truncate max-w-[180px]">{r.name}</div>
                </td>
                <td className="py-2 px-3 text-right num">{fmtInrCurrency(r.price)}</td>
                <td
                  className={cx(
                    "py-2 px-3 text-right num",
                    r.change >= 0 ? "text-up" : "text-down",
                  )}
                >
                  {fmtPct(r.change_pct)}
                </td>
                <td className="py-2 px-3 text-right num">{r.relative_volume.toFixed(2)}x</td>
                <td className="py-2 px-3 text-right num">
                  <span
                    className={cx(
                      "pill",
                      r.above_vwap ? "pill-up" : "pill-down",
                    )}
                  >
                    {r.above_vwap ? "above" : "below"}
                  </span>
                </td>
                <td className="py-2 px-3 text-right">
                  <span className={cx("pill", signalColor(r.signal_action))}>
                    {signalLabel(r.signal_action)}
                  </span>
                  <div className="text-[11px] text-ink-muted num mt-0.5">
                    {r.signal_confidence}
                  </div>
                </td>
                <td className="py-2 px-2 text-right">
                  <button
                    className="text-xs text-ink-muted hover:text-down"
                    onClick={async () => {
                      await fetch(
                        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/watchlist/${r.symbol}`,
                        { method: "DELETE" },
                      );
                      mutate();
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-ink-muted">
                  No stocks match. Add some from the Watchlist page.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
