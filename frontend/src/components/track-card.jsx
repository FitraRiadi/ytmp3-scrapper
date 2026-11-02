import { Download, FolderOpen, Play, RefreshCw, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { formatDuration, formatViews } from '@/lib/format'
import { cn } from '@/lib/utils'

const BUSY_STATUS = new Set(['queued', 'downloading', 'converting'])

export function TrackCard({ track, job, index = 0, onConvert, onCancel, onRetry, onPlay, onOpenFolder }) {
  const status = job?.status
  const busy = BUSY_STATUS.has(status)
  const ready = status === 'ready'
  const failed = status === 'error'

  return (
    <Card
      className="animate-float-in group gap-0 overflow-hidden border-white/[0.06] bg-white/[0.025] py-0 shadow-none transition-all duration-300 hover:border-white/[0.14] hover:bg-white/[0.045]"
      style={{ animationDelay: `${Math.min(index * 55, 240)}ms` }}
    >
      <CardContent className="flex flex-col gap-4 p-3 sm:flex-row sm:items-center sm:gap-5 sm:p-4">
        {/* thumbnail */}
        <div className="relative aspect-video w-full shrink-0 overflow-hidden rounded-lg bg-muted sm:w-[168px]">
          <img
            src={track.thumbnail}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={(event) => {
              event.currentTarget.src = `https://i.ytimg.com/vi/${track.id}/mqdefault.jpg`
            }}
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
          />

          {track.duration > 0 && (
            <span className="absolute right-1.5 bottom-1.5 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-white">
              {formatDuration(track.duration)}
            </span>
          )}

          {track.live && (
            <span className="absolute top-1.5 left-1.5 rounded bg-red-500 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white">
              live
            </span>
          )}

          {!busy && (
            <button
              type="button"
              onClick={() => onPlay(track, job)}
              aria-label={`Putar ${track.title}`}
              className="absolute inset-0 grid place-items-center bg-black/45 opacity-0 backdrop-blur-[1px] transition duration-200 group-hover:opacity-100 focus-visible:opacity-100"
            >
              <span className="grid size-11 place-items-center rounded-full bg-white text-black shadow-lg transition hover:scale-105">
                <Play className="size-4 fill-current" />
              </span>
            </button>
          )}
        </div>

        {/* info */}
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-[15px] leading-snug font-semibold tracking-tight">
            {track.title}
          </h3>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11.5px] text-muted-foreground">
            <span className="max-w-full truncate">{track.channel}</span>
            {track.viewCount > 0 && (
              <>
                <span className="opacity-40">•</span>
                <span>{formatViews(track.viewCount)}</span>
              </>
            )}
            {ready && job?.sizeLabel && (
              <>
                <span className="opacity-40">•</span>
                <span className="text-emerald-400/90">MP3 {job.sizeLabel}</span>
              </>
            )}
          </div>

          {failed && job?.error && (
            <p className="mt-2.5 rounded-md border border-destructive/25 bg-destructive/10 px-2.5 py-1.5 text-[11px] leading-relaxed text-destructive">
              {job.error}
            </p>
          )}

          {busy && (
            <div className="mt-3 max-w-md">
              <div className="mb-1.5 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
                <span className="truncate">{job.message}</span>
                <span className="shrink-0 tabular-nums text-foreground/80">
                  {Math.round(job.progress)}%
                </span>
              </div>
              <Progress
                value={status === 'queued' ? 30 : Math.max(4, job.progress)}
                className={cn('h-1.5 bg-white/10', status === 'queued' && 'shimmer-bar')}
                indicatorClassName="gradient-primary"
              />
            </div>
          )}
        </div>

        {/* actions */}
        <div className="flex w-full shrink-0 flex-col gap-2 sm:w-[142px]">
          {!job && (
            <>
              <Button
                type="button"
                onClick={() => onPlay(track)}
                variant="outline"
                className="h-10 w-full gap-2 rounded-xl border-white/12 bg-white/[0.03] font-medium hover:bg-white/[0.08]"
              >
                <Play className="size-3.5 fill-current" />
                Putar
              </Button>
              <Button
                type="button"
                onClick={() => onConvert(track)}
                className="gradient-primary glow-primary h-10 w-full gap-2 rounded-xl font-semibold text-white transition hover:brightness-110"
              >
                <Download className="size-4" />
                Convert MP3
              </Button>
            </>
          )}

          {busy && (
            <Button
              type="button"
              variant="outline"
              onClick={() => onCancel(track)}
              className="h-9 w-full gap-1.5 border-white/10 text-[12px] text-muted-foreground hover:text-foreground"
            >
              <X className="size-3.5" />
              Batalkan
            </Button>
          )}

          {ready && (
            <>
              <Button
                type="button"
                onClick={() => onPlay(track, job)}
                variant="outline"
                className="h-10 w-full gap-2 rounded-xl border-white/12 bg-white/[0.03] font-medium hover:bg-white/[0.08]"
              >
                <Play className="size-3.5 fill-current" />
                Preview
              </Button>

              <div className="flex w-full gap-2">
                <Button
                  asChild
                  className="gradient-primary glow-primary h-10 flex-1 gap-2 rounded-xl font-semibold text-white transition hover:brightness-110"
                >
                  <a href={job.downloadUrl} download={job.fileName || 'audio.mp3'}>
                    <Download className="size-4" />
                    Download
                  </a>
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  title="Buka folder file"
                  onClick={() => onOpenFolder(track)}
                  className="hidden size-10 shrink-0 rounded-xl border-white/12 bg-white/[0.03] sm:inline-flex"
                >
                  <FolderOpen className="size-4" />
                </Button>
              </div>
            </>
          )}

          {failed && (
            <>
              <Button
                type="button"
                onClick={() => onPlay(track)}
                variant="outline"
                className="h-10 w-full gap-2 rounded-xl border-white/12 bg-white/[0.03] font-medium hover:bg-white/[0.08]"
              >
                <Play className="size-3.5 fill-current" />
                Putar
              </Button>
              <Button
                type="button"
                onClick={() => onRetry(track)}
                variant="outline"
                className="h-10 w-full gap-2 rounded-xl border-white/12 bg-white/[0.03]"
              >
                <RefreshCw className="size-4" />
                Coba lagi
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
