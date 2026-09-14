"use client";

import type { AnalysisReport } from "@/lib/types";
import { fmtInr, fmtInrCurrency } from "@/lib/utils";

export default function TradePlanCard({ report }: { report: AnalysisReport }) {
  const plan = report.trade_plan;
  if (!plan || report.signal === "WAIT") {
    return (
      <div className="card p-4">
        <div className="text-xs uppercase tracking-wider text-ink-muted">Trade plan</div>
        <div className="mt-2 text-sm text-ink-soft">
          <div className="font-medium">NO TRADE PLAN</div>
          <div className="mt-1 text-xs text-ink-muted">
            {report.warnings[0] ??
              "The engine will not force an entry without adequate confluence and risk/reward."}
          </div>
        </div>
      </div>
    );
  }

  const entry = (plan.entry_low + plan.entry_high) / 2;
  const riskPerShare = Math.abs(entry - plan.stop);
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-ink-muted">Trade plan</div>
        <div className="text-[11px] px-2 py-0.5 rounded bg-brand/10 text-brand-dark dark:text-up">
          {report.signal}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <Row label="Entry" value={
          plan.entry_low === plan.entry_high
            ? fmtInrCurrency(entry)
            : `${fmtInr(plan.entry_low)} – ${fmtInr(plan.entry_high)}`
        } />
        <Row label="Invalidation" value={fmtInrCurrency(plan.stop)} tone="down" />
        <Row label="Target 1" value={fmtInrCurrency(plan.target_1)} tone="up" />
        <Row label="Target 2" value={fmtInrCurrency(plan.target_2)} tone="up" />
        <Row label="Risk / share" value={fmtInrCurrency(riskPerShare)} />
        <Row label="Risk / Reward" value={`1 : ${plan.risk_reward.toFixed(2)}`} bold />
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  tone,
  bold,
}: {
  label: string;
  value: string;
  tone?: "up" | "down";
  bold?: boolean;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase text-ink-muted">{label}</div>
      <div
        className={
          "num " +
          (bold ? "font-semibold " : "") +
          (tone === "up" ? "text-up " : tone === "down" ? "text-down " : "")
        }
      >
        {value}
      </div>
    </div>
  );
}
