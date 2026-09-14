"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
  SeriesMarker,
} from "lightweight-charts";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { AnalysisReport, Candle } from "@/lib/types";

export type Overlays = {
  ema9: boolean;
  ema20: boolean;
  ema50: boolean;
  vwap: boolean;
  sma20: boolean;
  support: boolean;
  resistance: boolean;
  structure: boolean;
  bos_choch: boolean;
  trade_plan: boolean;
};

function ema(values: number[], period: number): number[] {
  if (!values.length) return [];
  const k = 2 / (period + 1);
  const out: number[] = [values[0]];
  for (let i = 1; i < values.length; i++) out.push(values[i] * k + out[i - 1] * (1 - k));
  return out;
}

function sma(values: number[], period: number): number[] {
  const out: number[] = new Array(values.length).fill(NaN);
  if (values.length < period) return out;
  let sum = 0;
  for (let i = 0; i < period; i++) sum += values[i];
  out[period - 1] = sum / period;
  for (let i = period; i < values.length; i++) {
    sum += values[i] - values[i - period];
    out[i] = sum / period;
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

export default function AnalysisChart({
  symbol,
  timeframe,
  overlays,
  report,
  candlesUrl,
  refreshMs = 4000,
}: {
  symbol: string;
  timeframe: string;
  overlays: Overlays;
  report: AnalysisReport | null | undefined;
  candlesUrl?: string;
  refreshMs?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const overlaySeriesRef = useRef<Record<string, ISeriesApi<any>>>({});
  const priceLinesRef = useRef<any[]>([]);
  const zoneSeriesRef = useRef<ISeriesApi<any>[]>([]);

  const url =
    candlesUrl ?? `/api/market/candles/${symbol}?timeframe=${timeframe}&limit=300`;
  const { data: candles } = useSWR<Candle[]>(url, fetcher, { refreshInterval: refreshMs });

  // --- Init ---
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
      height: 480,
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
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // --- Candles + volume ---
  useEffect(() => {
    if (!candles || !candleSeriesRef.current || !volSeriesRef.current) return;
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
      color: c.close >= c.open ? "rgba(0,179,134,0.35)" : "rgba(235,91,60,0.35)",
    }));
    candleSeriesRef.current.setData(cData);
    volSeriesRef.current.setData(vData);
  }, [candles]);

  // --- Overlays (EMA / SMA / VWAP) ---
  useEffect(() => {
    if (!candles || !chartRef.current) return;

    // Clear previous overlays
    for (const k of Object.keys(overlaySeriesRef.current)) {
      chartRef.current.removeSeries(overlaySeriesRef.current[k]);
    }
    overlaySeriesRef.current = {};

    const times = candles.map((c) => (new Date(c.time).getTime() / 1000) as UTCTimestamp);
    const closes = candles.map((c) => c.close);

    if (overlays.ema9) {
      const s = chartRef.current.addLineSeries({ color: "#00b386", lineWidth: 1 });
      s.setData(ema(closes, 9).map((v, i) => ({ time: times[i], value: v })));
      overlaySeriesRef.current.ema9 = s;
    }
    if (overlays.ema20) {
      const s = chartRef.current.addLineSeries({ color: "#e08a00", lineWidth: 1 });
      s.setData(ema(closes, 20).map((v, i) => ({ time: times[i], value: v })));
      overlaySeriesRef.current.ema20 = s;
    }
    if (overlays.ema50) {
      const s = chartRef.current.addLineSeries({ color: "#3c6df0", lineWidth: 1 });
      s.setData(ema(closes, 50).map((v, i) => ({ time: times[i], value: v })));
      overlaySeriesRef.current.ema50 = s;
    }
    if (overlays.sma20) {
      const s = chartRef.current.addLineSeries({ color: "#8b93a7", lineWidth: 1, lineStyle: 2 });
      const smaValues = sma(closes, 20);
      s.setData(
        smaValues
          .map((v, i) => ({ time: times[i], value: v }))
          .filter((p) => !Number.isNaN(p.value)),
      );
      overlaySeriesRef.current.sma20 = s;
    }
    if (overlays.vwap) {
      const s = chartRef.current.addLineSeries({ color: "#8b93a7", lineWidth: 2 });
      s.setData(vwapSeries(candles).map((v, i) => ({ time: times[i], value: v })));
      overlaySeriesRef.current.vwap = s;
    }
  }, [candles, overlays.ema9, overlays.ema20, overlays.ema50, overlays.sma20, overlays.vwap]);

  // --- Support / Resistance zones (as area series between low & high) ---
  useEffect(() => {
    if (!chartRef.current || !candles || candles.length === 0) return;
    for (const s of zoneSeriesRef.current) chartRef.current.removeSeries(s);
    zoneSeriesRef.current = [];
    if (!report) return;

    const timeStart = (new Date(candles[0].time).getTime() / 1000) as UTCTimestamp;
    const timeEnd = (new Date(candles[candles.length - 1].time).getTime() / 1000) as UTCTimestamp;

    const drawZone = (low: number, high: number, color: string) => {
      // A single-value area between price_low and price_high visualised as two
      // horizontal lines and a translucent band via addBaselineSeries.
      const bandTop = chartRef.current!.addLineSeries({
        color,
        lineStyle: 2,
        lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      bandTop.setData([{ time: timeStart, value: high }, { time: timeEnd, value: high }]);
      const bandBottom = chartRef.current!.addLineSeries({
        color,
        lineStyle: 2,
        lineWidth: 1,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      bandBottom.setData([{ time: timeStart, value: low }, { time: timeEnd, value: low }]);
      zoneSeriesRef.current.push(bandTop, bandBottom);
    };

    if (overlays.support) {
      for (const z of report.support.slice(0, 3)) {
        drawZone(z.price_low, z.price_high, "rgba(0,179,134,0.55)");
      }
    }
    if (overlays.resistance) {
      for (const z of report.resistance.slice(0, 3)) {
        drawZone(z.price_low, z.price_high, "rgba(235,91,60,0.55)");
      }
    }
  }, [report, candles, overlays.support, overlays.resistance]);

  // --- Structure markers (HH/HL/LH/LL, BOS, CHOCH) ---
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    if (!report || !candles) {
      candleSeriesRef.current.setMarkers([]);
      return;
    }
    const markers: SeriesMarker<UTCTimestamp>[] = [];

    if (overlays.structure || overlays.bos_choch) {
      for (const ev of report.structure.events) {
        const t = (new Date(ev.timestamp).getTime() / 1000) as UTCTimestamp;
        const isBOSCHOCH = ev.type.startsWith("BOS") || ev.type.startsWith("CHOCH");
        if (isBOSCHOCH && !overlays.bos_choch) continue;
        if (!isBOSCHOCH && !overlays.structure) continue;
        const isUp = ev.type.includes("UP") || ev.type === "HH" || ev.type === "HL";
        markers.push({
          time: t,
          position: isUp ? "belowBar" : "aboveBar",
          shape: isBOSCHOCH ? "square" : "circle",
          color: ev.type.includes("CHOCH")
            ? "#e08a00"
            : ev.type.includes("BOS")
            ? "#3c6df0"
            : isUp
            ? "#00b386"
            : "#eb5b3c",
          text: ev.type.replace("_", " "),
        });
      }
    }
    // Order markers by time - lightweight-charts requires that.
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    candleSeriesRef.current.setMarkers(markers);
  }, [report, candles, overlays.structure, overlays.bos_choch]);

  // --- Trade plan lines ---
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    for (const pl of priceLinesRef.current) candleSeriesRef.current.removePriceLine(pl);
    priceLinesRef.current = [];
    if (!overlays.trade_plan || !report?.trade_plan || report.signal === "WAIT") return;
    const plan = report.trade_plan;
    const entry = (plan.entry_low + plan.entry_high) / 2;
    priceLinesRef.current.push(
      candleSeriesRef.current.createPriceLine({
        price: entry,
        color: "#00b386",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `Entry ${entry.toFixed(2)}`,
      }),
      candleSeriesRef.current.createPriceLine({
        price: plan.stop,
        color: "#eb5b3c",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `Stop ${plan.stop.toFixed(2)}`,
      }),
      candleSeriesRef.current.createPriceLine({
        price: plan.target_1,
        color: "#3c6df0",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `T1 ${plan.target_1.toFixed(2)}`,
      }),
      candleSeriesRef.current.createPriceLine({
        price: plan.target_2,
        color: "#3c6df0",
        lineWidth: 1,
        lineStyle: 1,
        axisLabelVisible: true,
        title: `T2 ${plan.target_2.toFixed(2)}`,
      }),
    );
  }, [report, overlays.trade_plan]);

  return <div ref={containerRef} className="w-full" />;
}
