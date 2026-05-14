import { useMemo, useState, type FormEvent } from 'react'
import { cn } from '@/lib/utils'
import { classify, FORMAT_HINTS } from '@/lib/variant-format'

export type SearchMode = 'lookup' | 'ai'

export interface LookupSubmit {
  mode: 'lookup'
  gene: string
  variant: string
}

export interface AiSubmit {
  mode: 'ai'
  query: string
}

export type SearchSubmit = LookupSubmit | AiSubmit

interface SearchShellProps {
  variant?: 'hero' | 'nav'
  loading?: boolean
  initialMode?: SearchMode
  initialGene?: string
  initialVariant?: string
  onSubmit: (payload: SearchSubmit) => void
  className?: string
}

const SAMPLE_CHIPS = [
  'RPE65 c.260A>G',
  'BRCA1 c.5266dupC',
  'rs6025',
  'NM_000277.3:c.1315C>T',
]

export function SearchShell({
  variant = 'hero',
  loading = false,
  initialMode = 'lookup',
  initialGene = '',
  initialVariant = '',
  onSubmit,
  className,
}: SearchShellProps) {
  const [mode, setMode] = useState<SearchMode>(initialMode)
  const [gene, setGene] = useState(initialGene)
  const [variantStr, setVariantStr] = useState(initialVariant)
  const [aiQuery, setAiQuery] = useState('')

  const combinedQuery = useMemo(
    () => (mode === 'lookup' ? `${gene} ${variantStr}`.trim() : aiQuery.trim()),
    [mode, gene, variantStr, aiQuery],
  )
  const detectedFormat = useMemo(() => classify(combinedQuery), [combinedQuery])
  const formatHint = FORMAT_HINTS[detectedFormat]

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (loading) return
    if (mode === 'lookup') {
      const g = gene.trim()
      const v = variantStr.trim()
      if (!g || !v) return
      onSubmit({ mode: 'lookup', gene: g, variant: v })
    } else {
      const q = aiQuery.trim()
      if (!q) return
      onSubmit({ mode: 'ai', query: q })
    }
  }

  const isAi = mode === 'ai'
  const isNav = variant === 'nav'

  return (
    <form
      onSubmit={handleSubmit}
      className={cn('w-full', className)}
      role="search"
      aria-label={isAi ? 'AI search' : 'Variant lookup'}
    >
      <div
        data-mode={mode}
        className="flex items-center gap-2 bg-[var(--bg)] transition-colors"
        style={{
          border: `0.5px solid ${isAi ? 'var(--ink-2)' : 'var(--line)'}`,
          borderRadius: isNav ? 100 : 14,
          padding: isNav ? '4px 6px 4px 14px' : 8,
          boxShadow: isNav ? 'none' : '0 1px 0 rgba(11,26,43,0.02), 0 8px 24px -12px rgba(11,26,43,0.08)',
        }}
      >
        <span
          aria-hidden
          className="flex shrink-0 items-center justify-center"
          style={{ width: 18, height: 18, color: isAi ? 'var(--teal)' : 'var(--ink-4)' }}
        >
          {isAi ? <SparkIcon /> : <SearchIcon />}
        </span>

        {mode === 'lookup' ? (
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <input
              type="text"
              value={gene}
              onChange={(e) => setGene(e.target.value.toUpperCase())}
              placeholder="GENE"
              autoComplete="off"
              spellCheck={false}
              className="min-w-0 flex-[0_0_88px] border-none bg-transparent outline-none"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: isNav ? 12.5 : 14,
                color: 'var(--ink)',
                padding: '8px 0',
                letterSpacing: '-0.01em',
              }}
              aria-label="Gene"
            />
            <span
              aria-hidden
              style={{ width: '0.5px', height: 22, background: 'var(--line)' }}
            />
            <input
              type="text"
              value={variantStr}
              onChange={(e) => setVariantStr(e.target.value)}
              placeholder="c.260A>G or p.Asp87Gly or rs…"
              autoComplete="off"
              spellCheck={false}
              className="min-w-0 flex-1 border-none bg-transparent outline-none"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: isNav ? 12.5 : 14,
                color: 'var(--ink)',
                padding: '8px 0',
                letterSpacing: '-0.01em',
              }}
              aria-label="Variant"
            />
          </div>
        ) : (
          <input
            type="text"
            value={aiQuery}
            onChange={(e) => setAiQuery(e.target.value)}
            placeholder="Ask Eamos about a variant, gene, or condition…"
            autoComplete="off"
            spellCheck={false}
            className="min-w-0 flex-1 border-none bg-transparent outline-none"
            style={{
              fontFamily: 'var(--body)',
              fontSize: isNav ? 13.5 : 15,
              color: 'var(--ink)',
              padding: '8px 0',
              letterSpacing: '-0.005em',
            }}
            aria-label="AI query"
          />
        )}

        <ModeToggle mode={mode} onChange={setMode} />

        <button
          type="submit"
          disabled={loading}
          aria-label="Submit"
          className="inline-flex shrink-0 items-center justify-center text-white transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style={{
            height: isNav ? 34 : 42,
            width: isNav ? 34 : undefined,
            minWidth: isNav ? 34 : 88,
            padding: isNav ? 0 : '0 18px',
            borderRadius: isNav ? 999 : 10,
            border: 'none',
            background: isAi ? 'var(--teal)' : 'var(--ink-2)',
            fontSize: 13,
            fontWeight: 600,
            fontFamily: 'var(--body)',
            gap: 6,
          }}
        >
          {isNav ? <ArrowIcon /> : <>{loading ? 'Loading…' : 'Search'}<ArrowIcon /></>}
        </button>
      </div>

      {!isNav && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span
            className="mr-1 text-[11px] font-medium uppercase tracking-[0.08em]"
            style={{ color: 'var(--ink-4)' }}
          >
            {combinedQuery ? formatHint : 'Try'}
          </span>
          {combinedQuery
            ? null
            : SAMPLE_CHIPS.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => {
                    setMode('lookup')
                    const [g, ...rest] = chip.split(' ')
                    if (rest.length > 0) {
                      setGene(g.toUpperCase())
                      setVariantStr(rest.join(' '))
                    } else {
                      setGene('')
                      setVariantStr(chip)
                    }
                  }}
                  className="inline-flex items-center gap-1.5 rounded-full transition-colors"
                  style={{
                    padding: '5px 10px',
                    background: 'var(--bg-soft)',
                    border: '0.5px solid var(--line)',
                    fontFamily: 'var(--mono)',
                    fontSize: 11,
                    color: 'var(--ink-3)',
                  }}
                >
                  <span
                    aria-hidden
                    style={{ width: 4, height: 4, borderRadius: 999, background: 'var(--ink-5)' }}
                  />
                  {chip}
                </button>
              ))}
        </div>
      )}
    </form>
  )
}

