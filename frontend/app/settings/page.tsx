"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { UserSettings } from "@/lib/types";
import { cx } from "@/lib/utils";

const FIELDS: Array<{
  key: keyof UserSettings;
  label: string;
  type: "number" | "int" | "bool" | "text";
  step?: number;
  hint?: string;
}> = [
  { key: "capital", label: "Available capital (₹)", type: "number", step: 500 },
  { key: "daily_profit_target", label: "Daily profit target (₹)", type: "number", step: 100 },
  { key: "daily_max_loss", label: "Daily max loss (₹)", type: "number", step: 100 },
  { key: "max_loss_per_trade", label: "Max loss per trade (₹)", type: "number", step: 50 },
  { key: "max_trades_per_day", label: "Max trades per day", type: "int" },
  { key: "max_open_positions", label: "Max open positions", type: "int" },
  { key: "min_risk_reward", label: "Minimum R:R", type: "number", step: 0.1 },
  { key: "min_confidence", label: "Signal confidence threshold", type: "int" },
  { key: "conservative_confidence", label: "Conservative confidence threshold", type: "int" },
  { key: "brokerage_per_order", label: "Brokerage per order (₹)", type: "number", step: 1 },
  { key: "slippage_bps", label: "Slippage assumption (bps)", type: "number", step: 1 },
  { key: "preferred_timeframes", label: "Preferred timeframes", type: "text", hint: "Comma separated e.g. 5m,15m" },
  { key: "preferred_strategies", label: "Preferred strategies", type: "text", hint: "trend_vwap,breakout,pullback,orb" },
  { key: "intraday_only", label: "Intraday only", type: "bool" },
  { key: "conservative_after_target", label: "Enable conservative mode after target", type: "bool" },
  { key: "auto_order_execution", label: "Auto order execution (requires broker)", type: "bool" },
];

export default function SettingsPage() {
  const { data, mutate } = useSWR<UserSettings>("/api/settings", fetcher);
  const [form, setForm] = useState<Partial<UserSettings>>({});
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm({});
      setWeights(data.signal_weights);
    }
  }, [data?.id]);

  const active = { ...(data ?? {}), ...form } as UserSettings;

  async function save() {
    setSaving(true);
    try {
      await api.put("/api/settings", { ...form, signal_weights: weights });
      setMsg("Saved");
      mutate();
    } catch (e: any) {
      setMsg(e.message);
    } finally {
      setSaving(false);
      setTimeout(() => setMsg(null), 2000);
    }
  }

  if (!data) return <div className="card p-6 animate-pulse h-64" />;

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold">Trading profile</div>
          <button className="button button-primary" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
        {msg && <div className="text-xs mt-1 text-brand-dark">{msg}</div>}
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          {FIELDS.map((f) => {
            const v = active[f.key] as any;
            if (f.type === "bool") {
              return (
                <label key={f.key} className="flex items-center gap-2 p-2 rounded-md hover:bg-gray-50 dark:hover:bg-white/5">
                  <input
                    type="checkbox"
                    checked={!!v}
                    onChange={(e) =>
                      setForm((s) => ({ ...s, [f.key]: e.target.checked as any }))
                    }
                  />
                  <span>{f.label}</span>
                </label>
              );
            }
            return (
              <label key={f.key} className="flex flex-col gap-1">
                <span className="text-xs text-ink-muted">{f.label}</span>
                <input
                  type={f.type === "text" ? "text" : "number"}
                  step={f.step}
                  value={v ?? ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    const parsed =
                      f.type === "int"
                        ? parseInt(raw || "0", 10)
                        : f.type === "number"
                        ? parseFloat(raw || "0")
                        : raw;
                    setForm((s) => ({ ...s, [f.key]: parsed as any }));
                  }}
                  className="border border-border dark:border-border-dark rounded-md px-2 py-1.5 text-sm bg-transparent num"
                />
                {f.hint && <span className="text-[11px] text-ink-muted">{f.hint}</span>}
              </label>
            );
          })}
        </div>
      </div>

      <div className="card p-4">
        <div className="font-semibold">Signal weights</div>
        <div className="text-xs text-ink-muted">
          Confidence is a weighted sum of these categories. Adjust to prefer certain factors.
        </div>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(weights).map(([k, v]) => (
            <label key={k} className="flex items-center gap-3">
              <span className="w-32 text-sm capitalize">{k.replace("_", " ")}</span>
              <input
                type="range"
                min={0}
                max={30}
                value={v}
                onChange={(e) => setWeights((w) => ({ ...w, [k]: parseInt(e.target.value, 10) }))}
                className="flex-1"
              />
              <span className="w-10 text-right num text-sm">{v}</span>
            </label>
          ))}
        </div>
        <div className="mt-2 text-xs text-ink-muted">
          Total weight: {Object.values(weights).reduce((a, b) => a + b, 0)} (any positive total works)
        </div>
      </div>
    </div>
  );
}
