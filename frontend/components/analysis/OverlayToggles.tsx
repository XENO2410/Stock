"use client";

import type { Overlays } from "./AnalysisChart";
import { cx } from "@/lib/utils";

const GROUPS: { title: string; items: { key: keyof Overlays; label: string }[] }[] = [
  {
    title: "Moving averages",
    items: [
      { key: "ema9", label: "EMA 9" },
      { key: "ema20", label: "EMA 20" },
      { key: "ema50", label: "EMA 50" },
      { key: "sma20", label: "SMA 20" },
      { key: "vwap", label: "VWAP" },
    ],
  },
  {
    title: "Zones",
    items: [
      { key: "support", label: "Support" },
      { key: "resistance", label: "Resistance" },
    ],
  },
  {
    title: "Structure",
    items: [
      { key: "structure", label: "HH/HL/LH/LL" },
      { key: "bos_choch", label: "BOS/CHOCH" },
      { key: "trade_plan", label: "Trade plan" },
    ],
  },
];

export default function OverlayToggles({
  overlays,
  onChange,
}: {
  overlays: Overlays;
  onChange: (o: Overlays) => void;
}) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs">
      {GROUPS.map((g) => (
        <div key={g.title} className="flex items-center gap-2">
          <span className="text-ink-muted uppercase tracking-wide text-[10px]">{g.title}</span>
          {g.items.map((item) => {
            const checked = overlays[item.key];
            return (
              <button
                key={item.key}
                onClick={() => onChange({ ...overlays, [item.key]: !checked })}
                className={cx(
                  "px-2 py-0.5 rounded border text-[11px]",
                  checked
                    ? "bg-brand/10 text-brand-dark border-brand/40 dark:text-up"
                    : "bg-transparent text-ink-soft border-border dark:border-border-dark hover:bg-gray-50 dark:hover:bg-white/5",
                )}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
