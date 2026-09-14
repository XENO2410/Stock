"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { AnalysisReport, AnalysisWeights, ReplaySessionState } from "@/lib/types";
import { cx, fmtInrCurrency } from "@/lib/utils";

import AnalysisChart, { Overlays } from "@/components/analysis/AnalysisChart";
import OverlayToggles from "@/components/analysis/OverlayToggles";
import SignalCard from "@/components/analysis/SignalCard";
import ConfluenceBars from "@/components/analysis/ConfluenceBars";
import WhyPanel from "@/components/analysis/WhyPanel";
import TradePlanCard from "@/components/analysis/TradePlanCard";
import MultiTimeframeStrip from "@/components/analysis/MultiTimeframeStrip";
import AnalysisFactsGrid from "@/components/analysis/AnalysisFactsGrid";
import ZonesList from "@/components/analysis/ZonesList";
import ReplayControls from "@/components/replay/ReplayControls";

const DEFAULT_OVERLAYS: Overlays = {
  ema9: true,
  ema20: true,
  ema50: false,
  vwap: true,
  sma20: false,
  support: true,
  resistance: true,
  structure: true,
  bos_choch: true,
  trade_plan: true,
};

export default function ReplayWorkspacePage({ params }: { params: { symbol: string } }) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = searchParams.get("session");
  const initialTf = searchParams.get("tf") || "5m";

  const [timeframe, setTimeframe] = useState<string>(initialTf);
  const [overlays, setOverlays] = useState<Overlays>(DEFAULT_OVERLAYS);
  const [playing, setPlaying] = useState(false);

  const { data: state, mutate: mutateState } = useSWR<ReplaySessionState>(
    sessionId ? `/api/replay/sessions/${sessionId}` : null,
    fetcher,
    { refreshInterval: 0 },
  );

  const candlesUrl = sessionId
    ? `/api/replay/sessions/${sessionId}/candles?tf=${encodeURIComponent(timeframe)}&limit=1000`
    : undefined;
  const analysisUrl = sessionId
    ? `/api/replay/sessions/${sessionId}/analysis?tf=${encodeURIComponent(timeframe)}`
    : null;

  const { data: report, mutate: mutateReport } = useSWR<AnalysisReport>(
    analysisUrl,
    fetcher,
    { refreshInterval: 0, keepPreviousData: true },
  );
  const { data: weights } = useSWR<AnalysisWeights>("/api/analysis/weights", fetcher);

  const refresh = async () => {
    await Promise.all([mutateState(), mutateReport()]);
  };

  // Autoplay loop
  const playRef = useRef(false);
  useEffect(() => {
    playRef.current = playing;
  }, [playing]);
  useEffect(() => {
    if (!sessionId) return;
    let stopped = false;
    (async () => {
      while (!stopped) {
        if (!playRef.current) {
          await new Promise((r) => setTimeout(r, 150));
          continue;
        }
        const s = state;
        if (s?.status === "finished") {
          setPlaying(false);
          continue;
        }
        try {
          const next = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/step?count=1`);
          mutateState(next, { revalidate: false });
          await mutateReport();
          if (next.status === "finished") setPlaying(false);
          const speed = next.speed || 1;
          const gapMs = Math.max(50, 1000 / speed);
          await new Promise((r) => setTimeout(r, gapMs));
        } catch {
          setPlaying(false);
        }
      }
    })();
    return () => {
      stopped = true;
    };
  }, [sessionId, mutateState, mutateReport, state]);

  const changeTf = (tf: string) => setTimeframe(tf);

  const onStep = async (n: number) => {
    if (!sessionId) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/step?count=${n}`);
    mutateState(s, { revalidate: false });
    await mutateReport();
  };
  const onBack = async (n: number) => {
    if (!sessionId) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/back?count=${n}`);
    mutateState(s, { revalidate: false });
    await mutateReport();
  };
  const onReset = async () => {
    if (!sessionId) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/reset`);
    mutateState(s, { revalidate: false });
    await mutateReport();
  };
  const onJumpToStart = async () => {
    if (!sessionId) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/goto`, { index: 30 });
    mutateState(s, { revalidate: false });
    await mutateReport();
  };
  const onJumpToEnd = async () => {
    if (!sessionId || !state) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/goto`, {
      index: state.total_candles - 1,
    });
    mutateState(s, { revalidate: false });
    await mutateReport();
  };
  const onSpeed = async (v: number) => {
    if (!sessionId) return;
    const s = await api.post<ReplaySessionState>(`/api/replay/sessions/${sessionId}/speed?value=${v}`);
    mutateState(s, { revalidate: false });
  };
  const onPlayPause = () => setPlaying((p) => !p);

  const availableTfs = state?.available_timeframes ?? ["5m", "15m", "1h", "1d"];

  if (!sessionId) {
    return (
      <div className="card p-4">
        <div className="text-sm text-ink-muted">
          No session id in URL. Start one from{" "}
          <button onClick={() => router.push("/replay")} className="text-brand underline">
            /replay
          </button>
          .
        </div>
      </div>
    );
  }

  if (!state) return <div className="card p-4 animate-pulse h-24" />;

  return (
    <div className="space-y-4">
      <ReplayControls
        state={state}
        playing={playing}
        onPlayPause={onPlayPause}
        onStep={onStep}
        onBack={onBack}
        onReset={onReset}
        onJumpToStart={onJumpToStart}
        onJumpToEnd={onJumpToEnd}
        onSpeed={onSpeed}
      />

      <div className="card p-2 flex flex-wrap items-center gap-1">
        {availableTfs.map((tf) => (
          <button
            key={tf}
            onClick={() => changeTf(tf)}
            className={cx(
              "px-2 py-1 rounded-md text-xs font-medium",
              tf === timeframe
                ? "bg-brand text-white"
                : "bg-gray-100 dark:bg-white/5 text-ink-soft hover:bg-gray-200 dark:hover:bg-white/10",
            )}
          >
            {tf}
          </button>
        ))}
        <div className="mx-3 h-4 w-px bg-border dark:bg-border-dark" />
        <OverlayToggles overlays={overlays} onChange={setOverlays} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <div className="space-y-4 min-w-0">
          <div className="card p-0 overflow-hidden">
            <AnalysisChart
              symbol={symbol}
              timeframe={timeframe}
              overlays={overlays}
              report={report ?? null}
              candlesUrl={candlesUrl}
              refreshMs={0}
            />
          </div>
          {report && <AnalysisFactsGrid report={report} />}
          {report && <ZonesList report={report} />}
        </div>

        <div className="space-y-4">
          {report ? (
            <>
              <SignalCard report={report} />
              <MultiTimeframeStrip report={report} />
              <ConfluenceBars report={report} weights={weights} />
              <WhyPanel report={report} />
              <TradePlanCard report={report} />
            </>
          ) : (
            <div className="card p-4 animate-pulse h-40" />
          )}
        </div>
      </div>
    </div>
  );
}
