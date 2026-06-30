'use client'

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import type { AlignReferenceResponse, SourceDisclosure } from '@/lib/backend'
import { resolveAlignReference } from '@/lib/api'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import { disclosureChipClass, disclosureView } from '@/lib/workbench/source-disclosure'
import { ReadRow } from './ReadRow'
import {
  bestOrientation,
  customReference,
  defaultReference,
  findMotif,
  readFromFile,
  readFromPaste,
  type ReadEntry,
  type ReferenceState,
} from './read-model'

interface AlignPanelProps {
  data: GeneWindowData
  gene: string
  cdna: string
  transcript?: string
}

function referenceFromResolved(response: AlignReferenceResponse): ReferenceState {
  const region = [response.genome_build, response.genomic_hg38].filter(Boolean).join(' ')
  const provenance = [response.gene, response.transcript, region].filter(Boolean).join(' / ')
  return {
    label: `${response.gene} reference window`,
    sequence: response.reference,
    provenance: provenance || null,
    targetIndex: response.target_position,
    custom: false,
  }
}

export function AlignPanel({ data, gene, cdna, transcript }: AlignPanelProps) {
  const key = `${gene}|${cdna}|${transcript ?? data.transcript}`
  return <AlignWorkspace key={key} data={data} gene={gene} cdna={cdna} transcript={transcript} />
}

