import clsx from "clsx";

export const cx = clsx;

export function fmtInr(v: number, digits = 2): string {
  if (!isFinite(v)) return "-";
  return v.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtInrCurrency(v: number, digits = 0): string {
  return "₹" + fmtInr(v, digits);
}

export function fmtPct(v: number, digits = 2): string {
  const s = (v >= 0 ? "+" : "") + v.toFixed(digits) + "%";
  return s;
}

export function fmtQty(v: number): string {
  return v.toLocaleString("en-IN");
}

export function fmtCompact(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e7) return (v / 1e7).toFixed(2) + "Cr";
  if (abs >= 1e5) return (v / 1e5).toFixed(2) + "L";
  if (abs >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return String(v);
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-IN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", { hour12: false });
}

export function signalColor(action: string): string {
  switch (action) {
    case "STRONG_BUY":
      return "bg-brand text-white";
    case "BUY":
      return "bg-brand/15 text-brand-dark";
    case "STRONG_SELL":
      return "bg-down text-white";
    case "SELL":
      return "bg-down/15 text-down";
    default:
      return "bg-gray-100 text-neutral";
  }
}

export function signalLabel(action: string): string {
  return action.replace(/_/g, " ");
}

export function directionSign(dir: string): number {
  return dir === "LONG" ? 1 : dir === "SHORT" ? -1 : 0;
}
