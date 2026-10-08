export function formatBytes(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—"
  const units = ["B", "KB", "MB", "GB", "TB"]
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v < 10 && i > 0 ? v.toFixed(1) : Math.round(v)} ${units[i]}`
}

export function formatDate(raw: string): string {
  if (!raw) return ""
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function pct(n: number): string {
  return `${Math.round(n * 100)}%`
}

export function senderLabel(name: string, email: string): string {
  return name || email || "(unknown)"
}
