import { Loader2, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

const SUGGESTIONS = [
  'Rex Orange County - Best Friend',
  'Tulus - Hati-Hati di Jalan',
  'The Weeknd - Blinding Lights',
  'NIKI - lowkey',
]

export function SearchBar({ value, onChange, onSubmit, loading }) {
  const submit = (event) => {
    event.preventDefault()
    onSubmit(value)
  }

  return (
    <div className="w-full">
      <form onSubmit={submit} className="w-full">
        <div
          className={cn(
            'flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.035] p-2 pl-4 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.9)] backdrop-blur',
            'transition-all duration-300 focus-within:border-primary/60 focus-within:bg-white/[0.055] focus-within:ring-4 focus-within:ring-primary/10',
          )}
        >
          <Search className="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Input
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Mis. Rex Orange County - Best Friend"
            aria-label="Cari lagu di YouTube"
            autoComplete="off"
            spellCheck="false"
            className="h-11 flex-1 border-0 bg-transparent px-0 text-[15px] shadow-none placeholder:text-muted-foreground/70 focus-visible:ring-0 dark:bg-transparent"
          />
          <Button
            type="submit"
            size="lg"
            disabled={loading || !value.trim()}
            className="gradient-primary glow-primary h-10 shrink-0 rounded-xl px-5 font-semibold text-white transition hover:brightness-110 disabled:opacity-60 sm:px-6"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                <span className="hidden sm:inline">Mencari</span>
              </>
            ) : (
              <>
                <Search className="size-4 sm:hidden" />
                <span className="hidden sm:inline">Cari</span>
              </>
            )}
          </Button>
        </div>
      </form>

      <div className="mt-3.5 flex flex-wrap gap-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSubmit(suggestion)}
            className="rounded-full border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-[11.5px] text-muted-foreground transition hover:border-primary/40 hover:bg-primary/10 hover:text-foreground"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
