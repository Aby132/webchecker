export function StatusBadge({ status }) {
  const s = (status || 'UNKNOWN').toUpperCase()
  const cls =
    s === 'UP' ? 'up' :
    s === 'DOWN' ? 'down' :
    s === 'DEGRADED' ? 'degraded' :
    s === 'DISABLED' ? 'disabled' : 'unknown'
  return <span className={`badge ${cls}`}>{s}</span>
}

export function formatMs(value) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value)} ms`
}

export function formatUptime(value) {
  if (value === null || value === undefined) return 'Not enough data'
  return `${Number(value).toFixed(2)}%`
}

export function timeAgo(iso) {
  if (!iso) return 'Never'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}
