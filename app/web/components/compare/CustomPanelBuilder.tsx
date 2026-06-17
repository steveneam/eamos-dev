'use client'

import { useRef, useState } from 'react'
import { resolvePanel } from '@/lib/panels'
import { type CustomPanelDraft } from '@/lib/panels.mock'
import type { Panel } from '@/lib/backend'
import { IconDropInto, IconSparkle } from '@/components/icons/Icon'

/**
 * Custom gene-panel builders (spec §6.3). Both live in the Keywords tab of the
 * scope rail, stacked — same "build a panel → add as filter" job, two flavours:
 *   - KeywordPanelBuilder (Tier A, ships now): type keywords / paste gene symbols
 *     / attach a list → deterministic resolution (mock → POST /panels/resolve).
 *   - LlmPanelComingSoon (Tier B): conversational + voice, COMING SOON, gated on
 *     AskEamos funding.
 */
export function KeywordPanelBuilder({ onCreate }: { onCreate: (panel: Panel) => void }) {
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState<CustomPanelDraft | null>(null)
  const [missed, setMissed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // POST /panels/resolve (falls back to the deterministic mock resolver when
  // offline). Tokens go out as `symbols`; the disease-keyword → MONDO path
  // lands with the backend resolver.
  const generate = async () => {
    const q = query.trim()
    if (!q) return
    setBusy(true)
    setMissed(false)
    setDraft(null)
    try {
      const symbols = q.split(/[\s,;|\t\r\n]+/).filter(Boolean)
      const panel = await resolvePanel({ symbols })
      if (panel.genes.length > 0) setDraft({ panel, sources: ['/panels/resolve'] })
      else setMissed(true)
    } catch {
      setMissed(true)
    } finally {
      setBusy(false)
    }
  }

  const accept = () => {
    if (!draft) return
    onCreate(draft.panel)
    setQuery('')
    setDraft(null)
    setMissed(false)
  }

  const ingestFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result ?? '')
      setQuery((prev) => (prev.trim() ? `${prev}\n${text}` : text))
      setDraft(null)
      setMissed(false)
    }
    reader.readAsText(file)
  }

  return (
    <div>
      <textarea
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setMissed(false)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) generate()
        }}
        rows={3}
        placeholder="Type a disease or paste gene symbols, e.g. early-onset retinal dystrophy — or USH2A, ABCA4, RPE65"
        style={{
          width: '100%',
          resize: 'vertical',
          padding: '8px 10px',
          borderRadius: 8,
          border: '0.5px solid var(--line-2)',
          background: 'var(--bg)',
          fontSize: 12,
          lineHeight: 1.5,
          color: 'var(--ink)',
          fontFamily: 'inherit',
        }}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const file = e.dataTransfer.files?.[0]
          if (file) ingestFile(file)
        }}
        onClick={() => fileRef.current?.click()}
        style={{
          marginTop: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          padding: '8px 10px',
          borderRadius: 8,
          border: `1px dashed ${dragOver ? 'var(--warn-text)' : 'var(--line-2)'}`,
          background: dragOver ? 'var(--warn-tint)' : 'var(--bg-soft)',
          color: 'var(--ink-4)',
          fontSize: 11,
          cursor: 'pointer',
        }}
      >
        <IconDropInto size={13} /> Drag or attach a gene/keyword list (CSV, TSV, text)
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".csv,.tsv,.txt,.list,text/plain"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) ingestFile(file)
          e.target.value = ''
        }}
        style={{ display: 'none' }}
      />

      <button
        type="button"
        onClick={generate}
        disabled={!query.trim() || busy}
        style={{
          marginTop: 8,
          width: '100%',
          padding: '7px 12px',
          borderRadius: 8,
          border: '0.5px solid var(--ink-2)',
          background: query.trim() && !busy ? 'var(--ink-2)' : 'var(--bg-soft)',
          color: query.trim() && !busy ? '#fff' : 'var(--ink-5)',
          fontSize: 12,
          fontWeight: 600,
          cursor: query.trim() && !busy ? 'pointer' : 'not-allowed',
        }}
      >
        {busy ? 'Resolving…' : 'Generate panel'}
      </button>

      {draft && (
        <div
          style={{
            marginTop: 10,
            padding: '9px 10px',
            borderRadius: 8,
            background: 'var(--teal-tint)',
            border: '0.5px solid var(--teal-bdr)',
          }}
        >
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)' }}>{draft.panel.name}</div>
          <div style={{ fontSize: 11, color: 'var(--ink-3)', margin: '3px 0 9px', fontFamily: 'var(--mono)' }}>
            {draft.panel.genes.length} genes · from {draft.sources.join(', ')}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={accept}
              style={{
                padding: '6px 12px',
                borderRadius: 8,
                border: '0.5px solid var(--teal-deep)',
                background: 'var(--teal-deep)',
                color: '#fff',
                fontSize: 11.5,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Add as filter
            </button>
            <button
              type="button"
              onClick={() => setDraft(null)}
              style={{
                padding: '6px 12px',
                borderRadius: 8,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-3)',
                fontSize: 11.5,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {missed && (
        <p style={{ marginTop: 8, fontSize: 11.5, lineHeight: 1.5, color: 'var(--warn-text)' }}>
          Nothing resolved. Try a term like “retinal”, “cardiac”, or “cancer”, or paste known gene
          symbols (the mock resolver covers the launch panels until ClinGen/GenCC + HGNC are live).
        </p>
      )}
    </div>
  )
}

export function LlmPanelComingSoon() {
  return (
    <div
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 10,
        padding: '14px 13px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <IconSparkle size={13} />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--warn-text)' }}>Describe it in plain language</span>
      </div>
      <p style={{ fontSize: 11.5, lineHeight: 1.55, color: 'var(--ink-2)', margin: '8px 0 0' }}>
        Type or speak what you need (“early-onset retinal dystrophy, definitive genes only”) and Eamos
        drafts the panel conversationally, then refines it as you reply.
      </p>
      <div
        style={{
          marginTop: 10,
          padding: '8px 10px',
          borderRadius: 8,
          background: 'var(--bg)',
          border: '0.5px dashed var(--warn-bdr)',
          color: 'var(--ink-5)',
          fontSize: 12,
        }}
      >
        Ask Eamos…
      </div>
      <p style={{ marginTop: 10, fontSize: 10.5, fontWeight: 600, letterSpacing: '0.04em', color: 'var(--warn-text)', fontFamily: 'var(--mono)' }}>
        COMING SOON
      </p>
    </div>
  )
}
