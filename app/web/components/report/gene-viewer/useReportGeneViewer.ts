'use client'

import { useEffect, useMemo, useState } from 'react'

import { getGeneViewer } from '@/lib/api'
import type {
  GeneContextSnapshot,
  GeneViewerResponse,
  ProteinAlphaMissenseHeatmap,
  ProteinDomainTrack,
} from '@/lib/backend'
import { adaptGeneViewer, geneViewerScaffoldWarnings } from '@/lib/workbench/gene-viewer-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'
import type { GeneWindowData } from '@/lib/workbench/gene-window'

import { adaptGeneContextSnapshot } from './reportGeneViewerAdapter'

export interface ReportGeneViewerControllerInput {
  gene: string
  cdna: string
  transcript?: string | null
  initialData?: GeneWindowData | null
  geneContextSnapshot?: GeneContextSnapshot | null
  proteinDomainTrack?: ProteinDomainTrack | null
  markerClassification?: string | null
  /** Offline fixture mode: render from the bundled GENE_VIEWER_SAMPLE without
   * a network call, matching the explicit fixture report. */
  demo?: boolean
}

function warningsForViewer(response: GeneViewerResponse): string[] {
  const trackWarnings = response.tracks.protein_features.domain_track?.warnings ?? []
  const alphamissenseWarnings = response.tracks.alphamissense_heatmap?.warnings ?? []
  return Array.from(
    new Set([
      ...geneViewerScaffoldWarnings(response),
      ...trackWarnings,
      ...alphamissenseWarnings,
    ]),
  )
}

export function viewerFetchWarning(error: Error): string {
  const message = error.message.trim().replace(/\s+/g, ' ')
  return `gene_viewer_live_request_failed:${message || error.name || 'unknown_error'}`
}

export function shouldFetchViewerPayload({
  demo,
  includeAlphaMissense,
  seededData,
  alphaHeatmap,
}: {
  demo: boolean
  includeAlphaMissense: boolean
  seededData: GeneWindowData | null
  alphaHeatmap: ProteinAlphaMissenseHeatmap | null
}): boolean {
  if (demo) return false
  if (seededData == null) return true
  return includeAlphaMissense && alphaHeatmap == null
}

