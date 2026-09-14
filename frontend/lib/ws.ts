"use client";

import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "./api";

type TickPayload = {
  type: "ticks" | "top_signals";
  data: any;
  ts?: string;
};

export function useMarketStream() {
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [changes, setChanges] = useState<Record<string, number>>({});
  const [connected, setConnected] = useState(false);
  const [topSignals, setTopSignals] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    let retry: NodeJS.Timeout | null = null;

    const connect = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/ws/stream`);
        wsRef.current = ws;
        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          if (!closed) retry = setTimeout(connect, 2000);
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (evt) => {
          try {
            const msg: TickPayload = JSON.parse(evt.data);
            if (msg.type === "ticks" && Array.isArray(msg.data)) {
              setPrices((prev) => {
                const next = { ...prev };
                for (const t of msg.data) next[t.symbol] = t.price;
                return next;
              });
              setChanges((prev) => {
                const next = { ...prev };
                for (const t of msg.data) next[t.symbol] = t.change_pct;
                return next;
              });
            } else if (msg.type === "top_signals") {
              setTopSignals(msg.data || []);
            }
          } catch {}
        };
      } catch {
        if (!closed) retry = setTimeout(connect, 2000);
      }
    };
    connect();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
    };
  }, []);

  return { prices, changes, topSignals, connected };
}
