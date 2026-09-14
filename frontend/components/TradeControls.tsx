"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { PositionSize, Quote, SignalOut } from "@/lib/types";
import { cx, fmtInr, fmtInrCurrency } from "@/lib/utils";

export default function TradeControls({
  symbol,
  signal,
  quote,
}: {
  symbol: string;
  signal: SignalOut | null;
  quote?: Quote;
}) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState<number>(0);
  const [entry, setEntry] = useState<number>(0);
  const [sl, setSl] = useState<number>(0);
  const [t1, setT1] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sizing, setSizing] = useState<PositionSize | null>(null);

  useEffect(() => {
    if (!signal || signal.direction === "NONE") return;
    setSide(signal.direction === "LONG" ? "BUY" : "SELL");
    setEntry((signal.entry_low + signal.entry_high) / 2);
    setSl(signal.stop_loss);
    setT1(signal.target_1);
  }, [signal?.id]);

  useEffect(() => {
    let cancel = false;
    async function run() {
      if (!entry || !sl || entry === sl) return;
      try {
        const s = await api.post<PositionSize>("/api/positions/size", {
          entry_price: entry,
          stop_loss: sl,
          direction: side === "BUY" ? "LONG" : "SHORT",
        });
        if (!cancel) {
          setSizing(s);
          if (qty === 0) setQty(s.suggested_quantity);
        }
      } catch (e: any) {
        if (!cancel) setError(e.message);
      }
    }
    run();
    return () => {
      cancel = true;
    };
  }, [entry, sl, side]);

  async function placePaper() {
    setError(null);
    setBusy(true);
    try {
      await api.post("/api/positions", {
        symbol,
        direction: side === "BUY" ? "LONG" : "SHORT",
        quantity: qty || sizing?.suggested_quantity || 1,
        entry_price: entry || quote?.price,
        stop_loss: sl,
        target_1: t1,
        target_2: signal?.target_2 ?? 0,
        strategy: signal?.strategy ?? "manual",
        signal_confidence: signal?.confidence ?? 0,
        mode: "PAPER",
      });
      alert("Paper position opened");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2">
        {(["BUY", "SELL"] as const).map((s) => (
          <button
            key={s}
            className={cx(
              "flex-1 py-1.5 rounded-md text-sm font-medium",
              side === s
                ? s === "BUY"
                  ? "bg-brand text-white"
                  : "bg-down text-white"
                : "bg-gray-100 dark:bg-white/5 text-ink-soft",
            )}
            onClick={() => setSide(s)}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <Field label="Qty" value={qty} onChange={setQty} />
        <Field label="Entry" value={entry} onChange={setEntry} step={0.05} />
        <Field label="Stop loss" value={sl} onChange={setSl} step={0.05} />
        <Field label="Target 1" value={t1} onChange={setT1} step={0.05} />
      </div>

      {sizing && (
        <div className="mt-3 rounded-lg bg-gray-50 dark:bg-white/5 p-3 text-xs">
          <div className="flex justify-between">
            <span className="text-ink-muted">Risk / share</span>
            <span className="num">{fmtInr(sizing.risk_per_share)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Max qty by risk</span>
            <span className="num">{sizing.max_quantity_by_risk}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Suggested qty</span>
            <span className="num font-medium">{sizing.suggested_quantity}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Capital required</span>
            <span className="num">{fmtInrCurrency(sizing.capital_required)}</span>
          </div>
          {sizing.warnings.map((w, i) => (
            <div key={i} className="text-down mt-1">
              ⚠ {w}
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mt-2 text-xs text-down border border-down/40 rounded p-2">{error}</div>
      )}

      <button
        disabled={busy}
        className={cx(
          "mt-4 button w-full",
          side === "BUY" ? "button-primary" : "bg-down text-white hover:bg-down/90",
        )}
        onClick={placePaper}
      >
        {busy ? "Placing…" : `${side} paper`}
      </button>
      <div className="mt-2 text-[11px] text-ink-muted text-center">
        Paper trade only. Live orders require broker integration.
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] text-ink-muted uppercase">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-transparent border border-border dark:border-border-dark rounded-md px-2 py-1.5 num"
      />
    </label>
  );
}
