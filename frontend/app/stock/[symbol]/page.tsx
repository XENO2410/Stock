"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Quote, SignalOut } from "@/lib/types";
import PriceChart from "@/components/PriceChart";
import SignalPanel from "@/components/SignalPanel";
import MarketDepth from "@/components/MarketDepth";
import TradeControls from "@/components/TradeControls";
import TickTape from "@/components/TickTape";
import { cx, fmtInrCurrency, fmtPct, fmtQty } from "@/lib/utils";

export default function StockPage({ params }: { params: { symbol: string } }) {
  const symbol = params.symbol.toUpperCase();
  const { data: quote } = useSWR<Quote>(`/api/market/quote/${symbol}`, fetcher, {
    refreshInterval: 2000,
  });
  const { data: signal, error: sigErr } = useSWR<SignalOut>(
    `/api/signals/${symbol}`,
    fetcher,
    { refreshInterval: 5000 },
  );

  const up = (quote?.change ?? 0) >= 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="card p-4 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase text-ink-muted">{quote?.name || symbol} · NSE</div>
          <div className="mt-1 flex items-baseline gap-2">
            <div className="text-3xl font-semibold num">
              {quote ? fmtInrCurrency(quote.price) : "…"}
            </div>
            {quote && (
              <div className={cx("num", up ? "text-up" : "text-down")}>
                {up ? "+" : ""}
                {quote.change.toFixed(2)} ({fmtPct(quote.change_pct)})
              </div>
            )}
          </div>
        </div>
        {quote && (
          <div className="hidden md:grid grid-cols-4 gap-x-6 gap-y-1 text-xs">
            <Info label="Open" value={fmtInrCurrency(quote.day_open)} />
            <Info label="High" value={fmtInrCurrency(quote.day_high)} />
            <Info label="Low" value={fmtInrCurrency(quote.day_low)} />
            <Info label="Prev close" value={fmtInrCurrency(quote.prev_close)} />
            <Info label="VWAP" value={fmtInrCurrency(quote.vwap)} />
            <Info label="Volume" value={fmtQty(quote.volume)} />
            <Info label="Upper circuit" value={fmtInrCurrency(quote.upper_circuit)} />
            <Info label="Lower circuit" value={fmtInrCurrency(quote.lower_circuit)} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <PriceChart symbol={symbol} signal={sigErr ? null : signal ?? null} />
          <MarketDepth symbol={symbol} />
        </div>
        <div className="space-y-4">
          <SignalPanel symbol={symbol} signal={sigErr ? null : signal ?? null} />
          <TradeControls symbol={symbol} signal={sigErr ? null : signal ?? null} quote={quote} />
          <TickTape symbol={symbol} />
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-ink-muted">{label}</div>
      <div className="num font-medium">{value}</div>
    </div>
  );
}