function AlignWorkspace({ data, gene, cdna, transcript }: AlignPanelProps) {
  const seedReference = useMemo(() => defaultReference(data), [data])

  const [reference, setReference] = useState<ReferenceState>(seedReference)
  const [referenceSourceDisclosure, setReferenceSourceDisclosure] =
    useState<SourceDisclosure | null>(null)
  const [referenceStatus, setReferenceStatus] = useState<'resolving' | 'ready' | 'unavailable'>(
    'resolving',
  )
  const [reads, setReads] = useState<ReadEntry[]>([])
  const [addError, setAddError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [refEditing, setRefEditing] = useState(false)
  const [refDraft, setRefDraft] = useState('')
  const [refError, setRefError] = useState<string | null>(null)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [pasteDraft, setPasteDraft] = useState('')
  const [search, setSearch] = useState('')
  const [activeMatch, setActiveMatch] = useState(0)
  const [parsing, setParsing] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const referenceFallback: Partial<SourceDisclosure> = reference.custom
    ? {
        source_status: 'local_provider',
        provider_id: 'custom_alignment_reference',
        provider_label: 'Custom alignment reference',
      }
    : {
        source_status: 'local_provider',
        provider_id: 'viewer_payload_alignment_reference',
        provider_label: 'Viewer payload reference',
      }
  const referenceSource = disclosureView(referenceSourceDisclosure, referenceFallback)

  useEffect(() => {
    let stale = false
    queueMicrotask(() => {
      if (stale) return
      setReference(seedReference)
      setReferenceSourceDisclosure(null)
      setReferenceStatus('resolving')
    })
    resolveAlignReference({
      gene,
      cdna,
      transcript,
      species: 'human',
    })
      .then((resolved) => {
        if (stale) return
        const fixtureReference =
          resolved.source === 'fixture' ||
          resolved.source_disclosure?.source_status === 'fixture'
        if (!fixtureReference) setReference(referenceFromResolved(resolved))
        setReferenceSourceDisclosure(resolved.source_disclosure ?? null)
        setReferenceStatus('ready')
      })
      .catch(() => {
        if (stale) return
        setReferenceStatus('unavailable')
      })
    return () => {
      stale = true
    }
  }, [cdna, gene, seedReference, transcript])

  const matches = useMemo(() => findMotif(reference.sequence, search), [reference.sequence, search])
  const searchHits = useMemo(() => {
    const set = new Set<number>()
    for (const match of matches) {
      for (let i = match.start; i < match.start + match.length; i += 1) set.add(i)
    }
    return set
  }, [matches])
  const activeIdx = matches.length > 0 ? Math.min(activeMatch, matches.length - 1) : 0
  const activeStart = matches.length > 0 ? matches[activeIdx].start : null
  const stepMatch = (delta: number) => {
    if (matches.length === 0) return
    setActiveMatch((prev) => (prev + delta + matches.length) % matches.length)
  }

  const addFiles = useCallback(async (files: FileList | File[]) => {
    setAddError(null)
    const list = Array.from(files)
    const errors: string[] = []
    setParsing(list.length)
    try {
      for (const file of list) {
        try {
          const parsed = await readFromFile(file)
          // Auto-orient: pick the orientation that aligns better to the reference.
          const read = { ...parsed, orientation: bestOrientation(reference, parsed) }
          setReads((prev) => (prev.some((r) => r.id === read.id) ? prev : [...prev, read]))
        } catch (error) {
          errors.push(`${file.name}: ${error instanceof Error ? error.message : 'could not parse'}`)
        } finally {
          setParsing((n) => Math.max(0, n - 1))
        }
      }
    } finally {
      setParsing(0)
    }
    if (errors.length > 0) setAddError(errors.join(' · '))
  }, [reference])

  const handleDrop = async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragOver(false)
    if (event.dataTransfer.files?.length) await addFiles(event.dataTransfer.files)
  }

  const addPaste = () => {
    try {
      setReads((prev) => [...prev, readFromPaste(pasteDraft, `Pasted read ${prev.length + 1}`)])
      setPasteDraft('')
      setPasteOpen(false)
      setAddError(null)
    } catch (error) {
      setAddError(error instanceof Error ? error.message : 'Could not parse pasted sequence.')
    }
  }

  const applyCustomReference = (text: string, label?: string) => {
    try {
      setReference(customReference(text, label))
      setReferenceSourceDisclosure({
        source_status: 'local_provider',
        provider_id: 'custom_alignment_reference',
        provider_label: 'Custom alignment reference',
        source_version: null,
        cache_status: null,
        warnings: [],
        requirements: [],
      })
      setReferenceStatus('ready')
      setRefEditing(false)
      setRefDraft('')
      setRefError(null)
    } catch (error) {
      setRefError(error instanceof Error ? error.message : 'Invalid reference sequence.')
    }
  }

  const setOrientation = (id: string, orientation: ReadEntry['orientation']) =>
    setReads((prev) =>
      prev.map((read) => (read.id === id ? { ...read, orientation } : read)),
    )

  return (
    <div className="align-panel align-flow">
      <div className="tool-panel-head">
        <div>
          <h2 className="tool-panel-title">Sequence alignment</h2>
          <span className="tool-panel-sub">Reference vs Sanger reads · chromatogram view</span>
        </div>
      </div>

      {/* Reference / template */}
      <section className="align-reference">
        <div className="align-reference-head">
          <div>
            <span className="field-label">Reference / template</span>
            <b>{reference.label}</b>
            <span className="align-reference-meta">
              {reference.provenance ?? 'Custom reference'} · {reference.sequence.length} bp
            </span>
          </div>
          <div className="align-read-actions">
            {reference.custom && (
              <button
                type="button"
                className="align-read-btn"
                onClick={() => {
                  setReference(seedReference)
                  setReferenceSourceDisclosure(null)
                  setReferenceStatus('ready')
                }}
              >
                Reset to {data.gene}
              </button>
            )}
            <button
              type="button"
              className="align-read-btn"
              onClick={() => {
                setRefEditing((v) => !v)
                setRefDraft('')
                setRefError(null)
              }}
            >
              {refEditing ? 'Cancel' : 'Edit reference'}
            </button>
          </div>
        </div>
        <div className="workbench-source-line" role="note">
          <span
            className={`workbench-source-chip ${disclosureChipClass(referenceSource.status)}`}
          >
            {referenceSource.statusLabel}
          </span>
          <span>{referenceSource.providerLabel}</span>
          {referenceSource.cacheStatus && (
            <span className="workbench-source-muted">{referenceSource.cacheStatus}</span>
          )}
          {referenceStatus === 'resolving' && (
            <span className="workbench-source-muted">resolving backend reference</span>
          )}
          {referenceStatus === 'unavailable' && (
            <span className="workbench-source-muted">backend reference unavailable</span>
          )}
        </div>
        {refEditing && (
          <div className="align-ref-editor">
            <textarea
              className="align-textarea"
              value={refDraft}
              spellCheck={false}
              placeholder=">reference&#10;Paste FASTA or raw sequence…"
              onChange={(event) => setRefDraft(event.target.value)}
            />
            <div className="align-ref-editor-row">
              <label className="align-read-btn align-file-btn">
                Upload FASTA
                <input
                  type="file"
                  accept=".fasta,.fa,.fna,.txt,.seq"
                  hidden
                  onChange={async (event) => {
                    const file = event.target.files?.[0]
                    if (file) applyCustomReference(await file.text(), file.name)
                  }}
                />
              </label>
              <button
                type="button"
                className="btn-teal"
                onClick={() => applyCustomReference(refDraft)}
                disabled={!refDraft.trim()}
              >
                Use this reference
              </button>
              <span className="align-slot-hint">
                Identifier search (Entrez / Ensembl / RefSeq) is coming via the backend.
              </span>
            </div>
            {refError && (
              <div className="align-slot-error" role="alert">
                {refError}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Add reads */}
      <div
        className={`align-add${dragOver ? ' dragover' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <span className="align-add-label">
          Drop Sanger <b>.ab1</b> reads here, or
        </span>
        <button type="button" className="btn-teal" onClick={() => fileInputRef.current?.click()}>
          Choose .ab1 files
        </button>
        <button type="button" className="align-read-btn" onClick={() => setPasteOpen((v) => !v)}>
          Paste sequence
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".ab1,.abi"
          multiple
          hidden
          onChange={(event) => {
            if (event.target.files?.length) void addFiles(event.target.files)
            event.target.value = ''
          }}
        />
      </div>
      {pasteOpen && (
        <div className="align-ref-editor">
          <textarea
            className="align-textarea"
            value={pasteDraft}
            spellCheck={false}
            placeholder=">read&#10;ACGT…"
            onChange={(event) => setPasteDraft(event.target.value)}
          />
          <div className="align-ref-editor-row">
            <button type="button" className="btn-teal" onClick={addPaste} disabled={!pasteDraft.trim()}>
              Add read
            </button>
          </div>
        </div>
      )}
      {parsing > 0 && (
        <div className="align-parsing" role="status">
          <i className="align-spinner" aria-hidden="true" />
          Parsing {parsing} read{parsing > 1 ? 's' : ''}…
        </div>
      )}
      {addError && (
        <div className="align-slot-error" role="alert">
          {addError}
        </div>
      )}

      {/* Find sequence (FinchTV-style motif search) — placed right above the alignment */}
      <div className="align-find">
        <span className="field-label">Find sequence</span>
        <input
          className="field-input align-find-input"
          type="text"
          value={search}
          spellCheck={false}
          placeholder="ACGT… (searches reference, fwd + rev-comp)"
          onChange={(event) => {
            setSearch(event.target.value)
            setActiveMatch(0)
          }}
        />
        {search.trim().length >= 2 && (
          <div className="align-find-nav">
            <button type="button" className="align-nav-btn" onClick={() => stepMatch(-1)} aria-label="Previous match">
              ◀
            </button>
            <span className="align-find-count">
              {matches.length > 0 ? `${activeIdx + 1} / ${matches.length}` : 'No matches'}
            </span>
            <button type="button" className="align-nav-btn" onClick={() => stepMatch(1)} aria-label="Next match">
              ▶
            </button>
            {search && (
              <button type="button" className="align-read-btn" onClick={() => setSearch('')}>
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Reads */}
      {reads.length === 0 ? (
        <div className="align-empty">
          Drop one or more Sanger <b>.ab1</b> reads (or paste a sequence) to align against{' '}
          {reference.label}.
        </div>
      ) : (
        <>
          <div className="align-base-legend" aria-label="Base colours">
            <span className="field-label">Bases</span>
            <span className="abl A">A</span>
            <span className="abl C">C</span>
            <span className="abl G">G</span>
            <span className="abl T">T</span>
          </div>
          <div className="align-reads">
            {reads.map((read) => (
            <ReadRow
              key={read.id}
              read={read}
              reference={reference}
              searchHits={searchHits}
              activeSearchStart={activeStart}
              onSetOrientation={(orientation) => setOrientation(read.id, orientation)}
              onRemove={() => setReads((prev) => prev.filter((r) => r.id !== read.id))}
            />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
