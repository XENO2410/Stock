"use client";

import { useEffect, useRef, useState } from "react";
import { createChart, IChartApi, ISeriesApi, UTCTimestamp, CrosshairMode } from "lightweight-charts";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Candle, SignalOut } from "@/lib/types";
import { cx } from "@/lib/utils";

const TIMEFRAMES = ["1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"];

type Overlays = {
  vwap: boolean;
  ema9: boolean;
  ema20: boolean;
  ema50: boolean;
  prevDay: boolean;
  sr: boolean;
  signal: boolean;
};

const DEFAULT_OVERLAYS: Overlays = {
  vwap: true,
  ema9: true,
  ema20: true,
  ema50: false,
  prevDay: false,
  sr: false,
  signal: true,
};

function ema(values: number[], period: number): number[] {
  if (!values.length) return [];
  const k = 2 / (period + 1);
  const out: number[] = [values[0]];
  for (let i = 1; i < values.length; i++) {
    out.push(values[i] * k + out[i - 1] * (1 - k));
  }
  return out;
}

function vwapSeries(candles: Candle[]): number[] {
  let cumV = 0;
  let cumPV = 0;
  const out: number[] = [];
  for (const c of candles) {
    const tp = (c.high + c.low + c.close) / 3;
    cumV += c.volume;
    cumPV += tp * c.volume;
    out.push(cumV > 0 ? cumPV / cumV : c.close);
  }
  return out;
}

export default function PriceChart({
  symbol,
  signal,
}: {
  symbol: string;
  signal?: SignalOut | null;
}) {
  const [timeframe, setTimeframe] = useState<string>("5m");
  const [overlays, setOverlays] = useState<Overlays>(DEFAULT_OVERLAYS);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const overlaySeriesRef = useRef<Record<string, ISeriesApi<any>>>({});
  const priceLinesRef = useRef<any[]>([]);

  const { data: candles } = useSWR<Candle[]>(
    `/api/market/candles/${symbol}?timeframe=${timeframe}&limit=300`,
    fetcher,
    { refreshInterval: 3000 },
  );

  // Init chart
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#4b5468",
        fontFamily: "Inter, sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(139,147,167,0.08)" },
        horzLines: { color: "rgba(139,147,167,0.08)" },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
      height: 460,
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00b386",
      downColor: "#eb5b3c",
      borderVisible: false,
      wickUpColor: "#00b386",
      wickDownColor: "#eb5b3c",
    });
    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
      color: "rgba(139,147,167,0.3)",
    });
    volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volSeriesRef.current = volSeries;

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Update data
  useEffect(() => {
    if (!candles || !candleSeriesRef.current) return;
    const cData = candles.map((c) => ({
      time: (new Date(c.time).getTime() / 1000) as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    const vData = candles.map((c) => ({
      time: (new Date(c.time).getTime() / 1000) as UTCTimestamp,
      value: c.volume,
      color:
        c.close >= c.open ? "rgba(0,179,134,0.35)" : "rgba(235,91,60,0.35)",
    }));
    candleSeriesRef.current.setData(cData);
    volSeriesRef.current?.setData(vData);

    // Clear old overlays
    for (const key in overlaySeriesRef.current) {
      chartRef.current?.removeSeries(overlaySeriesRef.current[key]);
    }
    overlaySeriesRef.current = {};

    const times = cData.map((c) => c.time);
    const closes = candles.map((c) => c.close);

    if (overlays.vwap) {
      const v = vwapSeries(candles);
      const s = chartRef.current!.addLineSeries({
        color: "#8b93a7",
        lineWidth: 2,
        lineStyle: 0,
      });
      s.setData(v.map((val, i) => ({ time: times[i], value: val })));
      overlaySeriesRef.current.vwap = s;
    }
    if (overlays.ema9) {
      const v = ema(closes, 9);
      const s = chartRef.current!.addLineSeries({ color: "#00b386", lineWidth: 1 });
      s.setData(v.map((val, i) => ({ time: times[i], value: val })));
      overlaySeriesRef.current.ema9 = s;
    }
    if (overlays.ema20) {
      const v = ema(closes, 20);
      const s = chartRef.current!.addLineSeries({ color: "#e08a00", lineWidth: 1 });
      s.setData(v.map((val, i) => ({ time: times[i], value: val })));
      overlaySeriesRef.current.ema20 = s;
    }
    if (overlays.ema50) {
      const v = ema(closes, 50);
      const s = chartRef.current!.addLineSeries({ color: "#3c6df0", lineWidth: 1 });
      s.setData(v.map((val, i) => ({ time: times[i], value: val })));
      overlaySeriesRef.current.ema50 = s;
    }
  }, [candles, overlays.vwap, overlays.ema9, overlays.ema20, overlays.ema50]);

  // Signal price lines (entry / SL / targets)
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    for (const pl of priceLinesRef.current) {
      candleSeriesRef.current.removePriceLine(pl);
    }
    priceLinesRef.current = [];
    if (!overlays.signal || !signal || signal.direction === "NONE") return;
    const entry = (signal.entry_low + signal.entry_high) / 2;
    priceLinesRef.current.push(
      candleSeriesRef.current.createPriceLine({
        price: entry,
        color: "#00b386",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `Entry ${entry.toFixed(2)}`,
      }),
    );
    if (signal.stop_loss) {
      priceLinesRef.current.push(
        candleSeriesRef.current.createPriceLine({
          price: signal.stop_loss,
          color: "#eb5b3c",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `SL ${signal.stop_loss.toFixed(2)}`,
        }),
      );
    }
    if (signal.target_1) {
      priceLinesRef.current.push(
        candleSeriesRef.current.createPriceLine({
          price: signal.target_1,
          color: "#3c6df0",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `T1 ${signal.target_1.toFixed(2)}`,
        }),
      );
    }
    if (signal.target_2) {
      priceLinesRef.current.push(
        candleSeriesRef.current.createPriceLine({
          price: signal.target_2,
          color: "#3c6df0",
          lineWidth: 1,
          lineStyle: 1,
          axisLabelVisible: true,
          title: `T2 ${signal.target_2.toFixed(2)}`,
        }),
      );
    }
  }, [signal, overlays.signal, candles]);

  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 border-b border-border dark:border-border-dark">
        <div className="flex items-center gap-1 flex-wrap">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={cx(
                "px-2 py-1 rounded-md text-xs",
                tf === timeframe
                  ? "bg-brand text-white"
                  : "bg-gray-100 dark:bg-white/5 text-ink-soft hover:bg-gray-200 dark:hover:bg-white/10",
              )}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap text-xs">
          {(
            [
              ["vwap", "VWAP"],
              ["ema9", "EMA 9"],
              ["ema20", "EMA 20"],
              ["ema50", "EMA 50"],
              ["signal", "Signal lines"],
            ] as [keyof Overlays, string][]
          ).map(([k, label]) => (
            <label key={k} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={overlays[k]}
                onChange={(e) =>
                  setOverlays((o) => ({ ...o, [k]: e.target.checked }))
                }
              />
              {label}
            </label>
          ))}
        </div>
      </div>
      <div ref={containerRef} className="w-full" />
    </div>
  );
}
