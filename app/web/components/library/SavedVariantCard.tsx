'use client'

import type { DragEvent } from 'react'
import type { SavedVariant } from '@/lib/variant-library'
import { VariantCardRow } from './VariantCardRow'

/**
 * A worklist entry: <VariantCardRow> + the selection / pin / remove chrome,
 * matched to VariantTable's selected-row vocabulary (teal-tint + 3px inset bar)
 * so the rail and the compare table read as one family. Design §2.
 */
export interface SavedVariantCardProps {
  variant: SavedVariant
  selected: boolean
  onToggleSelect: () => void
  pinned: boolean
  onTogglePin: () => void
  /** This card is the report currently on screen — a quiet "you are here" cue. */
  here?: boolean
  onOpen: () => void
  onRemove: () => void
  onDragStart?: (e: DragEvent) => void
  onDragEnd?: (e: DragEvent) => void
}

export function SavedVariantCard({
  variant,
  selected,
  onToggleSelect,
  pinned,
  onTogglePin,
  here,
  onOpen,
  onRemove,
  onDragStart,
  onDragEnd,
}: SavedVariantCardProps) {
  const label = `${variant.gene ?? ''} ${variant.variant ?? variant.query}`.trim()
  return (
    <div
      className="lib-card"
      data-selected={selected ? 'true' : 'false'}
      data-here={here ? 'true' : 'false'}
      data-pinned={pinned ? 'true' : 'false'}
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    >
      <input
        type="checkbox"
        className="lib-card-check"
        checked={selected}
        onChange={onToggleSelect}
        aria-label={`Select ${label}`}
      />
      <VariantCardRow
        gene={variant.gene}
        hgvs={variant.variant ?? variant.query}
        classification={variant.classification}
        hgvsFull={variant.hgvs_full}
        onOpen={onOpen}
      />
      <div className="lib-card-actions">
        <button
          type="button"
          className="lib-card-pin"
          aria-pressed={pinned}
          title={pinned ? 'Unpin from compare' : 'Pin for compare'}
          onClick={onTogglePin}
        >
          ⇄
        </button>
        <button
          type="button"
          className="lib-card-remove"
          aria-label={`Remove ${label} from library`}
          title="Remove"
          onClick={onRemove}
        >
          ✕
        </button>
      </div>
    </div>
  )
}
