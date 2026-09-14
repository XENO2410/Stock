"use client";

import type { AnalysisReport } from "@/lib/types";
import { fmtInr, cx } from "@/lib/utils";

export default function ZonesList({ report }: { report: AnalysisReport }) {
  const strengthLabel = (s: number) => (s >= 3 ? "HIGH" : s >= 2 ? "MEDIUM" : "LOW");

  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-ink-muted">Zones near price</div>
      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <Column
          title="Resistance"
          items={report.resistance.slice(0, 3).map((z) => ({
            range: `${fmtInr(z.price_low)} – ${fmtInr(z.price_high)}`,
            strength: strengthLabel(z.strength),
            reasons: z.reasons,
            tone: "down" as const,
          }))}
        />
        <Column
          title="Support"
          items={report.support.slice(0, 3).map((z) => ({
            range: `${fmtInr(z.price_low)} – ${fmtInr(z.price_high)}`,
            strength: strengthLabel(z.strength),
            reasons: z.reasons,
            tone: "up" as const,
          }))}
        />
      </div>
    </div>
  );
}

function Column({
  title,
  items,
}: {
  title: string;
  items: { range: string; strength: string; reasons: string[]; tone: "up" | "down" }[];
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-ink-muted mb-1">{title}</div>
      {items.length === 0 && <div className="text-xs text-ink-muted">–</div>}
      <ul className="space-y-2">
        {items.map((z, idx) => (
          <li
            key={idx}
            className={cx(
              "rounded-md border px-2.5 py-1.5",
              z.tone === "up"
                ? "border-brand/25 bg-brand/5"
                : "border-down/25 bg-down/5",
            )}
          >
            <div className="flex items-center justify-between text-xs">
              <span className={cx("num font-medium", z.tone === "up" ? "text-brand-dark dark:text-up" : "text-down")}>
                {z.range}
              </span>
              <span className="text-[10px] uppercase text-ink-muted">{z.strength}</span>
            </div>
            {z.reasons.length > 0 && (
              <div className="mt-0.5 text-[11px] text-ink-muted truncate">{z.reasons.join(" · ")}</div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
