'use client'
import { useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { parseVariantFile, stashCompareVariants, type ParsedVariant } from '@/lib/variant-file'
import { reportHrefForQuery } from '@/lib/variant-search'

interface EamosSearchProps {
  size?: 'hero' | 'compact'
  tone?: 'dark' | 'light'
  onSubmit: (query: string) => void
  className?: string
}

// Per-theme styling. Dark = the landing (dark end-to-end); light = the report
// page's white nav. Same shape/behaviour either way.
const TONES = {
  dark: {
    bg: 'var(--hero-glass2)',
    border: 'var(--hero-line)',
    borderFocus: 'var(--em-bright)',
    text: 'var(--hero-ink)',
    icon: 'var(--hero-ink-3)',
    send: 'var(--em)',
    sendIcon: '#04140e',
    glowFocus:
      '0 24px 70px -28px rgba(0,0,0,0.7), 0 0 0 4px rgba(52,211,153,0.14), 0 0 70px -16px rgba(16,185,129,0.55)',
    glowHero: '0 24px 70px -30px rgba(0,0,0,0.7), 0 0 60px -20px rgba(16,185,129,0.38)',
    glowHover: '0 20px 60px -28px rgba(0,0,0,0.6), 0 0 0 4px rgba(52,211,153,0.08)',
    borderHover: 'var(--hero-ink-3)',
    sendDeep: 'var(--em-deep)',
    // backdrop:none — the bg (--hero-glass2) is already opaque OKLCH, so blur
    // only buys per-keystroke repaints (mobile typing lag) with no visible gain.
    backdrop: 'none',
  },
  light: {
    bg: 'var(--bg)',
    border: 'var(--line-2)',
    borderFocus: 'var(--teal)',
    text: 'var(--ink)',
    icon: 'var(--ink-4)',
    send: 'var(--teal)',
    sendIcon: '#ffffff',
    glowFocus: '0 1px 2px rgba(15,23,42,0.04), 0 0 0 4px rgba(29,158,117,0.13)',
    glowHero: '0 12px 36px -22px rgba(15,23,42,0.22)',
    // Hover signal matches the Try pills + nav text-links: the border snaps
    // to the teal accent and a soft teal ring picks it up. Same teal axis as
    // every other interactive surface on the landing.
    glowHover: '0 8px 24px -16px rgba(15,23,42,0.18), 0 0 0 4px rgba(29,158,117,0.16)',
    borderHover: 'var(--teal)',
    sendDeep: 'var(--teal-deep)',
    backdrop: 'none',
  },
} as const

/**
 * The single continuous search bar — one freeform input that doubles as a
 * structured lookup and a plain-language AI query (the backend search-input
 * resolver decides which). Minimal AI-assistant styling: attach left, send
 * right. The placeholder softly *suggests* the gene + variant format without
 * forcing two strict fields. Shared by the landing (dark) and the report (light).
 */
export function EamosSearch({ size = 'hero', tone = 'dark', onSubmit, className }: EamosSearchProps) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [sendHover, setSendHover] = useState(false)
  const [attachHover, setAttachHover] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const isHero = size === 'hero'
  const t = TONES[tone]
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const q = value.trim()
    if (q) onSubmit(q)
  }

  // Attach a variant file (paperclip or drag-drop): parse it client-side into a
  // variant list, then route — a single variant goes straight to its report, a
  // list goes to /compare. Full VCF normalization is the batch backend's job.
  const routeVariants = (variants: ParsedVariant[], source: string) => {
    if (variants.length === 0) return
    if (variants.length === 1) {
      const href = reportHrefForQuery(variants[0].query)
      if (href) {
        router.push(href)
        return
      }
    }
    stashCompareVariants(variants, source)
    router.push('/compare')
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const seen = new Set<string>()
    const variants: ParsedVariant[] = []
    for (const file of Array.from(files)) {
      try {
        const text = await file.text()
        for (const v of parseVariantFile(text, file.name)) {
          const key = v.query.toLowerCase()
          if (seen.has(key)) continue
          seen.add(key)
          variants.push(v)
        }
      } catch {
        // Unreadable file — skip it; any other dropped files still parse.
      }
    }
    routeVariants(variants, Array.from(files).map((f) => f.name).join(', '))
  }

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    void handleFiles(e.target.files)
    e.target.value = ''
  }

  const onDrop = (e: DragEvent<HTMLFormElement>) => {
    e.preventDefault()
    setDragActive(false)
    void handleFiles(e.dataTransfer.files)
  }

  return (
    <form
      onSubmit={submit}
      data-tone={tone}
      role="search"
      aria-label="Search Eamos"
      className={cn('flex items-center', className)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onDragOver={(e) => {
        e.preventDefault()
        if (!dragActive) setDragActive(true)
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragActive(false)
      }}
      onDrop={onDrop}
      style={{
        gap: isHero ? 8 : 6,
        background: t.bg,
        border: `0.5px solid ${focused || dragActive ? t.borderFocus : hovered ? t.borderHover : t.border}`,
        borderRadius: isHero ? 18 : 999,
        padding: isHero ? '8px 8px 8px 12px' : '5px 5px 5px 12px',
        boxShadow: focused || dragActive ? t.glowFocus : hovered ? t.glowHover : isHero ? t.glowHero : 'none',
        backdropFilter: t.backdrop,
        transition:
          'border-color var(--dur-2) var(--ease-standard), box-shadow var(--dur-2) var(--ease-standard)',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".vcf,.csv,.tsv,.txt,text/plain"
        multiple
        onChange={onInputChange}
        style={{ display: 'none' }}
        aria-hidden
        tabIndex={-1}
      />
      <button
        type="button"
        aria-label="Attach a variant file"
        title="Attach a variant list — VCF, CSV, TSV, or one variant per line"
        className="inline-flex shrink-0 items-center justify-center transition-colors"
        onClick={() => fileInputRef.current?.click()}
        onMouseEnter={() => setAttachHover(true)}
        onMouseLeave={() => setAttachHover(false)}
        style={{
          width: isHero ? 38 : 30,
          height: isHero ? 38 : 30,
          borderRadius: 999,
          background: 'transparent',
          border: 'none',
          color: attachHover ? t.text : t.icon,
          cursor: 'pointer',
        }}
      >
        <PaperclipIcon />
      </button>

      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={
          dragActive
            ? 'Drop a variant file to compare'
            : isHero
              ? 'Gene, variant, or a plain question, e.g. USH2A c.2276G>T'
              : 'Gene, variant, e.g. USH2A c.2276G>T'
        }
        autoComplete="off"
        spellCheck={false}
        aria-label="Search a gene and variant, or ask a question"
        className="min-w-0 flex-1 border-none bg-transparent outline-none"
        style={{
          fontFamily: 'var(--body)',
          fontSize: isHero ? 16 : 13.5,
          color: t.text,
          padding: isHero ? '8px 0' : '6px 0',
          letterSpacing: '-0.005em',
        }}
      />

      <button
        type="submit"
        aria-label="Search"
        className="inline-flex shrink-0 items-center justify-center"
        onMouseEnter={() => setSendHover(true)}
        onMouseLeave={() => setSendHover(false)}
        style={{
          width: isHero ? 40 : 32,
          height: isHero ? 40 : 32,
          borderRadius: 999,
          border: 'none',
          background: sendHover ? t.sendDeep : t.send,
          color: t.sendIcon,
          cursor: 'pointer',
          transform: sendHover ? 'scale(1.06)' : 'scale(1)',
          transition: 'transform var(--dur-1) var(--ease-standard), background var(--dur-1) var(--ease-standard)',
        }}
      >
        <ArrowUpIcon />
      </button>
    </form>
  )
}

function PaperclipIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  )
}

function ArrowUpIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  )
}