interface ModeToggleProps {
  mode: SearchMode
  onChange: (next: SearchMode) => void
}

function ModeToggle({ mode, onChange }: ModeToggleProps) {
  return (
    <div
      role="tablist"
      aria-label="Search mode"
      className="inline-flex shrink-0 items-center"
      style={{
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 999,
        padding: 2,
        gap: 2,
      }}
    >
      {(['lookup', 'ai'] as const).map((m) => {
        const pressed = mode === m
        return (
          <button
            key={m}
            type="button"
            role="tab"
            aria-pressed={pressed}
            onClick={() => onChange(m)}
            className="inline-flex items-center gap-1 rounded-full border-none transition-colors"
            style={{
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              color: pressed ? 'var(--ink)' : 'var(--ink-4)',
              background: pressed ? 'var(--bg)' : 'transparent',
              boxShadow: pressed ? '0 1px 1px rgba(11,26,43,0.06), 0 0 0 0.5px var(--line)' : 'none',
              fontFamily: 'var(--body)',
              letterSpacing: '-0.005em',
            }}
          >
            <span style={{ width: 11, height: 11, color: pressed && m === 'ai' ? 'var(--teal)' : 'currentColor' }}>
              {m === 'ai' ? <SparkIcon /> : <SearchIcon />}
            </span>
            {m === 'ai' ? 'AI' : 'Lookup'}
          </button>
        )
      })}
    </div>
  )
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" width="100%" height="100%" aria-hidden>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" width="100%" height="100%" aria-hidden>
      <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12,5 19,12 12,19" />
    </svg>
  )
}
