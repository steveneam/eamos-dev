'use client'

import { useMemo, useState, type DragEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { WorkRailSection } from '@/components/layout/WorkRail'
import { reportHrefForQuery } from '@/lib/variant-search'
import { stashCompareVariants, type ParsedVariant } from '@/lib/variant-file'
import {
  createFolder,
  moveVariant,
  removeFolder,
  removeVariant,
  renameFolder,
  type SavedVariant,
} from '@/lib/variant-library'
import { useLibrary } from './useLibrary'
import { SavedVariantCard } from './SavedVariantCard'
import {
  IconArrowRight,
  IconBookmark,
  IconChevron,
  IconDropInto,
  IconFolderMove,
  IconPin,
  IconPlus,
  IconRemove,
  IconRename,
} from '@/components/icons/Icon'
import './library.css'

/**
 * The shared cross-surface worklist block: Saved variants + Folders + Compare
 * tray, rendered as <WorkRailSection>s. Driven by useLibrary() so every surface
 * re-renders on a store change. Mounted on /report (via VariantLibraryRail) and
 * /compare (alongside ScopeGate). Design: phase-3-4-design.md §3.
 */

const DT = 'text/plain'
const TRAY_KEY = 'eamos.compare-tray.v1'

function readTray(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(TRAY_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : []
  } catch {
    return []
  }
}
function writeTray(ids: string[]): void {
  try {
    window.localStorage.setItem(TRAY_KEY, JSON.stringify(ids))
  } catch {
    // private mode / quota — ephemeral UI state, non-fatal.
  }
}

function toParsed(v: SavedVariant): ParsedVariant {
  return { raw: v.raw, gene: v.gene, variant: v.variant, query: v.query }
}

export interface LibrarySectionProps {
  /** Override the card-open behaviour per surface (default = navigate to report). */
  onOpen?: (v: SavedVariant) => void
  /** The variant currently on screen (its `query`) — marks the "you are here" card. */
  currentQuery?: string
  /** Surface-specific tooltip for opening a card (default "Open report"; /workbench loads the viewer). */
  openLabel?: string
}

export function LibrarySection({ onOpen, currentQuery, openLabel }: LibrarySectionProps) {
  const router = useRouter()
  const { variants, folders } = useLibrary()

  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [pinned, setPinned] = useState<Set<string>>(() => new Set(readTray()))
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(() => new Set())
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null)
  const [newFolderOpen, setNewFolderOpen] = useState(false)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [moveMenuOpen, setMoveMenuOpen] = useState(false)

  const hereId = currentQuery ? currentQuery.toLowerCase() : null

  const topLevel = useMemo(
    () => variants.filter((v) => !v.folderId).sort((a, b) => b.savedAt - a.savedAt),
    [variants],
  )
  const byFolder = useMemo(() => {
    const map = new Map<string, SavedVariant[]>()
    for (const f of folders) map.set(f.id, [])
    for (const v of variants) if (v.folderId && map.has(v.folderId)) map.get(v.folderId)!.push(v)
    for (const list of map.values()) list.sort((a, b) => b.savedAt - a.savedAt)
    return map
  }, [variants, folders])

  const open = (v: SavedVariant) => {
    if (onOpen) return onOpen(v)
    const href = reportHrefForQuery(v.query)
    if (href) router.push(href)
  }

  const toggleSelect = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  const clearSelection = () => setSelected(new Set())

  const updatePinned = (next: Set<string>) => {
    setPinned(next)
    writeTray([...next])
  }
  const togglePin = (id: string) => {
    const next = new Set(pinned)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    updatePinned(next)
  }
  const pinSelected = () => {
    const next = new Set(pinned)
    for (const id of selected) next.add(id)
    updatePinned(next)
    clearSelection()
  }

  const moveSelectedTo = (folderId: string | null) => {
    for (const id of selected) moveVariant(id, folderId)
    clearSelection()
    setMoveMenuOpen(false)
  }

  // --- DnD: drag a card (or the whole selection) onto a folder header ---
  const dragIdsFor = (id: string): string[] =>
    selected.has(id) && selected.size > 0 ? [...selected] : [id]
  const onCardDragStart = (id: string) => (e: DragEvent) => {
    e.dataTransfer.setData(DT, JSON.stringify({ ids: dragIdsFor(id) }))
    e.dataTransfer.effectAllowed = 'move'
  }
  const onFolderDrop = (folderId: string) => (e: DragEvent) => {
    e.preventDefault()
    setDragOverFolder(null)
    try {
      const { ids } = JSON.parse(e.dataTransfer.getData(DT)) as { ids: string[] }
      for (const id of ids) moveVariant(id, folderId)
      clearSelection()
    } catch {
      // not a card payload — ignore
    }
  }

  const removeOne = (id: string) => {
    removeVariant(id)
    if (pinned.has(id)) {
      const next = new Set(pinned)
      next.delete(id)
      updatePinned(next)
    }
  }

  const commitNewFolder = (name: string) => {
    if (name.trim()) createFolder(name)
    setNewFolderOpen(false)
  }

  // Compare tray: resolve pinned ids → live variants (prune stale ids defensively).
  const pinnedVariants = useMemo(
    () => [...pinned].map((id) => variants.find((v) => v.id === id)).filter((v): v is SavedVariant => Boolean(v)),
    [pinned, variants],
  )
  const openInCompare = () => {
    if (pinnedVariants.length < 2) return
    stashCompareVariants(pinnedVariants.map(toParsed), 'Compare tray')
    router.push('/compare')
  }

  const renderCard = (v: SavedVariant) => (
    <SavedVariantCard
      key={v.id}
      variant={v}
      selected={selected.has(v.id)}
      onToggleSelect={() => toggleSelect(v.id)}
      pinned={pinned.has(v.id)}
      onTogglePin={() => togglePin(v.id)}
      here={hereId === v.id}
      onOpen={() => open(v)}
      onRemove={() => removeOne(v.id)}
      onDragStart={onCardDragStart(v.id)}
      openLabel={openLabel}
    />
  )

  return (
    <>
      <WorkRailSection title="Saved variants" meta={topLevel.length}>
        <div className="lib-secbar">
          <Link href="/compare">Import VCF <IconArrowRight size={12} /></Link>
        </div>

        {variants.length === 0 ? (
          <div className="lib-empty">
            <span className="lib-empty-glyph" aria-hidden><IconBookmark size={18} /></span>
            <strong>No saved variants yet.</strong>
            <p>
              Save the variant you’re viewing, or <Link href="/compare">import a VCF in Compare</Link> to
              build a worklist.
            </p>
          </div>
        ) : (
          <div className="lib-list">{topLevel.map(renderCard)}</div>
        )}

        {selected.size > 0 && (
          <div className="lib-seltoolbar">
            <span className="lib-seltoolbar-count">{selected.size} selected</span>
            <div className="lib-seltoolbar-actions">
              <button type="button" onClick={() => setMoveMenuOpen((o) => !o)} aria-expanded={moveMenuOpen}>
                <IconFolderMove size={14} /> Move to folder
              </button>
              <button type="button" onClick={pinSelected}>
                <IconPin size={14} /> Pin
              </button>
              <button type="button" className="seltoolbar-clear" onClick={clearSelection} aria-label="Clear selection">
                <IconRemove size={14} />
              </button>
              {moveMenuOpen && (
                <div className="lib-folder-menu" role="menu">
                  {folders.length === 0 ? (
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        const f = createFolder('New folder')
                        if (f) moveSelectedTo(f.id)
                      }}
                    >
                      New folder…
                    </button>
                  ) : (
                    <>
                      {folders.map((f) => (
                        <button key={f.id} type="button" role="menuitem" onClick={() => moveSelectedTo(f.id)}>
                          {f.name}
                        </button>
                      ))}
                      <button type="button" role="menuitem" onClick={() => moveSelectedTo(null)}>
                        — Top level
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </WorkRailSection>

      <WorkRailSection title="Folders" meta={folders.length}>
        {folders.map((f) => {
          const isOpen = !collapsedFolders.has(f.id)
          const cards = byFolder.get(f.id) ?? []
          return (
            <div
              key={f.id}
              className="lib-folder"
              data-open={isOpen ? 'true' : 'false'}
              data-dragover={dragOverFolder === f.id ? 'true' : 'false'}
            >
              {confirmDelete === f.id ? (
                <div className="lib-folder-confirm">
                  <span>Delete folder? Its variants move to Saved.</span>
                  <button type="button" className="confirm-cancel" onClick={() => setConfirmDelete(null)}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="confirm-del"
                    onClick={() => {
                      removeFolder(f.id)
                      setConfirmDelete(null)
                    }}
                  >
                    Delete
                  </button>
                </div>
              ) : renaming === f.id ? (
                <input
                  className="lib-folder-input"
                  autoFocus
                  defaultValue={f.name}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      renameFolder(f.id, (e.target as HTMLInputElement).value)
                      setRenaming(null)
                    } else if (e.key === 'Escape') {
                      setRenaming(null)
                    }
                  }}
                  onBlur={(e) => {
                    renameFolder(f.id, e.target.value)
                    setRenaming(null)
                  }}
                />
              ) : (
                <div
                  className="lib-folder-head"
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragOverFolder(f.id)
                  }}
                  onDragLeave={(e) => {
                    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragOverFolder(null)
                  }}
                  onDrop={onFolderDrop(f.id)}
                >
                  <button
                    type="button"
                    className="lib-folder-toggle"
                    onClick={() =>
                      setCollapsedFolders((prev) => {
                        const next = new Set(prev)
                        if (next.has(f.id)) next.delete(f.id)
                        else next.add(f.id)
                        return next
                      })
                    }
                  >
                    <span className="lib-folder-chev" aria-hidden>
                      {dragOverFolder === f.id ? <IconDropInto size={14} /> : <IconChevron size={12} />}
                    </span>
                    <span className="lib-folder-name">{f.name}</span>
                    <span className="lib-count">{cards.length}</span>
                  </button>
                  <div className="lib-folder-actions">
                    <button type="button" title="Rename folder" aria-label={`Rename ${f.name}`} onClick={() => setRenaming(f.id)}>
                      <IconRename size={14} />
                    </button>
                    <button
                      type="button"
                      className="danger"
                      title="Delete folder"
                      aria-label={`Delete ${f.name}`}
                      onClick={() => setConfirmDelete(f.id)}
                    >
                      <IconRemove size={14} />
                    </button>
                  </div>
                </div>
              )}
              <div className="lib-folder-body">
                <div className="lib-folder-cards">{cards.map(renderCard)}</div>
              </div>
            </div>
          )
        })}

        {newFolderOpen ? (
          <input
            className="lib-folder-input"
            autoFocus
            placeholder="Folder name"
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitNewFolder((e.target as HTMLInputElement).value)
              else if (e.key === 'Escape') setNewFolderOpen(false)
            }}
            onBlur={(e) => commitNewFolder(e.target.value)}
          />
        ) : (
          <button type="button" className="lib-newfolder" onClick={() => setNewFolderOpen(true)}>
            <IconPlus size={13} /> New folder
          </button>
        )}
      </WorkRailSection>

      <WorkRailSection title="Compare tray" meta={pinnedVariants.length}>
        {pinnedVariants.length === 0 ? (
          <p className="lib-tray-empty">Pin 2 or more saved variants to line them up in Compare.</p>
        ) : (
          <div className="lib-tray">
            {pinnedVariants.map((v) => (
              <span key={v.id} className="lib-pin-chip">
                {v.gene ?? v.query}
                {v.variant ? ` ${v.variant}` : ''}
                <button type="button" aria-label={`Unpin ${v.gene ?? v.query}`} onClick={() => togglePin(v.id)}>
                  <IconRemove size={11} />
                </button>
              </span>
            ))}
          </div>
        )}
        <button
          type="button"
          className="lib-tray-open"
          disabled={pinnedVariants.length < 2}
          title={pinnedVariants.length < 2 ? 'Pin at least 2 variants' : undefined}
          onClick={openInCompare}
        >
          Open in Compare <IconArrowRight size={12} />
        </button>
      </WorkRailSection>
    </>
  )
}
