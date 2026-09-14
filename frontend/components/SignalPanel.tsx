"use client";

import { useState } from "react";
import type { SignalOut } from "@/lib/types";
import { cx, fmtInr, fmtInrCurrency, signalColor, signalLabel } from "@/lib/utils";

export default function SignalPanel({
  symbol,
  signal,
}: {
  symbol: string;
  signal: SignalOut | null;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!signal) return <div className="card p-4 animate-pulse h-64" />;

  const noTrade = signal.action === "NO_TRADE";
  const entryMid = (signal.entry_low + signal.entry_high) / 2;

  return (
    <div className="card overflow-hidden">
      <div className="p-4">
        <div className="text-xs uppercase text-ink-muted">Signal</div>
        <div className="mt-1 flex items-center gap-2">
          <div className="text-lg font-semibold">{symbol}</div>
          <span className={cx("pill", signalColor(signal.action))}>
            {signalLabel(signal.action)}
          </span>
        </div>
        {noTrade ? (
          <NoTradeBlock signal={signal} />
        ) : (
          <TradeBlock signal={signal} entryMid={entryMid} />
        )}

        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-4 button button-secondary w-full"
        >
          {expanded ? "Hide" : "Why this signal?"}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-border dark:border-border-dark p-4 text-sm">
          <div className="text-xs uppercase text-ink-muted mb-2">Breakdown</div>
          <table className="w-full">
            <tbody>
              {Object.entries(signal.breakdown).map(([k, v]) => (
                <tr key={k} className="[&>td]:py-1">
                  <td className="w-1/3 text-ink-soft">{k}</td>
                  <td>{v.verdict}</td>
                  <td className="text-right num">
                    +{v.score}
                    <span className="text-ink-muted">/{v.max}</span>
                  </td>
                </tr>
              ))}
              <tr className="border-t border-border/60 dark:border-border-dark/60">
                <td className="pt-2 font-medium">Total confidence</td>
                <td></td>
                <td className="pt-2 text-right font-semibold num">{signal.confidence}/100</td>
              </tr>
            </tbody>
          </table>

          <div className="mt-3">
            <div className="text-xs uppercase text-ink-muted mb-1">Reasons</div>
            <ul className="list-disc pl-5 text-sm text-ink-soft space-y-1">
              {signal.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <div className="mt-3">
            <div className="text-xs uppercase text-ink-muted mb-1">Invalid if</div>
            <div className="text-sm text-down">{signal.invalidation}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function TradeBlock({ signal, entryMid }: { signal: SignalOut; entryMid: number }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3 mt-4 text-sm">
      <Info label="Confidence" value={`${signal.confidence}/100`} bold />
      <Info label="Strategy" value={signal.strategy.replace("_", " ")} />
      <Info
        label="Entry"
        value={
          signal.entry_low === signal.entry_high
            ? fmtInrCurrency(entryMid)
            : `${fmtInr(signal.entry_low)} - ${fmtInr(signal.entry_high)}`
        }
      />
      <Info label="Stop loss" value={fmtInrCurrency(signal.stop_loss)} tone="down" />
      <Info label="Target 1" value={fmtInrCurrency(signal.target_1)} tone="up" />
      <Info label="Target 2" value={fmtInrCurrency(signal.target_2)} tone="up" />
      <Info label="R:R" value={`1 : ${signal.risk_reward.toFixed(2)}`} />
      <Info
        label="Valid until"
        value={
          signal.valid_until
            ? new Date(signal.valid_until).toLocaleTimeString("en-IN", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
              })
            : "-"
        }
      />
    </div>
  );
}

function NoTradeBlock({ signal }: { signal: SignalOut }) {
  return (
    <div className="mt-3 text-sm text-ink-soft">
      <div className="rounded-lg bg-gray-50 dark:bg-white/5 p-3">
        <div className="font-medium text-ink">Reason</div>
        <ul className="mt-1 list-disc pl-5 space-y-1">
          {signal.reasons.slice(0, 4).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
        <div className="mt-2 text-ink-muted text-xs">
          Confidence {signal.confidence}/100 — below the current threshold.
        </div>
      </div>
    </div>
  );
}

function Info({
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
        className={cx(
          "num",
          bold && "font-semibold",
          tone === "up" && "text-up",
          tone === "down" && "text-down",
        )}
      >
        {value}
      </div>
    </div>
  );
}
