"use client";

import type { ReplaySessionState } from "@/lib/types";
import { cx } from "@/lib/utils";

const SPEEDS = [0.5, 1, 2, 5, 10];

export default function ReplayControls({
  state,
  playing,
  onPlayPause,
  onStep,
  onBack,
  onReset,
  onJumpToStart,
  onJumpToEnd,
  onSpeed,
}: {
  state: ReplaySessionState;
  playing: boolean;
  onPlayPause: () => void;
  onStep: (n: number) => void;
  onBack: (n: number) => void;
  onReset: () => void;
  onJumpToStart: () => void;
  onJumpToEnd: () => void;
  onSpeed: (v: number) => void;
}) {
  const progress = state.total_candles > 0 ? (state.cursor / (state.total_candles - 1)) * 100 : 0;
  const inSampleEnd = state.total_candles > 0 ? (state.in_sample_end_index / (state.total_candles - 1)) * 100 : 0;

  return (
    <div className="card p-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-[11px] uppercase tracking-wider text-yellow-800 dark:text-yellow-300 bg-yellow-100 dark:bg-yellow-500/10 rounded px-2 py-0.5">
          REPLAY
        </div>
        <div className="text-sm font-medium">{state.symbol}</div>
        <div className="text-xs text-ink-muted">{state.primary_timeframe}</div>
        <div className="text-xs text-ink-soft num">
          {state.current_timestamp
            ? new Date(state.current_timestamp).toLocaleString("en-IN", { hour12: false })
            : "—"}
        </div>
        <div className="text-xs text-ink-muted num">
          {state.cursor + 1} / {state.total_candles}
        </div>
        <div
          className={cx(
            "text-[10px] uppercase px-1.5 py-0.5 rounded",
            state.in_sample
              ? "bg-blue-100 text-blue-800 dark:bg-blue-500/10 dark:text-blue-300"
              : "bg-brand/10 text-brand-dark dark:text-up",
          )}
          title={`Train split at index ${state.in_sample_end_index} (${(state.train_frac * 100).toFixed(0)}% train)`}
        >
          {state.in_sample ? "IN-SAMPLE" : "OUT-OF-SAMPLE"}
        </div>

        <div className="ml-auto flex items-center gap-1">
          <Btn onClick={onJumpToStart} title="Jump to start">|◀</Btn>
          <Btn onClick={() => onBack(1)} title="Back 1">◀</Btn>
          <Btn onClick={onPlayPause} title={playing ? "Pause" : "Play"} primary>
            {playing ? "❚❚ Pause" : "▶ Play"}
          </Btn>
          <Btn onClick={() => onStep(1)} title="Step 1">▶</Btn>
          <Btn onClick={() => onStep(10)} title="Step 10">▶▶</Btn>
          <Btn onClick={onJumpToEnd} title="Jump to end">▶|</Btn>
          <Btn onClick={onReset} title="Reset">↺</Btn>
        </div>
      </div>

      <div className="mt-3 relative h-2 rounded bg-gray-100 dark:bg-white/5 overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-brand"
          style={{ width: `${progress}%` }}
        />
        <div
          className="absolute top-0 bottom-0 w-px bg-blue-500"
          style={{ left: `${inSampleEnd}%` }}
          title="Train / Test split"
        />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
        <span className="text-ink-muted">Speed</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeed(s)}
            className={cx(
              "px-2 py-0.5 rounded",
              state.speed === s
                ? "bg-brand text-white"
                : "bg-gray-100 dark:bg-white/5 text-ink-soft",
            )}
          >
            {s}x
          </button>
        ))}
        <span className="ml-auto text-ink-muted">
          Source <span className="font-medium">{state.source}</span>
        </span>
      </div>
    </div>
  );
}

function Btn({
  onClick,
  children,
  title,
  primary,
}: {
  onClick: () => void;
  children: React.ReactNode;
  title?: string;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={cx(
        "px-2.5 py-1 rounded-md text-xs font-medium",
        primary
          ? "bg-brand text-white hover:bg-brand-dark"
          : "bg-gray-100 dark:bg-white/5 text-ink-soft hover:bg-gray-200 dark:hover:bg-white/10",
      )}
    >
      {children}
    </button>
  );
}
