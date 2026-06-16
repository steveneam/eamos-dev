'use client'

import { useRef, useState, type DragEvent } from 'react'
import { parseVariantFile, type ParsedVariant } from '@/lib/variant-file'
import { IconDropInto, IconPlus } from '@/components/icons/Icon'

/**
 * In-page variant import for /compare — drop / browse / paste a VCF or variant
 * list without leaving the Batch surface. Reuses the search bar's parse + dedup
 * (parseVariantFile from lib/variant-file), so the attach grammar is identical;
 * only the routing differs (the search bar redirects, here we populate in place).
 *
 *   - `block`   (empty state): the hero dropzone + Browse + an optional paste box.
 *   - `compact` (loaded state): a small "Add file" button that merges another
 *                file into the current cohort.
 */

const ACCEPT = '.vcf,.csv,.tsv,.txt,text/plain'

/** Parse one or more files into a single deduped variant list (same dedup the
 *  search bar applies across multiple dropped files). */
async function parseFiles(files: FileList | File[]): Promise<{ variants: ParsedVariant[]; source: string }> {
  const arr = Array.from(files)
  const seen = new Set<string>()
  const variants: ParsedVariant[] = []
  for (const file of arr) {
    try {
      const text = await file.text()
      for (const v of parseVariantFile(text, file.name)) {
        const key = v.query.toLowerCase()
        if (seen.has(key)) continue
        seen.add(key)
        variants.push(v)
      }
    } catch {
      // Unreadable file — skip it; any other selected files still parse.
    }
  }
  return { variants, source: arr.map((f) => f.name).join(', ') }
}

export function VariantImport({
  onVariants,
  compact = false,
}: {
  /** Called with the parsed (deduped) variants + a source label for the stash. */
  onVariants: (variants: ParsedVariant[], source: string) => void
  compact?: boolean
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragActive, setDragActive] = useState(false)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [note, setNote] = useState<string | null>(null)

  const ingest = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const { variants, source } = await parseFiles(files)
    if (variants.length === 0) {
      setNote('No variants found in that file — expected a VCF, or one variant per line.')
      return
    }
    setNote(null)
    onVariants(variants, source)
  }

  const loadPasted = () => {
    const text = pasteText.trim()
    if (!text) return
    const variants = parseVariantFile(text, 'pasted-list.txt')
    if (variants.length === 0) {
      setNote('Couldn’t parse that text — expected a VCF body, or one variant per line.')
      return
    }
    setNote(null)
    setPasteText('')
    setPasteOpen(false)
    onVariants(variants, 'pasted list')
  }

  // Shared hidden file input for both variants.
  const fileInput = (
    <input
      ref={fileInputRef}
      type="file"
      accept={ACCEPT}
      multiple
      onChange={(e) => {
        void ingest(e.target.files)
        e.target.value = ''
      }}
      style={{ display: 'none' }}
      aria-hidden
      tabIndex={-1}
    />
  )

  if (compact) {
    return (
      <>
        {fileInput}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Add variants from another file to this cohort"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '5px 10px',
            borderRadius: 9,
            border: '0.5px solid var(--line-2)',
            background: 'var(--bg)',
            color: 'var(--ink-2)',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <IconPlus size={12} /> Add file
        </button>
      </>
    )
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
    void ingest(e.dataTransfer.files)
  }

  return (
    <div>
      {fileInput}
      <div
        role="button"
        tabIndex={0}
        aria-label="Drop a variant file or browse"
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            fileInputRef.current?.click()
          }
        }}
        onDragOver={(e) => {
          e.preventDefault()
          if (!dragActive) setDragActive(true)
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragActive(false)
        }}
        onDrop={onDrop}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: 10,
          padding: '34px 28px',
          borderRadius: 14,
          border: dragActive ? '1.5px solid var(--teal)' : '1.5px dashed var(--line-2)',
          background: dragActive ? 'var(--teal-tint)' : 'var(--bg-soft)',
          cursor: 'pointer',
          transform: dragActive ? 'scale(1.005)' : 'scale(1)',
          transition: 'border-color .15s ease, background .15s ease, transform .15s ease',
        }}
      >
        <span
          aria-hidden
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 42,
            height: 42,
            borderRadius: 999,
            background: dragActive ? 'var(--teal)' : 'var(--bg)',
            border: '0.5px solid var(--line)',
            color: dragActive ? '#fff' : 'var(--teal-deep)',
          }}
        >
          <IconDropInto size={19} />
        </span>
        <div>
          <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>
            {dragActive ? 'Drop to load these variants' : 'Drop a variant file, or browse'}
          </p>
          <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: '5px 0 0' }}>
            VCF, CSV, TSV, or a plain-text list — one variant per line.
          </p>
        </div>
        <span className="cmp-cta cmp-cta--solid" style={{ padding: '8px 18px', fontSize: 13, pointerEvents: 'none' }}>
          Browse files
        </span>
      </div>

      <div style={{ textAlign: 'center', marginTop: 12 }}>
        <button
          type="button"
          onClick={() => setPasteOpen((o) => !o)}
          aria-expanded={pasteOpen}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            color: 'var(--ink-4)',
            fontSize: 12.5,
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          {pasteOpen ? 'Hide paste box' : 'or paste a list of variants'}
        </button>
      </div>

      {pasteOpen && (
        <div style={{ marginTop: 10 }}>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder={'RPE65 c.260A>G\nABCA4 p.Gly1961Glu\n1-94002271-A-G'}
            rows={5}
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: 10,
              border: '0.5px solid var(--line-2)',
              background: 'var(--bg)',
              fontSize: 12.5,
              fontFamily: 'var(--mono)',
              color: 'var(--ink)',
              resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
            <button
              type="button"
              onClick={loadPasted}
              disabled={!pasteText.trim()}
              className="cmp-cta cmp-cta--solid"
              style={{ padding: '7px 16px', fontSize: 13, opacity: pasteText.trim() ? 1 : 0.5 }}
            >
              Load list →
            </button>
          </div>
        </div>
      )}

      {note && (
        <p style={{ fontSize: 12, color: 'var(--err)', textAlign: 'center', margin: '10px 0 0' }} role="alert">
          {note}
        </p>
      )}
    </div>
  )
}
