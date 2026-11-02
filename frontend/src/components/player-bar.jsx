import { useEffect, useState } from 'react'
import { Download, Pause, Play, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { formatDuration } from '@/lib/format'

export function PlayerBar({ player, audioRef, onClose }) {
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [seeking, setSeeking] = useState(false)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return undefined

    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onEnded = () => {
      setPlaying(false)
      setTime(0)
    }
    const onTimeUpdate = () => {
      if (!seeking) setTime(audio.currentTime || 0)
    }
    const onLoaded = () => {
      if (Number.isFinite(audio.duration)) setDuration(audio.duration)
    }

    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('loadedmetadata', onLoaded)

    return () => {
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('loadedmetadata', onLoaded)
    }
  }, [audioRef, seeking])

  useEffect(() => {
    setTime(0)
    setDuration(player?.track?.duration || 0)
  }, [player?.key, player?.track?.duration])

  if (!player) return null

  const { track, job } = player
  const max = duration > 0 ? duration : Math.max(track.duration || 0, 1)

  const toggle = () => {
    const audio = audioRef.current
    if (!audio?.src) return
    if (audio.paused) audio.play().catch(() => {})
    else audio.pause()
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-3 sm:p-4">
      <div className="animate-float-in mx-auto flex max-w-3xl items-center gap-3 rounded-2xl border border-white/10 bg-[oklch(0.175_0.014_300/0.92)] p-2.5 shadow-[0_24px_60px_-18px_rgba(0,0,0,0.95)] backdrop-blur-xl sm:gap-4 sm:p-3">
        <img
          src={track.thumbnail}
          alt=""
          referrerPolicy="no-referrer"
          className="hidden size-12 shrink-0 rounded-lg border border-white/10 object-cover sm:block"
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <p className="truncate text-[13px] font-semibold">{track.title}</p>
            <span className="ml-auto shrink-0 text-[10.5px] tabular-nums text-muted-foreground">
              {formatDuration(time)} / {formatDuration(max)}
            </span>
          </div>

          <Slider
            className="mt-2"
            value={[Math.min(time, max)]}
            min={0}
            max={max}
            step={0.5}
            onValueChange={(value) => {
              setSeeking(true)
              setTime(value[0])
            }}
            onValueCommit={(value) => {
              const audio = audioRef.current
              if (audio) audio.currentTime = value[0]
              setSeeking(false)
              setTime(value[0])
            }}
            aria-label="Posisi lagu"
          />

          <p className="mt-1.5 truncate text-[10.5px] text-muted-foreground">
            {track.channel}
            {job?.sizeLabel
              ? ` · MP3 ${job.sizeLabel}`
              : job?.streaming
                ? ' · Streaming langsung, belum disimpan'
                : ''}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={toggle}
            aria-label={playing ? 'Pause' : 'Play'}
            className="grid size-10 place-items-center rounded-full bg-white text-black shadow transition hover:scale-105 hover:bg-white/90"
          >
            {playing ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
          </button>

          {job?.downloadUrl && (
            <Button
              asChild
              variant="ghost"
              size="icon"
              title="Download MP3"
              className="hidden text-muted-foreground hover:text-foreground sm:inline-flex"
            >
              <a href={job.downloadUrl} download={job.fileName || 'audio.mp3'}>
                <Download className="size-4" />
              </a>
            </Button>
          )}

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Tutup player"
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
