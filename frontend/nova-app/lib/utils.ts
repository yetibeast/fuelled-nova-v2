export function formatPrice(n: number | null | undefined): string {
  if (n == null) return "---";
  return "$" + Math.round(n).toLocaleString();
}

export function formatRcn(n: number): string {
  if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(2) + "M";
  return formatPrice(n);
}

export function timeAgo(ts: string | number): string {
  const d = new Date(ts);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  if (diff < 172800) return "Yesterday";
  return d.toLocaleDateString();
}

export function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return min + "m ago";
  const hr = Math.floor(min / 60);
  if (hr < 24) return hr + "h ago";
  const days = Math.floor(hr / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return days + "d ago";
  const d = new Date(ts);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return months[d.getMonth()] + " " + d.getDate();
}

export function catName(raw: string | null): string {
  if (!raw) return "Uncategorized";
  return raw
    .replace(/_/g, " ")
    .replace(/\bpvf\b/i, "PVF")
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

export function statusDotClass(dateStr: string | null): string {
  if (!dateStr) return "status-red";
  const hrs = (Date.now() - new Date(dateStr).getTime()) / 3600000;
  if (hrs < 48) return "status-green";
  if (hrs < 168) return "status-yellow";
  return "status-red";
}

export function confidenceColor(c: string): string {
  if (c === "HIGH") return "#4CAF50";
  if (c === "MEDIUM") return "#FF9800";
  return "#F44336";
}

export function confidenceTailwind(c: string): string {
  if (c === "HIGH") return "emerald-400";
  if (c === "MEDIUM") return "amber-400";
  return "red-400";
}

export function fileIcon(name: string): string {
  const ext = (name || "").split(".").pop()?.toLowerCase() || "";
  if (ext === "pdf") return "\uD83D\uDCC4";
  if (["png", "jpg", "jpeg", "webp", "gif", "bmp", "svg"].includes(ext)) return "\uD83D\uDDBC\uFE0F";
  if (["xlsx", "xls", "csv"].includes(ext)) return "\uD83D\uDCCA";
  if (["eml", "msg"].includes(ext)) return "\uD83D\uDCE7";
  return "\uD83D\uDCC4";
}

export function formatFmvRange(low: number | null | undefined, high: number | null | undefined): string {
  return low != null && high != null ? `${formatPrice(low)} – ${formatPrice(high)}` : "---";
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return Math.round(bytes / 1024) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}
