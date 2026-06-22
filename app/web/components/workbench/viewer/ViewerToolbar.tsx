'use client'
import { memo, useEffect, useRef } from 'react'
import { IconChevron, IconRedo, IconRemove, IconSearch, IconUndo } from '@/components/icons/Icon'

interface ViewerToolbarProps {
  searchQuery: string
  jumpError: string | null
  searchPlaceholder: string
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
export const ViewerToolbar = memo(function ViewerToolbar({
  searchQuery,
  jumpError,
  searchPlaceholder,
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
        <IconSearch />
        <input
          ref={inputRef}
          type="text"
          id="sv-search"
          placeholder={searchPlaceholder}
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
            <IconRemove size={14} />
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
          <IconChevron size={14} style={{ transform: 'rotate(90deg)' }} />
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
          <IconChevron size={14} style={{ transform: 'rotate(-90deg)' }} />
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
          <IconUndo />
          Undo
        </button>
        <button
          type="button"
          className="sv-hist-btn"
          title="Redo (⌘⇧Z)"
          disabled={!canRedo}
          onClick={onRedo}
        >
          <IconRedo />
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
              {editCount} edit{editCount === 1 ? '' : 's'}{' '}
              <IconChevron size={12} style={{ transform: showHistory ? undefined : 'rotate(-90deg)' }} />
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
})
