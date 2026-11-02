import { useCallback, useEffect, useRef, useState } from 'react'
import { Library, Music4, RefreshCw, SearchX, Settings, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { LibraryGrid } from '@/components/library-grid'
import { PlayerBar } from '@/components/player-bar'
import { SearchBar } from '@/components/search-bar'
import { SettingsDialog } from '@/components/settings-dialog'
import { StatusPill } from '@/components/status-pill'
import { TrackCard } from '@/components/track-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Toaster } from '@/components/ui/sonner'
import {
  cancelJob,
  convertTrack,
  deleteLibraryItem,
  errorMessage,
  getHealth,
  getJob,
  getLibrary,
  openFolder,
  searchTracks,
  streamUrl,
} from '@/lib/api'

const ACTIVE = new Set(['queued', 'downloading', 'converting'])
const isActive = (job) => Boolean(job && ACTIVE.has(job.status))

function ResultsSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="flex gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
        >
          <Skeleton className="hidden aspect-video w-[168px] rounded-lg bg-white/[0.05] sm:block" />
          <div className="flex-1 space-y-2.5 py-1">
            <Skeleton className="h-4 w-3/4 bg-white/[0.05]" />
            <Skeleton className="h-3 w-1/3 bg-white/[0.05]" />
          </div>
          <Skeleton className="hidden h-10 w-[142px] rounded-xl bg-white/[0.05] sm:block" />
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [lastQuery, setLastQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searched, setSearched] = useState(false)
  const [results, setResults] = useState([])
  const [jobs, setJobs] = useState({})
  const [library, setLibrary] = useState([])
  const [libraryLoading, setLibraryLoading] = useState(true)
  const [health, setHealth] = useState(null)
  const [offline, setOffline] = useState(false)
  const [player, setPlayer] = useState(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const audioRef = useRef(null)
  const jobsRef = useRef(jobs)
  jobsRef.current = jobs
  const notifiedRef = useRef(new Set())

  /* ---------------- health ---------------- */
  useEffect(() => {
    let alive = true
    const check = async () => {
      try {
        const data = await getHealth()
        if (!alive) return
        setHealth(data)
        setOffline(false)
      } catch {
        if (alive) setOffline(true)
      }
    }
    check()
    const timer = setInterval(check, 30_000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  /* ---------------- library ---------------- */
  const loadLibrary = useCallback(async () => {
    try {
      const data = await getLibrary()
      const items = data.items || []
      setLibrary(items)
      // lagu yang sudah ada di koleksi langsung tampil sebagai siap diputar
      setJobs((previous) => {
        const next = { ...previous }
        for (const item of items) {
          if (!next[item.id]) next[item.id] = item
        }
        return next
      })
    } catch {
      /* diamkan, status server sudah terlihat di header */
    } finally {
      setLibraryLoading(false)
    }
  }, [])

  useEffect(() => {
    loadLibrary()
  }, [loadLibrary])

  /* ---------------- polling job ---------------- */
  const hasActive = Object.values(jobs).some(isActive)

  useEffect(() => {
    if (!hasActive) return undefined

    let stopped = false

    const tick = async () => {
      const ids = Object.values(jobsRef.current).filter(isActive).map((job) => job.id)
      if (!ids.length) return

      const settled = await Promise.allSettled(ids.map((id) => getJob(id)))
      if (stopped) return

      const updates = {}
      let becameReady = false

      for (const entry of settled) {
        if (entry.status !== 'fulfilled') continue
        const job = entry.value
        const previous = jobsRef.current[job.id]
        updates[job.id] = job

        if (job.status === 'ready' && previous?.status !== 'ready') {
          becameReady = true
          if (!notifiedRef.current.has(job.id)) {
            notifiedRef.current.add(job.id)
            toast.success('MP3 siap diunduh', { description: job.title })
          }
        }

        if (
          job.status === 'error' &&
          previous?.status !== 'error' &&
          job.error &&
          job.error !== 'Dibatalkan'
        ) {
          toast.error('Konversi gagal', { description: job.error })
        }
      }

      if (Object.keys(updates).length) {
        setJobs((previous) => ({ ...previous, ...updates }))
      }
      if (becameReady) loadLibrary()
    }

    tick()
    const timer = setInterval(tick, 900)
    return () => {
      stopped = true
      clearInterval(timer)
    }
  }, [hasActive, loadLibrary])

  /* ---------------- audio source ---------------- */
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !player?.job?.mediaUrl) return

    audio.src = player.job.mediaUrl
    audio.load()

    if (player.autoplay) {
      audio.play().catch(() => {
        toast.info('Tekan tombol play untuk memutar')
      })
    }
  }, [player])

  /* ---------------- actions ---------------- */
  const runSearch = async (value) => {
    const clean = String(value ?? query).trim()
    if (!clean || searching) return

    setQuery(clean)
    setLastQuery(clean)
    setSearched(true)
    setSearching(true)

    try {
      const data = await searchTracks(clean)
      const items = data.results || []
      setResults(items)

      // hasil yang filenya sudah ada langsung ditandai ready
      const cached = {}
      for (const item of items) {
        if (!item.cached) continue
        cached[item.id] = {
          ...item,
          status: 'ready',
          progress: 100,
          message: 'Sudah tersedia',
          error: null,
          cached: true,
          mediaUrl: `/api/media/${item.id}`,
          downloadUrl: `/api/media/${item.id}?download=1`,
        }
      }
      if (Object.keys(cached).length) {
        setJobs((previous) => {
          const next = { ...previous }
          for (const [id, job] of Object.entries(cached)) {
            if (!next[id] || !ACTIVE.has(next[id].status)) next[id] = job
          }
          return next
        })
      }

      if (!items.length) {
        toast.info('Tidak ada hasil', { description: 'Coba kata kunci lain atau tempel link YouTube.' })
      }
    } catch (error) {
      setResults([])
      toast.error('Pencarian gagal', { description: errorMessage(error) })
    } finally {
      setSearching(false)
    }
  }

  const handleConvert = async (track) => {
    notifiedRef.current.delete(track.id)
    try {
      const job = await convertTrack(track)
      setJobs((previous) => ({ ...previous, [job.id]: job }))

      if (job.status === 'ready') {
        toast.success('Sudah tersedia', { description: 'File MP3 sudah ada di koleksi.' })
        loadLibrary()
      }
    } catch (error) {
      toast.error('Gagal memulai konversi', { description: errorMessage(error) })
    }
  }

  const handleCancel = async (track) => {
    try {
      const job = await cancelJob(track.id)
      setJobs((previous) => ({ ...previous, [job.id]: job }))
      toast.info('Konversi dibatalkan')
    } catch (error) {
      toast.error('Gagal membatalkan', { description: errorMessage(error) })
    }
  }

  const handleOpenFolder = async (track) => {
    try {
      const response = await openFolder(track.id)
      if (!response.ok) toast.info(response.message || 'Tidak tersedia di sistem ini')
    } catch (error) {
      toast.error('Gagal membuka folder', { description: errorMessage(error) })
    }
  }

  const handlePlay = (track, job) => {
    const audio = audioRef.current
    // file MP3 yang sudah ada dipakai dulu; kalau belum, stream langsung dari YouTube
    const mediaUrl = job?.mediaUrl || streamUrl(track.id)
    if (!mediaUrl) return

    if (player?.track?.id === track.id && player?.job?.mediaUrl === mediaUrl && audio) {
      if (audio.paused) audio.play().catch(() => {})
      else audio.pause()
      return
    }

    const activeJob = job?.mediaUrl
      ? job
      : { ...track, mediaUrl, status: 'stream', streaming: true }

    setPlayer({ track, job: activeJob, autoplay: true, key: Date.now() })
  }

  const closePlayer = () => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.removeAttribute('src')
      audio.load()
    }
    setPlayer(null)
  }

  const handleDelete = async (item) => {
    if (!window.confirm(`Hapus "${item.title}" dari koleksi dan dari disk?`)) return
    try {
      await deleteLibraryItem(item.id)
      setLibrary((previous) => previous.filter((entry) => entry.id !== item.id))
      setJobs((previous) => {
        const next = { ...previous }
        delete next[item.id]
        return next
      })
      notifiedRef.current.delete(item.id)
      if (player?.track?.id === item.id) closePlayer()
      toast.success('Lagu dihapus', { description: item.title })
    } catch (error) {
      toast.error('Gagal menghapus', { description: errorMessage(error) })
    }
  }

  const handleSettingsSaved = (result) => {
    setHealth((previous) =>
      previous ? { ...previous, downloadDir: result.downloadDir } : previous,
    )
    loadLibrary()
  }

  const downloadDir = health?.downloadDir || ''
  const folderLabel = downloadDir.split(/[\\/]/).filter(Boolean).pop() || 'downloads'

  /* ---------------- render ---------------- */
  return (
    <div className="relative min-h-screen">
      <div className="app-glow" />

      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="gradient-primary glow-primary grid size-9 place-items-center rounded-xl text-white">
              <Music4 className="size-4.5" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-bold tracking-tight">
                ytmp3<span className="text-primary">.</span>scrapper
              </p>
              <p className="text-[9.5px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
                YouTube to MP3
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <StatusPill health={health} offline={offline} />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-9 text-muted-foreground hover:text-foreground"
              onClick={() => setSettingsOpen(true)}
              aria-label="Pengaturan folder penyimpanan"
              title="Folder penyimpanan"
            >
              <Settings className="size-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-44 sm:px-6">
        {/* hero */}
        <section className="pt-12 sm:pt-20">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px] text-muted-foreground">
            <Sparkles className="size-3 text-primary" />
            {health?.ytdlp ? `engine yt-dlp ${health.ytdlp}` : 'engine siap dipakai'}
          </div>

          <h1 className="mt-6 max-w-3xl text-[38px] font-extrabold leading-[1.04] tracking-tight sm:text-6xl">
            Cari lagu,{' '}
            <br className="hidden sm:block" />
            <span className="gradient-text">jadi MP3</span> dalam sekejap.
          </h1>

          <p className="mt-4 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-[15px]">
            Tulis judul lagu atau tempel link YouTube. Ambil 1–5 hasil, convert ke MP3, preview
            langsung di browser, lalu download — semua dari satu halaman.
          </p>

          <div className="mt-8 max-w-2xl">
            <SearchBar value={query} onChange={setQuery} onSubmit={runSearch} loading={searching} />
          </div>
        </section>

        {/* hasil pencarian */}
        {searched && (
          <section className="mt-14">
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">Hasil pencarian</h2>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {searching
                    ? 'Mencari di YouTube…'
                    : results.length
                      ? `${results.length} hasil untuk “${lastQuery}”`
                      : 'Tidak ada hasil'}
                </p>
              </div>
              {results.length > 0 && (
                <Badge variant="secondary" className="shrink-0 tabular-nums">
                  {results.length}/5
                </Badge>
              )}
            </div>

            {searching ? (
              <ResultsSkeleton />
            ) : results.length ? (
              <div className="space-y-3">
                {results.map((track, index) => (
                  <TrackCard
                    key={track.id}
                    track={track}
                    job={jobs[track.id]}
                    index={index}
                    onConvert={handleConvert}
                    onRetry={handleConvert}
                    onCancel={handleCancel}
                    onPlay={handlePlay}
                    onOpenFolder={handleOpenFolder}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-12 text-center">
                <SearchX className="mx-auto size-7 text-muted-foreground/60" />
                <p className="mt-3 text-sm font-medium">Lagu tidak ditemukan</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Coba ejaan lain, tambahkan nama artis, atau tempel link YouTube langsung.
                </p>
              </div>
            )}
          </section>
        )}

        {/* koleksi */}
        <section className="mt-16">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
                <Library className="size-4 text-primary" />
                Koleksi kamu
              </h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {library.length > 0
                  ? `${library.length} lagu tersimpan di folder ${folderLabel}/`
                  : 'Lagu yang sudah di-convert akan muncul di sini'}
              </p>
            </div>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={loadLibrary}
              className="shrink-0 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <RefreshCw className="size-3.5" />
              Refresh
            </Button>
          </div>

          <LibraryGrid
            items={library}
            loading={libraryLoading}
            onPlay={(item) => handlePlay(item, item)}
            onDelete={handleDelete}
          />
        </section>

        <footer className="mt-16 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.06] pt-5 text-[11.5px] text-muted-foreground">
          <span className="min-w-0">
            MP3 disimpan di{' '}
            <code
              className="rounded bg-white/[0.06] px-1.5 py-0.5 text-[11px]"
              title={downloadDir || undefined}
            >
              {folderLabel}/
            </code>
          </span>
          <span>Dipakai untuk keperluan pribadi. Hormati hak cipta.</span>
        </footer>
      </main>

      <audio ref={audioRef} preload="metadata" className="hidden" />
      <PlayerBar player={player} audioRef={audioRef} onClose={closePlayer} />
      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={handleSettingsSaved}
      />
      <Toaster />
    </div>
  )
}
