"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api, fetcher } from "@/lib/api";
import type { WatchlistRow } from "@/lib/types";
import { cx, fmtInrCurrency, fmtPct, signalColor, signalLabel } from "@/lib/utils";

export default function WatchlistPage() {
  const { data, mutate } = useSWR<WatchlistRow[]>("/api/watchlist", fetcher, {
    refreshInterval: 4000,
  });
  const { data: universe } = useSWR<{ symbol: string; name: string }[]>(
    "/api/market/universe",
    fetcher,
  );
  const [newSym, setNewSym] = useState("");

  async function add() {
    if (!newSym) return;
    try {
      await api.post("/api/watchlist", { symbol: newSym.toUpperCase() });
      setNewSym("");
      mutate();
    } catch (e: any) {
      alert(e.message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="font-semibold">Add stock</div>
        <div className="mt-2 flex gap-2 flex-wrap">
          <input
            list="universe"
            value={newSym}
            onChange={(e) => setNewSym(e.target.value.toUpperCase())}
            placeholder="Symbol (e.g. RATNAVEER)"
            className="border border-border dark:border-border-dark rounded-md px-3 py-1.5 text-sm bg-transparent"
          />
          <datalist id="universe">
            {universe?.map((u) => <option key={u.symbol} value={u.symbol}>{u.name}</option>)}
          </datalist>
          <button className="button button-primary" onClick={add}>Add</button>
        </div>
        <div className="mt-2 text-xs text-ink-muted">
          Demo universe: {universe?.map(u => u.symbol).join(", ")}
        </div>
      </div>

      <div className="card">
        <div className="p-3 border-b border-border dark:border-border-dark font-semibold">
          Watchlist ({data?.length ?? 0})
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-ink-muted text-xs">
              <tr className="[&>th]:py-2 [&>th]:px-3 text-left">
                <th>Symbol</th>
                <th className="text-right">Price</th>
                <th className="text-right">Change</th>
                <th className="text-right">Volume</th>
                <th className="text-right">RVol</th>
                <th>VWAP</th>
                <th>Trend</th>
                <th className="text-right">Signal</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data?.map((r) => (
                <tr
                  key={r.symbol}
                  className="hover:bg-gray-50 dark:hover:bg-white/[0.03] border-t border-border/60 dark:border-border-dark/60"
                >
                  <td className="py-2 px-3">
                    <Link href={`/stock/${r.symbol}`} className="font-medium">
                      {r.symbol}
                    </Link>
                    <div className="text-[11px] text-ink-muted">{r.name}</div>
                  </td>
                  <td className="py-2 px-3 text-right num">{fmtInrCurrency(r.price)}</td>
                  <td className={cx("py-2 px-3 text-right num", r.change >= 0 ? "text-up" : "text-down")}>
                    {fmtPct(r.change_pct)}
                  </td>
                  <td className="py-2 px-3 text-right num">{r.volume.toLocaleString("en-IN")}</td>
                  <td className="py-2 px-3 text-right num">{r.relative_volume.toFixed(2)}x</td>
                  <td className="py-2 px-3">
                    <span className={cx("pill", r.above_vwap ? "pill-up" : "pill-down")}>
                      {r.above_vwap ? "above" : "below"}
                    </span>
                  </td>
                  <td className="py-2 px-3">{r.trend}</td>
                  <td className="py-2 px-3 text-right">
                    <span className={cx("pill", signalColor(r.signal_action))}>
                      {signalLabel(r.signal_action)}
                    </span>
                    <div className="text-[11px] text-ink-muted num mt-0.5">
                      {r.signal_confidence}
                    </div>
                  </td>
                  <td className="py-2 px-3 text-right">
                    <button
                      className="text-xs text-ink-muted hover:text-down"
                      onClick={async () => {
                        await api.del(`/api/watchlist/${r.symbol}`);
                        mutate();
                      }}
                    >
                      remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
