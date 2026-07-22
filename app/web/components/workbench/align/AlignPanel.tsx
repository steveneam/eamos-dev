'use client'

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import type {
  AlignReferenceResponse,
  SourceDisclosure,
  WorkbenchDesignContextV1,
} from '@/lib/backend'
import { resolveAlignReference } from '@/lib/api'
import { canonicalJson, sha256Hex } from '@/lib/workbench/design-context'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import { disclosureChipClass, disclosureView } from '@/lib/workbench/source-disclosure'
import type { WorkbenchDerivedResultV1 } from '@/lib/workbench/workspace'
import { ReadRow } from './ReadRow'
import {
  bestOrientation,
  analyzeRead,
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
  designContext: WorkbenchDesignContextV1 | null
  restoredResultDigest?: string
  restoredDerivedResult?: WorkbenchDerivedResultV1
  executionBlockedReason: string | null
  onResultDigest?: (digest: string, summary: WorkbenchDerivedResultV1) => void
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

export function AlignPanel(props: AlignPanelProps) {
  const { data, gene, cdna, transcript } = props
  const key = `${gene}|${cdna}|${transcript ?? data.transcript}`
  return <AlignWorkspace key={key} {...props} />
}

function downloadAlignment(filename: string, content: string, mediaType: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: `${mediaType};charset=utf-8` }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function AlignWorkspace({
  data,
  gene,
  cdna,
  transcript,
  designContext,
  restoredResultDigest,
  restoredDerivedResult,
  executionBlockedReason,
  onResultDigest,
}: AlignPanelProps) {
  const seedReference = useMemo(() => defaultReference(data), [data])

  const [reference, setReference] = useState<ReferenceState>(seedReference)
  const [referenceSourceDisclosure, setReferenceSourceDisclosure] =
    useState<SourceDisclosure | null>(null)
  const [referenceStatus, setReferenceStatus] = useState<'resolving' | 'ready' | 'unavailable' | 'cancelled'>(
    'resolving',
  )
  const [resolutionEpoch, setResolutionEpoch] = useState(0)
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
  const [resultDigest, setResultDigest] = useState<string | null>(null)
  const [resultContextDigest, setResultContextDigest] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const referenceAbortRef = useRef<AbortController | null>(null)
  const onResultDigestRef = useRef(onResultDigest)
  useEffect(() => {
    onResultDigestRef.current = onResultDigest
  }, [onResultDigest])
  const referenceFallback: Partial<SourceDisclosure> = reference.custom
    ? {
        source_status: 'local_provider',
        provider_id: 'custom_alignment_reference',
        provider_label: 'Custom alignment reference',
      }
    : {
        source_status: 'unavailable',
        provider_id: 'alignment_reference_unverified',
        provider_label: 'Unverified alignment reference',
      }
  const referenceSource = disclosureView(referenceSourceDisclosure, referenceFallback)
  const canAlign = reference.custom || referenceStatus === 'ready'

  useEffect(() => {
    const controller = new AbortController()
    referenceAbortRef.current = controller
    queueMicrotask(() => {
      if (controller.signal.aborted) return
      setReference(seedReference)
      setReferenceSourceDisclosure(null)
      setReferenceStatus(
        designContext && !executionBlockedReason ? 'resolving' : 'unavailable',
      )
    })
    if (!designContext || executionBlockedReason) {
      return () => controller.abort()
    }
    resolveAlignReference({
      gene,
      cdna,
      transcript,
      species: 'human',
      design_context: designContext,
    }, { signal: controller.signal })
      .then((resolved) => {
        if (controller.signal.aborted) return
        setReference(referenceFromResolved(resolved))
        setReferenceSourceDisclosure(resolved.source_disclosure ?? null)
        setReferenceStatus('ready')
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          setReferenceStatus('cancelled')
          return
        }
        setReferenceStatus('unavailable')
        setAddError(error instanceof Error ? error.message : 'Reference resolution failed.')
      })
    return () => {
      controller.abort()
      if (referenceAbortRef.current === controller) referenceAbortRef.current = null
    }
  }, [cdna, designContext, executionBlockedReason, gene, resolutionEpoch, seedReference, transcript])

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
    if (!canAlign) {
      setAddError('Resolve a source-backed reference or provide custom FASTA before adding reads.')
      return
    }
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
  }, [canAlign, reference])

  const handleDrop = async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragOver(false)
    if (event.dataTransfer.files?.length) await addFiles(event.dataTransfer.files)
  }

  const addPaste = () => {
    if (!canAlign) {
      setAddError('Resolve a source-backed reference or provide custom FASTA before adding reads.')
      return
    }
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

  const analyses = useMemo(
    () => reads.map((read) => ({ read, analysis: analyzeRead(reference, read, false) })),
    [reads, reference],
  )

  useEffect(() => {
    if (!canAlign || analyses.length === 0) return
    let stale = false
    const compact = analyses.map(({ read, analysis }) => ({
      source: read.source,
      orientation: read.orientation,
      identity: analysis.comparison.alignment?.identity ?? null,
      mismatch_count: analysis.realMismatch.size,
      low_quality_mismatch_count: analysis.lowQMismatch.size,
      heterozygous_peak_count: analysis.hetIndices.size,
      trimmed_bases: analysis.trimStart + (read.sequence.length - analysis.trimEnd),
    }))
    Promise.all([
      sha256Hex(reference.sequence),
      sha256Hex(canonicalJson({
        context_digest: reference.custom ? null : designContext?.context_digest ?? null,
        reference_custom: reference.custom,
        analyses: compact,
      })),
    ]).then(([referenceDigest, digest]) => {
      if (stale) return
      const identities = compact
        .map((item) => item.identity)
        .filter((value): value is number => value !== null)
      const summary: WorkbenchDerivedResultV1 = {
        schema_version: 'workbench_derived_result.v1',
        tool: 'align',
        context_digest: reference.custom ? null : designContext?.context_digest ?? null,
        result_digest: digest,
        recorded_at: new Date().toISOString(),
        title: `${analyses.length} read${analyses.length === 1 ? '' : 's'} aligned`,
        metrics: {
          read_count: analyses.length,
          reference_kind: reference.custom ? 'custom_fasta' : 'source_backed_context',
          reference_sha256: referenceDigest,
          mean_identity_percent: identities.length > 0
            ? Number((identities.reduce((sum, value) => sum + value, 0) * 100 / identities.length).toFixed(2))
            : null,
          mismatch_count: compact.reduce((sum, item) => sum + item.mismatch_count, 0),
          low_quality_mismatch_count: compact.reduce((sum, item) => sum + item.low_quality_mismatch_count, 0),
          heterozygous_peak_count: compact.reduce((sum, item) => sum + item.heterozygous_peak_count, 0),
          computation: 'browser_local_pairwise',
        },
      }
      setResultDigest(digest)
      setResultContextDigest(summary.context_digest)
      onResultDigestRef.current?.(digest, summary)
    }).catch(() => undefined)
    return () => { stale = true }
  }, [analyses, canAlign, designContext?.context_digest, reference.custom, reference.sequence])

  const resultStale = Boolean(
    resultContextDigest && resultContextDigest !== designContext?.context_digest,
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
                  setReferenceStatus('resolving')
                  setResolutionEpoch((value) => value + 1)
                }}
              >
                Resolve {data.gene} reference
              </button>
            )}
            {referenceStatus === 'resolving' ? (
              <button
                type="button"
                className="align-read-btn"
                onClick={() => referenceAbortRef.current?.abort()}
              >
                Cancel reference request
              </button>
            ) : null}
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
            <span className="workbench-source-muted">source-backed reference unavailable; use custom FASTA</span>
          )}
          {referenceStatus === 'cancelled' && (
            <span className="workbench-source-muted">reference request cancelled</span>
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
                Entrez / Ensembl / RefSeq identifier resolution is unavailable in this backend. Paste or upload the resolved FASTA.
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

      <div className="workbench-context-binding" role="note">
        {reference.custom
          ? 'Custom FASTA is aligned locally in this browser and is not persisted.'
          : designContext
            ? `Reference request bound to context ${designContext.context_digest.slice(0, 10)}. Reads and chromatogram traces remain browser-memory only.`
            : 'Exact design context is unresolved. Automatic reference resolution is disabled.'}
      </div>
      {executionBlockedReason && !reference.custom ? (
        <div className="workbench-stale" role="alert">{executionBlockedReason}</div>
      ) : null}
      {resultStale ? (
        <div className="workbench-stale" role="status">
          The retained alignment summary is stale for the current design context.
        </div>
      ) : null}
      {!resultDigest && restoredResultDigest && restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          Retained derived summary: {restoredDerivedResult.title} · result {restoredResultDigest.slice(0, 10)}. Raw reads and traces were not stored.
        </div>
      ) : null}
      {!resultDigest && restoredResultDigest && !restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          This tab retained only prior alignment identity ({restoredResultDigest.slice(0, 10)}). Add the reads again to restore analysis.
        </div>
      ) : null}

      {/* Add reads */}
      <div
        className={`align-add${dragOver ? ' dragover' : ''}${canAlign ? '' : ' disabled'}`}
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
        <button type="button" className="btn-teal" onClick={() => fileInputRef.current?.click()} disabled={!canAlign}>
          Choose .ab1 files
        </button>
        <button type="button" className="align-read-btn" onClick={() => setPasteOpen((v) => !v)} disabled={!canAlign}>
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
      {!canAlign ? (
        <div className="align-empty">
          Resolve a source-backed reference or provide custom FASTA before adding reads.
        </div>
      ) : reads.length === 0 ? (
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
          <div className="workbench-export-row" aria-label="Alignment exports">
            <button
              type="button"
              onClick={() => downloadAlignment(
                `${gene}-alignment-summary.tsv`,
                [
                  'read_number\tsource\torientation\tidentity_percent\treal_mismatches\tlow_quality_mismatches\theterozygous_peaks',
                  ...analyses.map(({ read, analysis }, index) => [
                    index + 1,
                    read.source,
                    read.orientation,
                    analysis.comparison.alignment
                      ? (analysis.comparison.alignment.identity * 100).toFixed(2)
                      : '',
                    analysis.realMismatch.size,
                    analysis.lowQMismatch.size,
                    analysis.hetIndices.size,
                  ].join('\t')),
                ].join('\n'),
                'text/tab-separated-values',
              )}
            >
              Export summary
            </button>
            <button
              type="button"
              onClick={() => downloadAlignment(
                `${gene}-alignment-manifest.json`,
                JSON.stringify({
                  schema_version: 'workbench_alignment_manifest.v1',
                  gene,
                  cdna,
                  transcript: transcript ?? data.transcript,
                  context_digest: reference.custom ? null : resultContextDigest,
                  result_digest: resultDigest,
                  reference_kind: reference.custom ? 'custom_fasta' : 'source_backed_context',
                  read_count: reads.length,
                  computation: 'browser_local_pairwise',
                  raw_inputs_persisted: false,
                  generated_at: new Date().toISOString(),
                }, null, 2),
                'application/json',
              )}
            >
              Export manifest
            </button>
          </div>
        </>
      )}
    </div>
  )
}
