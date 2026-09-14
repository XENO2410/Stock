"use client";

import useSWR from "swr";
import { useState } from "react";
import { fetcher } from "@/lib/api";
import type { DepthSnapshot, ProviderInfo } from "@/lib/types";
import { cx, fmtInr, fmtQty } from "@/lib/utils";

const LEVEL_OPTIONS = [5, 10, 20, 25, 50];

export default function MarketDepth({ symbol }: { symbol: string }) {
  const [levels, setLevels] = useState(10);
  const { data: prov } = useSWR<ProviderInfo>("/api/market/provider", fetcher);
  const maxAvail = prov?.max_depth_levels ?? 10;
  const cappedLevels = Math.min(levels, maxAvail);
  const { data } = useSWR<DepthSnapshot>(
    `/api/market/depth/${symbol}?levels=${cappedLevels}`,
    fetcher,
    { refreshInterval: 1500 },
  );

  if (!data) return <div className="card p-4 animate-pulse h-64" />;

  const maxQty = Math.max(
    ...data.bids.map((b) => b.quantity),
    ...data.asks.map((a) => a.quantity),
    1,
  );
  const bidTotal = data.bid_total;
  const askTotal = data.ask_total;
  const total = bidTotal + askTotal || 1;
  const bidPct = (bidTotal / total) * 100;
  const askPct = (askTotal / total) * 100;

  return (
    <div className="card">
      <div className="p-3 border-b border-border dark:border-border-dark flex items-center justify-between gap-3">
        <div className="font-semibold">Market depth</div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-ink-muted">Levels:</span>
          {LEVEL_OPTIONS.map((l) => (
            <button
              key={l}
              disabled={l > maxAvail}
              className={cx(
                "px-2 py-0.5 rounded",
                l === levels
                  ? "bg-brand text-white"
                  : "bg-gray-100 dark:bg-white/5 text-ink-soft",
                l > maxAvail && "opacity-40 cursor-not-allowed",
              )}
              title={l > maxAvail ? `Provider supports up to ${maxAvail}` : ""}
              onClick={() => setLevels(l)}
            >
              {l}
            </button>
          ))}
          <button
            className={cx(
              "px-2 py-0.5 rounded",
              levels === maxAvail
                ? "bg-brand text-white"
                : "bg-gray-100 dark:bg-white/5 text-ink-soft",
            )}
            onClick={() => setLevels(maxAvail)}
          >
            MAX
          </button>
        </div>
      </div>

      <div className="p-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <div className="text-brand-dark dark:text-up">
            Buy {bidPct.toFixed(1)}%
          </div>
          <div className="text-down">Sell {askPct.toFixed(1)}%</div>
        </div>
        <div className="h-1.5 rounded bg-gray-100 dark:bg-white/5 overflow-hidden flex">
          <div className="h-full bg-brand/70" style={{ width: `${bidPct}%` }} />
          <div className="h-full bg-down/70" style={{ width: `${askPct}%` }} />
        </div>

        <div className="grid grid-cols-2 gap-4 mt-3 text-xs">
          {/* BIDS */}
          <div>
            <div className="text-ink-muted mb-1 flex justify-between">
              <span>Bid qty</span>
              <span>Bid price</span>
            </div>
            <ul className="space-y-0.5">
              {data.bids.map((b, i) => (
                <li
                  key={i}
                  className="relative flex justify-between px-1 py-0.5 rounded"
                >
                  <div
                    className="absolute inset-y-0 right-0 bg-brand/10"
                    style={{ width: `${(b.quantity / maxQty) * 100}%` }}
                  />
                  <span className="relative num">{fmtQty(b.quantity)}</span>
                  <span className="relative text-brand-dark dark:text-up num">
                    {fmtInr(b.price)}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex justify-between mt-1 pt-1 border-t border-border/60 dark:border-border-dark/60 num">
              <span className="text-ink-muted">Total</span>
              <span>{fmtQty(bidTotal)}</span>
            </div>
          </div>

          {/* ASKS */}
          <div>
            <div className="text-ink-muted mb-1 flex justify-between">
              <span>Ask price</span>
              <span>Ask qty</span>
            </div>
            <ul className="space-y-0.5">
              {data.asks.map((a, i) => (
                <li
                  key={i}
                  className="relative flex justify-between px-1 py-0.5 rounded"
                >
                  <div
                    className="absolute inset-y-0 left-0 bg-down/10"
                    style={{ width: `${(a.quantity / maxQty) * 100}%` }}
                  />
                  <span className="relative text-down num">{fmtInr(a.price)}</span>
                  <span className="relative num">{fmtQty(a.quantity)}</span>
                </li>
              ))}
            </ul>
            <div className="flex justify-between mt-1 pt-1 border-t border-border/60 dark:border-border-dark/60 num">
              <span className="text-ink-muted">Total</span>
              <span>{fmtQty(askTotal)}</span>
            </div>
          </div>
        </div>

        <div className="mt-3 text-xs flex flex-wrap gap-x-4 gap-y-1 text-ink-soft">
          <span>
            Spread: <span className="num">{data.spread.toFixed(2)}</span>
          </span>
          <span>
            Imbalance:{" "}
            <span
              className={cx(
                "pill",
                data.dominant_side === "BUY"
                  ? "pill-up"
                  : data.dominant_side === "SELL"
                  ? "pill-down"
                  : "pill-neutral",
              )}
            >
              {data.imbalance_pct.toFixed(0)}% {data.dominant_side}
            </span>
          </span>
          <span className="text-ink-muted">
            Provider max levels: {maxAvail}
          </span>
        </div>
      </div>
    </div>
  );
}
