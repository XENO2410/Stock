"use client";

import type { AnalysisReport } from "@/lib/types";

export default function WhyPanel({ report }: { report: AnalysisReport }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-ink-muted">Why this decision</div>
      <p className="mt-1 text-sm text-ink-soft leading-relaxed">{report.summary}</p>

      <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <Column title="For" tone="up" items={report.positive_evidence} />
        <Column title="Against" tone="down" items={report.negative_evidence} />
        <Column title="Warnings" tone="warn" items={report.warnings} />
      </div>
    </div>
  );
}

function Column({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "up" | "down" | "warn";
  items: string[];
}) {
  return (
    <div>
      <div
        className={
          tone === "up"
            ? "text-brand-dark dark:text-up font-medium"
            : tone === "down"
            ? "text-down font-medium"
            : "text-yellow-700 dark:text-yellow-300 font-medium"
        }
      >
        {title}
      </div>
      {items.length === 0 ? (
        <div className="text-ink-muted mt-1">–</div>
      ) : (
        <ul className="mt-1 list-disc pl-4 space-y-1 text-ink-soft">
          {items.slice(0, 6).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
