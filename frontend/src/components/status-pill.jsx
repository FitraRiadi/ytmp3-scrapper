import { cn } from '@/lib/utils'

export function StatusPill({ health, offline }) {
  if (offline) {
    return (
      <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11.5px] text-muted-foreground">
        <span className="size-2 rounded-full bg-destructive shadow-[0_0_0_3px_oklch(0.66_0.2_22/0.15)]" />
        offline
      </div>
    )
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11.5px] text-muted-foreground">
        <span className="size-2 animate-pulse rounded-full bg-amber-400" />
        menghubungkan…
      </div>
    )
  }

  const ready = health.ffmpeg && health.database
  const label = !health.database ? 'database mati' : !health.ffmpeg ? 'ffmpeg belum ada' : 'siap'
  const title = `yt-dlp ${health.ytdlp || '?'} · ffmpeg ${health.ffmpeg ? 'ok' : 'tidak ada'} · database ${
    health.database ? 'ok' : 'tidak terhubung'
  }`

  return (
    <div
      title={title}
      className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11.5px] text-muted-foreground"
    >
      <span
        className={cn(
          'size-2 rounded-full',
          ready
            ? 'bg-emerald-400 shadow-[0_0_0_3px_oklch(0.7_0.18_160/0.15)]'
            : 'bg-amber-400 shadow-[0_0_0_3px_rgba(251,191,36,0.15)]',
        )}
      />
      <span className="max-w-[150px] truncate">{label}</span>
    </div>
  )
}
