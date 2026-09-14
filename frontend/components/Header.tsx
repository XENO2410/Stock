"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { cx, fmtPct } from "@/lib/utils";
import type { MarketOverview, ProviderInfo } from "@/lib/types";
import { useEffect, useState } from "react";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/signals", label: "Signals" },
  { href: "/positions", label: "Positions" },
  { href: "/journal", label: "Journal" },
  { href: "/analytics", label: "Analytics" },
  { href: "/backtest", label: "Backtest" },
  { href: "/settings", label: "Settings" },
];

export default function Header() {
  const pathname = usePathname();
  const { data: ov } = useSWR<MarketOverview>("/api/market/overview", fetcher, {
    refreshInterval: 3000,
  });
  const { data: prov } = useSWR<ProviderInfo>("/api/market/provider", fetcher, {
    refreshInterval: 30000,
  });
  const [now, setNow] = useState<string>("");

  useEffect(() => {
    const t = setInterval(() => {
      setNow(
        new Date().toLocaleTimeString("en-IN", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    }, 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-white/90 dark:bg-surface-dark/80 backdrop-blur border-b border-border dark:border-border-dark">
      <div className="max-w-[1440px] mx-auto px-4 py-2 flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-brand text-white flex items-center justify-center font-bold text-sm">
            TA
          </div>
          <span className="font-semibold hidden md:inline">Trading Assistant</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {NAV.map((n) => {
            const active = pathname === n.href || (n.href !== "/" && pathname?.startsWith(n.href));
            return (
              <Link
                key={n.href}
                href={n.href}
                className={cx(
                  "px-3 py-1.5 rounded-md text-sm whitespace-nowrap",
                  active
                    ? "bg-brand/10 text-brand-dark dark:text-up"
                    : "text-ink-soft hover:bg-gray-100 dark:hover:bg-white/5",
                )}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4 text-xs">
          <div className="hidden lg:flex items-center gap-3 num">
            {ov?.indices.map((i) => (
              <div key={i.symbol} className="flex items-center gap-1">
                <span className="text-ink-muted">{i.name}</span>
                <span className="font-medium">{i.value.toFixed(2)}</span>
                <span className={cx(i.change >= 0 ? "text-up" : "text-down")}>
                  {fmtPct(i.change_pct)}
                </span>
              </div>
            ))}
          </div>
          <div className="hidden md:flex items-center gap-2">
            <span
              className={cx(
                "inline-block w-2 h-2 rounded-full",
                ov?.status === "LIVE" ? "bg-brand animate-pulse" : "bg-neutral",
              )}
            />
            <span className="text-ink-muted">{ov?.status || "..."}</span>
            <span className="text-ink-soft num">{now}</span>
          </div>
          {prov && (
            <span
              className={cx(
                "pill",
                prov.status && prov.status !== "ok"
                  ? "pill-down"
                  : prov.is_demo
                  ? "pill-neutral"
                  : "pill-up",
              )}
              title={
                prov.status && prov.status !== "ok"
                  ? `${prov.active} unavailable: ${prov.last_error || prov.status}. Falling back to demo. Hit /api/market/provider/diagnose for details.`
                  : `Provider: ${prov.active}`
              }
            >
              {prov.status && prov.status !== "ok"
                ? `${prov.active.toUpperCase()} ⚠`
                : prov.active.toUpperCase()}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
