"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { DailyGoal } from "@/lib/types";
import { fmtInrCurrency, cx } from "@/lib/utils";

export default function DailyGoalPanel() {
  const { data } = useSWR<DailyGoal>("/api/goal", fetcher, {
    refreshInterval: 3000,
  });
  if (!data) return <div className="card p-4 animate-pulse h-32" />;

  const pct = Math.max(0, Math.min(100, data.progress_pct));
  const targetReached = data.target_reached;
  const lossHit = data.loss_limit_hit;

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-ink-muted">Today's trading goal</div>
          <div className="mt-1 flex items-baseline gap-2">
            <div className="text-3xl font-semibold num">
              <span className={cx(data.realized_pnl >= 0 ? "text-up" : "text-down")}>
                {fmtInrCurrency(data.realized_pnl)}
              </span>
            </div>
            <div className="text-sm text-ink-muted">
              / {fmtInrCurrency(data.daily_target)}
            </div>
          </div>
          <div className="text-xs text-ink-muted mt-0.5">
            Remaining {fmtInrCurrency(data.remaining_target)} - Max loss {fmtInrCurrency(data.daily_max_loss)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-ink-muted">Trades</div>
          <div className="text-lg font-medium num">
            {data.trades_count} / {data.max_trades}
          </div>
          <div className="text-xs text-ink-muted mt-1">
            Win {data.win_rate.toFixed(0)}% ({data.winning_trades}/{data.losing_trades})
          </div>
        </div>
      </div>
      <div className="mt-3 h-2 rounded bg-gray-100 dark:bg-white/5 overflow-hidden">
        <div
          className={cx(
            "h-full",
            targetReached ? "bg-brand" : "bg-brand/70",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 text-xs text-ink-muted flex items-center gap-3">
        <span>Progress {pct.toFixed(1)}%</span>
        <span>Unrealized {fmtInrCurrency(data.unrealized_pnl)}</span>
        <span>
          Signal threshold {data.active_confidence_threshold}
          {data.conservative_mode && (
            <span className="ml-1 pill pill-neutral">conservative</span>
          )}
        </span>
      </div>

      {targetReached && (
        <div className="mt-3 rounded-lg border border-brand/40 bg-brand/5 dark:bg-brand/10 p-3 text-sm">
          <div className="font-semibold text-brand-dark dark:text-up">🎯 Daily target achieved</div>
          <div className="text-ink-soft mt-1">
            Consider stopping or switching to conservative mode. Overtrading risk is now elevated.
          </div>
        </div>
      )}
      {lossHit && (
        <div className="mt-3 rounded-lg border border-down/40 bg-down/5 p-3 text-sm">
          <div className="font-semibold text-down">🛑 Daily loss limit reached</div>
          <div className="text-ink-soft mt-1">
            No new trade signals are actively recommended. Adjust in Settings if you need to override.
          </div>
        </div>
      )}
    </div>
  );
}
