import { useCallback, useEffect, useState } from 'react'
import { Check, FolderOpen, FolderSearch, HardDrive, Loader2, RotateCcw, X } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  browseFolder,
  errorMessage,
  getSettings,
  openFolder,
  resetSettings,
  updateSettings,
} from '@/lib/api'
import { cn } from '@/lib/utils'

function moveSummary(result) {
  const parts = []
  if (result.moved) parts.push(`${result.moved} MP3 dipindahkan`)
  if (result.skipped) parts.push(`${result.skipped} dilewati (nama sama)`)
  if (result.moveErrors?.length) parts.push(`${result.moveErrors.length} gagal dipindah`)
  return parts.join(' · ') || result.downloadDir
}

export function SettingsDialog({ open, onClose, onSaved }) {
  const [settings, setSettings] = useState(null)
  const [path, setPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState('')
  const [moveFiles, setMoveFiles] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getSettings()
      setSettings(data)
      setPath(data.downloadDir || '')
    } catch (error) {
      toast.error('Gagal memuat pengaturan', { description: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return undefined
    setMoveFiles(true)
    load()
    return undefined
  }, [open, load])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const trimmed = path.trim()
  const changed = Boolean(settings && trimmed && trimmed !== settings.downloadDir)
  const canSave = Boolean(trimmed) && changed && !busy

  const handleBrowse = async () => {
    setBusy('browse')
    try {
      const result = await browseFolder()
      if (result.ok && result.path) {
        setPath(result.path)
      } else if (!result.canceled) {
        toast.info('Dialog folder tidak tersedia', { description: result.message })
      }
    } catch (error) {
      toast.error('Gagal membuka dialog folder', { description: errorMessage(error) })
    } finally {
      setBusy('')
    }
  }

  const handleOpen = async () => {
    setBusy('open')
    try {
      const result = await openFolder()
      if (!result.ok) toast.info(result.message || 'Tidak tersedia di sistem ini')
    } catch (error) {
      toast.error('Gagal membuka folder', { description: errorMessage(error) })
    } finally {
      setBusy('')
    }
  }

  const handleSave = async () => {
    if (!trimmed) return
    setBusy('save')
    try {
      const result = await updateSettings(trimmed, moveFiles)
      setSettings(result)
      setPath(result.downloadDir)
      onSaved?.(result)
      toast.success('Folder penyimpanan diperbarui', { description: moveSummary(result) })
    } catch (error) {
      toast.error('Gagal menyimpan folder', { description: errorMessage(error) })
    } finally {
      setBusy('')
    }
  }

  const handleReset = async () => {
    const question = moveFiles
      ? 'Kembalikan ke folder default? MP3 di folder sekarang akan dipindahkan.'
      : 'Kembalikan ke folder default? File lama tetap di folder sekarang.'
    if (!window.confirm(question)) return

    setBusy('reset')
    try {
      const result = await resetSettings()
      setSettings(result)
      setPath(result.downloadDir)
      onSaved?.(result)
      toast.success('Folder dikembalikan ke default', { description: moveSummary(result) })
    } catch (error) {
      toast.error('Gagal reset folder', { description: errorMessage(error) })
    } finally {
      setBusy('')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 backdrop-blur-sm sm:items-center"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose?.()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/10 bg-card shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] p-5">
          <div className="flex gap-3">
            <div className="gradient-primary grid size-9 shrink-0 place-items-center rounded-xl text-white">
              <HardDrive className="size-4" />
            </div>
            <div>
              <h2 id="settings-title" className="text-sm font-semibold tracking-tight">
                Folder penyimpanan
              </h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Tentukan di mana file MP3 disimpan.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-8 shrink-0 text-muted-foreground"
            onClick={onClose}
            aria-label="Tutup pengaturan"
          >
            <X className="size-4" />
          </Button>
        </div>

        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Folder aktif
              </span>
              {settings && (
                <div className="flex items-center gap-1.5">
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-muted-foreground">
                    {settings.isDefault ? 'default' : 'custom'}
                  </span>
                  <span
                    className={cn(
                      'rounded-full border px-2 py-0.5 text-[10px]',
                      settings.writable
                        ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                        : 'border-amber-400/20 bg-amber-400/10 text-amber-300',
                    )}
                  >
                    {settings.writable ? 'bisa ditulis' : 'tidak bisa ditulis'}
                  </span>
                </div>
              )}
            </div>
            <p className="mt-2 break-all font-mono text-[11.5px] leading-relaxed text-foreground/90">
              {loading && !settings ? 'Memuat…' : settings?.downloadDir || '—'}
            </p>
            {settings && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                {settings.files} file MP3 di folder ini
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="download-dir" className="text-xs font-medium">
              Path folder
            </label>
            <div className="flex gap-2">
              <Input
                id="download-dir"
                value={path}
                spellCheck={false}
                onChange={(event) => setPath(event.target.value)}
                placeholder="D:\\Music\\ytmp3"
                className="font-mono text-[12px]"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && canSave) handleSave()
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleBrowse}
                disabled={Boolean(busy)}
                className="shrink-0 gap-1.5"
              >
                {busy === 'browse' ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <FolderSearch className="size-3.5" />
                )}
                Pilih
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Gunakan path absolut. Folder dibuat otomatis kalau belum ada.
            </p>
          </div>

          <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <input
              type="checkbox"
              checked={moveFiles}
              onChange={(event) => setMoveFiles(event.target.checked)}
              className="mt-0.5 size-3.5 accent-primary"
            />
            <span className="text-[11.5px] leading-relaxed">
              <span className="font-medium text-foreground">Pindahkan MP3 lama</span>
              <span className="block text-muted-foreground">
                File yang sudah ada ikut dipindah ke folder baru. Kalau ada nama sama, file lama
                dilewati.
              </span>
            </span>
          </label>

          <div className="flex items-start gap-2 rounded-lg bg-white/[0.02] px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
            <Check className="mt-0.5 size-3.5 shrink-0 text-primary" />
            <span>
              Konversi yang sedang berjalan tetap diselesaikan di folder lamanya. Nama file di disk
              selalu <code className="rounded bg-white/[0.06] px-1 py-0.5">{'<videoId>.mp3'}</code>.
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.06] bg-white/[0.015] p-4">
          <div className="flex gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleReset}
              disabled={Boolean(busy) || !settings}
              className="gap-1.5 text-xs text-muted-foreground"
            >
              {busy === 'reset' ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RotateCcw className="size-3.5" />
              )}
              Default
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleOpen}
              disabled={Boolean(busy)}
              className="gap-1.5 text-xs text-muted-foreground"
            >
              {busy === 'open' ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <FolderOpen className="size-3.5" />
              )}
              Buka
            </Button>
          </div>

          <div className="ml-auto flex gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Tutup
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleSave}
              disabled={!canSave}
              className="gap-1.5"
            >
              {busy === 'save' ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Check className="size-3.5" />
              )}
              Simpan
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
