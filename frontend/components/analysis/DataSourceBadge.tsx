"use client";

import { cx } from "@/lib/utils";
import type { DataSource } from "@/lib/types";

const LABELS: Record<DataSource, { label: string; tone: "warn" | "neutral" | "ok" | "info" }> = {
  DEMO: { label: "DEMO", tone: "warn" },
  SIMULATED: { label: "SIMULATED", tone: "warn" },
  CSV: { label: "CSV", tone: "info" },
  HISTORICAL: { label: "HISTORICAL", tone: "info" },
  LIVE: { label: "LIVE", tone: "ok" },
};

export default function DataSourceBadge({
  source,
  hint,
  className,
}: {
  source: DataSource | string;
  hint?: string;
  className?: string;
}) {
  const cfg = LABELS[(source as DataSource) in LABELS ? (source as DataSource) : "SIMULATED"] ?? LABELS.SIMULATED;
  return (
    <span
      title={hint}
      className={cx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium tracking-wide uppercase",
        cfg.tone === "ok" && "bg-brand/15 text-brand-dark dark:text-up",
        cfg.tone === "warn" && "bg-yellow-100 text-yellow-800 dark:bg-yellow-500/10 dark:text-yellow-300",
        cfg.tone === "info" && "bg-blue-100 text-blue-800 dark:bg-blue-500/10 dark:text-blue-300",
        cfg.tone === "neutral" && "bg-gray-100 text-ink-soft dark:bg-white/5",
        className,
      )}
    >
      <span
        className={cx(
          "inline-block w-1.5 h-1.5 rounded-full",
          cfg.tone === "ok" && "bg-brand animate-pulse",
          cfg.tone === "warn" && "bg-yellow-500",
          cfg.tone === "info" && "bg-blue-500",
          cfg.tone === "neutral" && "bg-neutral",
        )}
      />
      {cfg.label}
      {hint && <span className="text-ink-muted normal-case font-normal">— {hint}</span>}
    </span>
  );
}
