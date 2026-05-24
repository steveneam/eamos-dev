import { useEffect, useRef } from 'react'

interface ViewerToolbarProps {
  searchQuery: string
  jumpError: string | null
  variantCount: number
  canUndo: boolean
  canRedo: boolean
  editCount: number
  showHistory: boolean
  onSearchChange: (q: string) => void
  onJumpQuery: (q: string) => void
  onClearSearch: () => void
  onStepVariant: (dir: 'prev' | 'next') => void
  onUndo: () => void
  onRedo: () => void
  onToggleHistory: () => void
  onReset: () => void
  registerFocus: (fn: () => void) => void
}

/** Find/jump box, ClinVar variant chevrons, undo/redo + history toggle.
 *  Port of `renderToolbar()`. */
export function ViewerToolbar({
  searchQuery,
  jumpError,
  variantCount,
  canUndo,
  canRedo,
  editCount,
  showHistory,
  onSearchChange,
  onJumpQuery,
  onClearSearch,
  onStepVariant,
  onUndo,
  onRedo,
  onToggleHistory,
  onReset,
  registerFocus,
}: ViewerToolbarProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    registerFocus(() => inputRef.current?.focus())
  }, [registerFocus])

  return (
    <div className="sv-toolbar">
      <div className={`sv-find${jumpError ? ' sv-find-error' : ''}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          id="sv-search"
          placeholder="Jump to c.260 · p.Asp87 · exon 5 · GAATTC"
          autoComplete="off"
          spellCheck={false}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              onJumpQuery(searchQuery)
            } else if (e.key === 'Escape') {
              onClearSearch()
            }
          }}
        />
        {searchQuery && (
          <button type="button" className="sv-find-clear" onClick={onClearSearch} aria-label="Clear">
            ×
          </button>
        )}
        {jumpError && (
          <div className="sv-find-msg" role="alert">
            {jumpError}
          </div>
        )}
      </div>

      <div className="sv-vnav">
        <span className="sv-vnav-label">ClinVar</span>
        <button
          type="button"
          className="sv-vnav-btn"
          title="Previous variant"
          aria-label="Previous ClinVar variant"
          disabled={variantCount === 0}
          onClick={() => onStepVariant('prev')}
        >
          ‹
        </button>
        <span className="sv-vnav-count">{variantCount}</span>
        <button
          type="button"
          className="sv-vnav-btn"
          title="Next variant"
          aria-label="Next ClinVar variant"
          disabled={variantCount === 0}
          onClick={() => onStepVariant('next')}
        >
          ›
        </button>
      </div>

      <div className="sv-hist">
        <button
          type="button"
          className="sv-hist-btn"
          title="Undo (⌘Z)"
          disabled={!canUndo}
          onClick={onUndo}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 7v6h6" />
            <path d="M21 17a9 9 0 0 0-15-6.7L3 13" />
          </svg>
          Undo
        </button>
        <button
          type="button"
          className="sv-hist-btn"
          title="Redo (⌘⇧Z)"
          disabled={!canRedo}
          onClick={onRedo}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 7v6h-6" />
            <path d="M3 17a9 9 0 0 1 15-6.7L21 13" />
          </svg>
          Redo
        </button>
        {editCount > 0 ? (
          <>
            <button
              type="button"
              className={`sv-hist-toggle${showHistory ? ' on' : ''}`}
              aria-expanded={showHistory}
              onClick={onToggleHistory}
            >
              {editCount} edit{editCount === 1 ? '' : 's'} {showHistory ? '▾' : '▸'}
            </button>
            <button type="button" className="sv-hist-reset" onClick={onReset}>
              Reset
            </button>
          </>
        ) : (
          <span className="sv-hist-count">No edits</span>
        )}
      </div>
    </div>
  )
}