export function useReportGeneViewer({
  gene,
  cdna,
  transcript,
  initialData = null,
  geneContextSnapshot = null,
  proteinDomainTrack = null,
  markerClassification = null,
  demo = false,
}: ReportGeneViewerControllerInput) {
  const seededData = useMemo(
    () =>
      initialData ??
      (geneContextSnapshot
        ? adaptGeneContextSnapshot(geneContextSnapshot, markerClassification)
        : null),
    [geneContextSnapshot, initialData, markerClassification],
  )
  const seededProteinTrack = proteinDomainTrack ?? geneContextSnapshot?.protein_domain_track ?? null
  const [data, setData] = useState<GeneWindowData | null>(() =>
    seededData ??
    (demo
      ? adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant', { architecture: 'transcript' })
      : null),
  )
  const [proteinTrack, setProteinTrack] = useState<ProteinDomainTrack | null>(() =>
    seededProteinTrack ??
    (demo ? GENE_VIEWER_SAMPLE.tracks.protein_features.domain_track ?? null : null),
  )
  const [alphaHeatmap, setAlphaHeatmap] = useState<ProteinAlphaMissenseHeatmap | null>(() =>
    demo ? GENE_VIEWER_SAMPLE.tracks.alphamissense_heatmap ?? null : null,
  )
  const [includeAlphaMissense, setIncludeAlphaMissense] = useState(false)
  const [warnings, setWarnings] = useState<string[]>(() =>
    seededProteinTrack?.warnings ?? (demo ? warningsForViewer(GENE_VIEWER_SAMPLE) : []),
  )
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!demo && seededData == null)

  useEffect(() => {
    let cancelled = false
    if (initialData) {
      void Promise.resolve().then(() => {
        if (cancelled) return
        setData(seededData)
        setProteinTrack(seededProteinTrack)
        setAlphaHeatmap(null)
        setWarnings(seededProteinTrack?.warnings ?? [])
        setError(null)
        setLoading(false)
      })
      return () => {
        cancelled = true
      }
    }
    if (seededData) {
      void Promise.resolve().then(() => {
        if (cancelled) return
        setData(seededData)
        setProteinTrack(seededProteinTrack)
        setWarnings(seededProteinTrack?.warnings ?? [])
        setError(null)
        setLoading(false)
        if (!includeAlphaMissense) setAlphaHeatmap(null)
      })
      if (!shouldFetchViewerPayload({ demo, includeAlphaMissense, seededData, alphaHeatmap })) {
        return () => {
          cancelled = true
        }
      }
    }
    if (demo) {
      void Promise.resolve().then(() => {
        if (cancelled) return
        setData(adaptGeneViewer(GENE_VIEWER_SAMPLE, 'variant', { architecture: 'transcript' }))
        setProteinTrack(GENE_VIEWER_SAMPLE.tracks.protein_features.domain_track ?? null)
        setAlphaHeatmap(
          includeAlphaMissense
            ? GENE_VIEWER_SAMPLE.tracks.alphamissense_heatmap ?? null
            : null,
        )
        setWarnings(warningsForViewer(GENE_VIEWER_SAMPLE))
        setError(null)
        setLoading(false)
      })
      return () => {
        cancelled = true
      }
    }
    void Promise.resolve().then(() => {
      if (cancelled) return
      if (!seededData) setLoading(true)
      setError(null)
    })
    const fetchViewer = (requestTranscript: string | null) =>
      getGeneViewer({
        gene,
        cdna,
        transcript: requestTranscript,
        species: 'human',
        allele_mode: 'variant',
        window: {
          kind: 'around_variant',
          cds_flank_bp: 120,
          intron_flank_bp: 30,
        },
        tracks: includeAlphaMissense
          ? ['sequence', 'exons', 'clinvar', 'protein_features', 'alphamissense', 'restriction']
          : ['sequence', 'exons', 'clinvar', 'protein_features', 'restriction'],
      })
    fetchViewer(transcript ?? null)
      .catch((fetchError: Error) => {
        if (!transcript) throw fetchError
        return fetchViewer(null)
      })
      .then((response) => {
        if (cancelled) return
        setData(adaptGeneViewer(response, 'variant', { architecture: 'transcript' }))
        setProteinTrack(response.tracks.protein_features.domain_track ?? null)
        setAlphaHeatmap(response.tracks.alphamissense_heatmap ?? null)
        setWarnings(warningsForViewer(response))
        setLoading(false)
      })
      .catch((fetchError: Error) => {
        if (cancelled) return
        if (seededData) {
          setData(seededData)
          setProteinTrack(seededProteinTrack)
          setWarnings(
            Array.from(
              new Set([
                ...(seededProteinTrack?.warnings ?? []),
                viewerFetchWarning(fetchError),
              ]),
            ),
          )
          setError(null)
        } else {
          setError(fetchError.message)
        }
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [
    gene,
    cdna,
    transcript,
    initialData,
    seededData,
    seededProteinTrack,
    alphaHeatmap,
    demo,
    includeAlphaMissense,
  ])

  const proteinTrackFeatureCount = proteinTrack?.features.length ?? 0
  const propProteinTrackFeatureCount = proteinDomainTrack?.features.length ?? 0
  const renderedProteinTrack =
    proteinTrackFeatureCount > 0 || propProteinTrackFeatureCount === 0
      ? proteinTrack ?? proteinDomainTrack
      : proteinDomainTrack
  const renderedWarnings = useMemo(
    () =>
      Array.from(
        new Set([
          ...warnings,
          ...(proteinDomainTrack?.warnings ?? []),
          ...(proteinTrack?.warnings ?? []),
        ]),
      ),
    [warnings, proteinDomainTrack, proteinTrack],
  )

  return {
    data,
    proteinTrack: renderedProteinTrack,
    alphaHeatmap,
    includeAlphaMissense,
    setIncludeAlphaMissense,
    warnings: renderedWarnings,
    error,
    loading,
  }
}
