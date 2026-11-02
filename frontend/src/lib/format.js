export function formatDuration(totalSeconds) {
  const total = Math.max(0, Math.round(Number(totalSeconds) || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (value) => String(value).padStart(2, '0')
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`
}

export function formatViews(count) {
  const value = Number(count) || 0
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1).replace('.0', '')} M views`
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1).replace('.0', '')} jt views`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1).replace('.0', '')} rb views`
  return value ? `${value} views` : ''
}
