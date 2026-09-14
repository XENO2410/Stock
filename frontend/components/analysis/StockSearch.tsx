"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetcher } from "@/lib/api";
import type { AnalysisInstrument } from "@/lib/types";
import { cx } from "@/lib/utils";

type Props = {
  source?: string;
  placeholder?: string;
  autoFocus?: boolean;
};

const DEBOUNCE_MS = 180;

export default function StockSearch({ source = "mock", placeholder = "Search stock…", autoFocus = false }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query]);

  const url = useMemo(() => {
    const q = encodeURIComponent(debounced);
    return `/api/instruments/search?q=${q}&source=${encodeURIComponent(source)}&limit=12`;
  }, [debounced, source]);

  const { data } = useSWR<AnalysisInstrument[]>(open ? url : null, fetcher, {
    keepPreviousData: true,
  });

  const results = data ?? [];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  const openInstrument = (i: AnalysisInstrument) => {
    setOpen(false);
    setQuery("");
    router.push(`/analysis/${encodeURIComponent(i.symbol)}?source=${encodeURIComponent(source)}`);
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) setOpen(true);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      openInstrument(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={wrapRef} className="relative w-full max-w-md">
      <input
        ref={inputRef}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKey}
        placeholder={placeholder}
        className="w-full px-3 py-1.5 rounded-md border border-border dark:border-border-dark bg-white/70 dark:bg-white/5 text-sm outline-none focus:border-brand"
      />
      {open && (
        <div className="absolute left-0 right-0 mt-1 z-50 rounded-md border border-border dark:border-border-dark bg-white dark:bg-surface-dark-alt shadow-card max-h-80 overflow-auto">
          {results.length === 0 && (
            <div className="px-3 py-2 text-xs text-ink-muted">
              {debounced ? "No matches" : "Start typing a symbol…"}
            </div>
          )}
          {results.map((i, idx) => (
            <button
              key={`${i.exchange}-${i.symbol}`}
              onMouseEnter={() => setActive(idx)}
              onClick={() => openInstrument(i)}
              className={cx(
                "w-full text-left flex items-center justify-between gap-3 px-3 py-2 text-sm",
                idx === active ? "bg-brand/10" : "hover:bg-gray-50 dark:hover:bg-white/[0.04]",
              )}
            >
              <div className="min-w-0">
                <div className="font-medium truncate">{i.symbol}</div>
                <div className="text-[11px] text-ink-muted truncate">{i.display_name}</div>
              </div>
              <div className="text-[11px] text-ink-muted whitespace-nowrap">
                {i.exchange} · {i.segment}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
