'use client'
import { useState, type FormEvent } from 'react'
import { cn } from '@/lib/utils'

interface EamosSearchProps {
  size?: 'hero' | 'compact'
  onSubmit: (query: string) => void
  className?: string
}

/**
 * The single continuous search bar — one freeform input that doubles as a
 * structured lookup and a plain-language AI query (the backend search-input
 * resolver decides which). Minimal AI-assistant styling: attach left, send
 * right. Dark tone only (the landing is dark end-to-end).
 */
export function EamosSearch({ size = 'hero', onSubmit, className }: EamosSearchProps) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const isHero = size === 'hero'

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const q = value.trim()
    if (q) onSubmit(q)
  }

  return (
    <form
      onSubmit={submit}
      data-tone="dark"
      role="search"
      aria-label="Search Eamos"
      className={cn('flex items-center', className)}
      style={{
        gap: isHero ? 8 : 6,
        background: 'var(--hero-glass2)',
        border: `0.5px solid ${focused ? 'var(--em-bright)' : 'var(--hero-line)'}`,
        borderRadius: isHero ? 18 : 999,
        padding: isHero ? '8px 8px 8px 12px' : '5px 5px 5px 12px',
        boxShadow: focused
          ? '0 24px 70px -28px rgba(0,0,0,0.7), 0 0 0 4px rgba(52,211,153,0.14), 0 0 70px -16px rgba(16,185,129,0.55)'
          : isHero
            ? '0 24px 70px -30px rgba(0,0,0,0.7), 0 0 60px -20px rgba(16,185,129,0.38)'
            : 'none',
        backdropFilter: 'blur(10px)',
        transition: 'border-color var(--dur-2) var(--ease-standard), box-shadow var(--dur-2) var(--ease-standard)',
      }}
    >
      <button
        type="button"
        aria-label="Attach a file"
        title="Attach a VCF (coming soon)"
        className="inline-flex shrink-0 items-center justify-center transition-colors"
        style={{
          width: isHero ? 38 : 30,
          height: isHero ? 38 : 30,
          borderRadius: 999,
          background: 'transparent',
          border: 'none',
          color: 'var(--hero-ink-3)',
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
        placeholder="Search a gene or variant — or just ask…"
        autoComplete="off"
        spellCheck={false}
        aria-label="Search a gene, variant, or ask a question"
        className="min-w-0 flex-1 border-none bg-transparent outline-none"
        style={{
          fontFamily: 'var(--body)',
          fontSize: isHero ? 16 : 13.5,
          color: 'var(--hero-ink)',
          padding: isHero ? '8px 0' : '6px 0',
          letterSpacing: '-0.005em',
        }}
      />

      <button
        type="submit"
        aria-label="Search"
        className="inline-flex shrink-0 items-center justify-center transition-transform"
        style={{
          width: isHero ? 40 : 32,
          height: isHero ? 40 : 32,
          borderRadius: 999,
          border: 'none',
          background: 'var(--em)',
          color: '#04140e',
          cursor: 'pointer',
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
