import { Download, Play, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDuration } from '@/lib/format'

export function LibraryGrid({ items, loading, onPlay, onDelete }) {
  if (loading && !items.length) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="space-y-2">
            <Skeleton className="aspect-square w-full rounded-xl bg-white/[0.05]" />
            <Skeleton className="h-3 w-3/4 bg-white/[0.05]" />
            <Skeleton className="h-3 w-1/2 bg-white/[0.05]" />
          </div>
        ))}
      </div>
    )
  }

  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-10 text-center">
        <p className="text-sm font-medium text-foreground/80">Belum ada lagu di koleksi</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Convert lagu pertamamu di atas — hasilnya otomatis tersimpan di sini (dan di folder{' '}
          <code className="rounded bg-white/[0.06] px-1 py-0.5 text-[11px]">downloads/</code>).
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.id}
          className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.025] transition hover:border-white/15 hover:bg-white/[0.05]"
        >
          <div className="relative aspect-square overflow-hidden bg-muted">
            <img
              src={item.thumbnail}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.04]"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-60" />

            <span className="absolute top-1.5 right-1.5 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-white/90">
              {formatDuration(item.duration)}
            </span>

            <div className="absolute inset-x-1.5 bottom-1.5 flex items-end justify-between gap-1">
              <button
                type="button"
                onClick={() => onPlay(item)}
                aria-label={`Putar ${item.title}`}
                className="grid size-9 place-items-center rounded-full bg-white text-black shadow-lg transition hover:scale-105"
              >
                <Play className="size-3.5 fill-current" />
              </button>

              <div className="flex gap-1">
                <Button
                  asChild
                  size="icon"
                  variant="secondary"
                  title="Download"
                  className="size-8 rounded-lg border border-white/10 bg-black/50 text-white backdrop-blur hover:bg-black/70"
                >
                  <a href={item.downloadUrl} download={item.fileName || 'audio.mp3'}>
                    <Download className="size-3.5" />
                  </a>
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="secondary"
                  title="Hapus dari koleksi"
                  onClick={() => onDelete(item)}
                  className="size-8 rounded-lg border border-white/10 bg-black/50 text-white backdrop-blur hover:bg-destructive/80"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            </div>
          </div>

          <div className="p-2.5">
            <p className="line-clamp-1 text-[12.5px] font-medium" title={item.title}>
              {item.title}
            </p>
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{item.channel}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
