"use client";

import { useMarketStream } from "@/lib/ws";
import Link from "next/link";
import { cx, signalColor, signalLabel } from "@/lib/utils";

export default function TopSignals() {
  const { topSignals } = useMarketStream();
  const list = topSignals.filter((s) => s.action !== "NO_TRADE").slice(0, 8);

  return (
    <div className="card">
      <div className="p-3 border-b border-border dark:border-border-dark font-semibold">
        Top signals (live)
      </div>
      <ul className="divide-y divide-border/60 dark:divide-border-dark/60">
        {list.length === 0 && (
          <li className="p-4 text-sm text-ink-muted">
            No high-quality signals right now. Sit tight - the engine is watching.
          </li>
        )}
        {list.map((s: any) => (
          <li key={s.symbol} className="p-3 flex items-center justify-between text-sm">
            <div>
              <Link href={`/stock/${s.symbol}`} className="font-medium">
                {s.symbol}
              </Link>
              <div className="text-[11px] text-ink-muted">
                {s.strategy} - confidence {s.confidence}
              </div>
            </div>
            <span className={cx("pill", signalColor(s.action))}>
              {signalLabel(s.action)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
