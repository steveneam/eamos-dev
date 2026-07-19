'use client'

import type { DragEvent } from 'react'
import type { SavedVariant } from '@/lib/variant-library'
import { VariantCardRow } from './VariantCardRow'
import { IconRemove } from '@/components/icons/Icon'

/**
 * A worklist entry: <VariantCardRow> + the selection / remove chrome, matched
 * to VariantTable's selected-row vocabulary (teal-tint + 3px inset bar) so the
 * rail and the Batch table read as one family. Design §2.
 */
export interface SavedVariantCardProps {
  variant: SavedVariant
  selected: boolean
  onToggleSelect: () => void
  /** This card is the report currently on screen — a quiet "you are here" cue. */
  here?: boolean
  onOpen: () => void
  onRemove: () => void
  onOpenReport: () => void
  onOpenWorkbench?: () => void
  onOpenPaper?: () => void
  onOpenBatch: () => void
  onDragStart?: (e: DragEvent) => void
  onDragEnd?: (e: DragEvent) => void
  /** Surface-specific tooltip for the card-open action (default "Open report"). */
  openLabel?: string
}

export function SavedVariantCard({
  variant,
  selected,
  onToggleSelect,
  here,
  onOpen,
  onRemove,
  onOpenReport,
  onOpenWorkbench,
  onOpenPaper,
  onOpenBatch,
  onDragStart,
  onDragEnd,
  openLabel,
}: SavedVariantCardProps) {
  const label = `${variant.gene ?? ''} ${variant.variant ?? variant.query}`.trim()
  return (
    <div
      className="lib-card"
      data-selected={selected ? 'true' : 'false'}
      data-here={here ? 'true' : 'false'}
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    >
      <div className="lib-card-mainrow">
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
          openLabel={openLabel}
        />
        <div className="lib-card-actions">
          <button
            type="button"
            className="lib-card-remove"
            aria-label={`Remove ${label} from library`}
            title="Remove"
            onClick={onRemove}
          >
            <IconRemove size={16} />
          </button>
        </div>
      </div>
      <div className="lib-card-workflows" aria-label={`Actions for ${label}`}>
        <button type="button" onClick={onOpenReport}>Report</button>
        <button type="button" disabled={!onOpenWorkbench} onClick={onOpenWorkbench}>Workbench</button>
        <button type="button" disabled={!onOpenPaper} onClick={onOpenPaper}>Papers</button>
        <button type="button" onClick={onOpenBatch}>Batch</button>
      </div>
    </div>
  )
}
