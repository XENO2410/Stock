"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { api, API_BASE, fetcher } from "@/lib/api";
import type { CsvFile, ReplaySessionState } from "@/lib/types";
import { cx } from "@/lib/utils";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"];

export default function ReplayIndexPage() {
  const router = useRouter();
  const { data: files, mutate } = useSWR<CsvFile[]>("/api/csv/library", fetcher, { refreshInterval: 5000 });
  const [busy, setBusy] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [upSymbol, setUpSymbol] = useState("");
  const [upTf, setUpTf] = useState("5m");
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function startSession(symbol: string, timeframe: string, source: "csv" | "mock" = "csv") {
    setBusy(true);
    try {
      const s = await api.post<ReplaySessionState>("/api/replay/sessions", { symbol, timeframe, source });
      router.push(`/replay/${encodeURIComponent(symbol)}?session=${s.id}&tf=${encodeURIComponent(timeframe)}`);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    const f = fileRef.current?.files?.[0];
    if (!f || !upSymbol) {
      alert("Pick a file and enter a symbol");
      return;
    }
    setBusy(true);
    setUploadResult(null);
    try {
      const fd = new FormData();
      fd.append("symbol", upSymbol);
      fd.append("timeframe", upTf);
      fd.append("file", f);
      const res = await fetch(`${API_BASE}/api/csv/upload`, { method: "POST", body: fd });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Upload failed");
      setUploadResult(json);
      await mutate();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Historical replay</h1>
            <p className="mt-1 text-sm text-ink-soft">
              Replay a historical OHLCV session candle-by-candle. The analysis engine sees only the
              candles up to the cursor — no look-ahead. Data source is always labelled honestly.
            </p>
          </div>
          <div className="text-[11px] uppercase tracking-wider text-yellow-800 dark:text-yellow-300 bg-yellow-100 dark:bg-yellow-500/10 rounded px-2 py-0.5">
            ₹0 · LOCAL DATA ONLY
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="font-medium">Your CSV library</div>
          <p className="text-xs text-ink-muted mt-1">
            Files at <code>backend/data/csv/&lt;SYMBOL&gt;_&lt;TIMEFRAME&gt;.csv</code>. Header
            columns: <code>timestamp,open,high,low,close,volume</code>.
          </p>
          <div className="mt-3 space-y-2">
            {(files ?? []).length === 0 && (
              <div className="text-sm text-ink-muted">No CSV files yet — upload one on the right, or drop files directly into the folder.</div>
            )}
            {(files ?? []).map((f) => (
              <div key={f.file} className="flex items-center justify-between border border-border dark:border-border-dark rounded-md p-2">
                <div>
                  <div className="text-sm font-medium">{f.symbol} · {f.timeframe || "?"}</div>
                  <div className="text-[11px] text-ink-muted">{f.file} · {(f.size_bytes / 1024).toFixed(1)} KB</div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="text-xs px-2 py-1 rounded bg-brand text-white"
                    disabled={busy}
                    onClick={() => startSession(f.symbol, f.timeframe || "5m", "csv")}
                  >
                    Open replay
                  </button>
                  <button
                    className="text-xs px-2 py-1 rounded bg-down/10 text-down"
                    disabled={busy}
                    onClick={async () => {
                      if (!confirm(`Delete ${f.file}?`)) return;
                      await api.del(`/api/csv/library/${encodeURIComponent(f.file)}`);
                      mutate();
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-4">
          <div className="font-medium">Upload CSV</div>
          <p className="text-xs text-ink-muted mt-1">
            Required columns: <code>timestamp,open,high,low,close,volume</code>. Duplicates are
            merged. Rows failing OHLC sanity are rejected — never silently kept.
          </p>
          <form onSubmit={upload} className="mt-3 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs">
                <span className="text-ink-muted uppercase tracking-wider">Symbol</span>
                <input value={upSymbol} onChange={(e) => setUpSymbol(e.target.value.toUpperCase())} className="border border-border dark:border-border-dark rounded px-2 py-1.5 text-sm bg-transparent" placeholder="RELIANCE" />
              </label>
              <label className="flex flex-col gap-1 text-xs">
                <span className="text-ink-muted uppercase tracking-wider">Timeframe</span>
                <select value={upTf} onChange={(e) => setUpTf(e.target.value)} className="border border-border dark:border-border-dark rounded px-2 py-1.5 text-sm bg-transparent">
                  {TIMEFRAMES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
            </div>
            <input ref={fileRef} type="file" accept=".csv" className="text-xs" />
            <button type="submit" disabled={busy} className="button button-primary w-full disabled:opacity-50">
              {busy ? "Uploading…" : "Upload"}
            </button>
          </form>
          {uploadResult && (
            <div className="mt-3 text-xs border border-border dark:border-border-dark rounded p-2 space-y-1">
              <div><span className="text-ink-muted">Saved as:</span> {uploadResult.saved_as}</div>
              <div><span className="text-ink-muted">Accepted:</span> {uploadResult.accepted_rows} · <span className="text-down">Rejected: {uploadResult.rejected_rows}</span> · Duplicates dropped: {uploadResult.duplicates_dropped}</div>
              <div><span className="text-ink-muted">Range:</span> {new Date(uploadResult.first_timestamp).toLocaleString("en-IN")} → {new Date(uploadResult.last_timestamp).toLocaleString("en-IN")}</div>
            </div>
          )}
        </div>
      </div>

      <div className="card p-4">
        <div className="font-medium">Or replay simulated data</div>
        <p className="text-xs text-ink-muted mt-1">
          Deterministic random-walk data — labelled <code>SIMULATED</code>. Useful for practising the
          replay UI without uploading anything. Not real market data.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "RATNAVEER"].map((sym) => (
            <button
              key={sym}
              disabled={busy}
              className={cx(
                "px-3 py-1 rounded-md text-xs bg-gray-100 dark:bg-white/5 text-ink-soft hover:bg-gray-200 dark:hover:bg-white/10",
              )}
              onClick={() => startSession(sym, "5m", "mock")}
            >
              {sym} 5m
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
