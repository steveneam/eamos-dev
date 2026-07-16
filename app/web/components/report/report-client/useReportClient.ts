'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { variantLookup } from '@/lib/api'
import type { SearchInputCandidate } from '@/lib/backend'
import { RPE65_NEGATIVE_CONTROL_SAMPLE } from '@/lib/sample-report'
import { cleanQuery, isLikelyUnparseable } from '@/lib/variant-format'
import { reportHrefForQuery, searchHrefForQuery } from '@/lib/variant-search'

import {
  LIVE_SAMPLE_REPORT_HREF,
  isAbortError,
  parseLazyOverrides,
  readCachedReport,
  reportRequestKey,
  reportSummaryRequest,
  writeCachedReport,
  type ReportLoadState,
  type ReportQueryInput,
} from './reportClientModel'

export function useReportClient() {
  const params = useSearchParams()
  const router = useRouter()
  const gene = params.get('gene')?.trim() ?? ''
  const cdna = params.get('cdna')?.trim() ?? ''
  const transcript = params.get('transcript')?.trim() ?? ''
  const proteinChange = params.get('protein_change')?.trim() ?? ''
  const q = params.get('q')?.trim() ?? ''
  const demo = params.get('demo') !== null
  const fromCompare = params.get('from') === 'compare'
  const backHref = fromCompare ? '/compare' : '/'
  const backLabel = fromCompare ? 'Back to filters' : 'Back to search'
  const negativeFixture = params.get('fixture') === 'rpe65-negative'
  const lazyParam = params.get('lazy')
  const lazyOverrides = useMemo(() => parseLazyOverrides(lazyParam), [lazyParam])
  const queryInput: ReportQueryInput = useMemo(
    () => ({
      cdna,
      demo,
      fixture: negativeFixture,
      gene,
      proteinChange,
      q,
      transcript,
    }),
    [cdna, demo, negativeFixture, gene, proteinChange, q, transcript],
  )
  const requestKey = useMemo(() => reportRequestKey(queryInput), [queryInput])
  const summaryRequest = useMemo(() => reportSummaryRequest(queryInput), [queryInput])

  const [state, setState] = useState<ReportLoadState>({ kind: 'idle' })
  const [attempt, setAttempt] = useState(0)
  const [searchFocused, setSearchFocused] = useState(false)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    if (demo) {
      router.replace(LIVE_SAMPLE_REPORT_HREF)
      return () => controller.abort()
    }

    if (negativeFixture) {
      return () => controller.abort()
    }

    if (!gene && !cdna && !q) {
      router.replace(LIVE_SAMPLE_REPORT_HREF)
      return () => controller.abort()
    }

    if (!gene && !cdna && q) {
      const cachedData = readCachedReport(requestKey)
      if (cachedData) {
        void Promise.resolve().then(() => {
          if (!cancelled) setState({ kind: 'ready', requestKey, data: cachedData })
        })
      }
      variantLookup({ search_text: q, species: 'human' }, { signal: controller.signal })
        .then((data) => {
          if (cancelled) return
          const interpretation = data.search_interpretation ?? null
          const responseGene =
            data.report_payload.report_profile?.header?.gene ??
            data.report_payload.variant_summary_rows[0]?.gene
          if (interpretation && !responseGene) {
            setState({
              kind: 'interpretation',
              requestKey,
              query: q,
              interpretation,
              detail: data.report_payload.limitations,
            })
            return
          }
          if (
            responseGene &&
            interpretation?.gene &&
            responseGene.toUpperCase() !== interpretation.gene.toUpperCase()
          ) {
            setState({
              kind: 'error',
              requestKey,
              message: `Lookup returned data for ${responseGene}, but the search resolved to ${interpretation.gene}. The report was not rendered to avoid showing stale variant facts.`,
            })
            return
          }
          writeCachedReport(requestKey, data)
          setState({ kind: 'ready', requestKey, data })
        })
        .catch((error: Error) => {
          if (cancelled || isAbortError(error)) return
          if (cachedData) return
          if (error instanceof TypeError) {
            setState({ kind: 'offline', requestKey })
          } else {
            setState({ kind: 'error', requestKey, message: error.message })
          }
        })
      return () => {
        cancelled = true
        controller.abort()
      }
    }

    if ((gene && !cdna && !q) || (!gene && cdna && !q)) {
      const href = reportHrefForQuery(`${gene} ${cdna}`.trim())
      if (href) router.replace(href)
      return () => controller.abort()
    }

    if (!gene || !cdna) {
      void Promise.resolve().then(() => {
        if (!cancelled) {
          setState({
            kind: 'error',
            requestKey,
            message: 'Both a gene and a cDNA (or HGVS) change are required.',
          })
        }
      })
      return () => controller.abort()
    }

    const cleanedCdna = cleanQuery(cdna)
    const probe = `${gene.toUpperCase()} ${cleanedCdna}`.trim()

    if (isLikelyUnparseable(gene, cdna)) {
      void Promise.resolve().then(() => {
        if (!cancelled) setState({ kind: 'malformed', requestKey, query: probe })
      })
      return () => controller.abort()
    }

    const cachedData = readCachedReport(requestKey)
    if (cachedData) {
      void Promise.resolve().then(() => {
        if (!cancelled) setState({ kind: 'ready', requestKey, data: cachedData })
      })
    }
    variantLookup(
      {
        gene,
        cdna: cleanedCdna,
        transcript: transcript || null,
        protein_change: proteinChange || null,
        species: 'human',
      },
      { signal: controller.signal },
    )
      .then((data) => {
        if (cancelled) return
        const warnings = data.warnings ?? []
        if (warnings.some((code) => code.startsWith('input_unparseable:'))) {
          setState({
            kind: 'malformed',
            requestKey,
            query: probe,
            detail: data.report_payload.limitations ?? undefined,
          })
          return
        }
        if (warnings.includes('no_genomic_resolution')) {
          setState({ kind: 'unresolved', requestKey, query: probe })
          return
        }
        const responseGene =
          data.report_payload.report_profile?.header?.gene ??
          data.report_payload.variant_summary_rows[0]?.gene
        if (responseGene && responseGene.toUpperCase() !== gene.toUpperCase()) {
          setState({
            kind: 'error',
            requestKey,
            message: `Lookup returned data for ${responseGene}, but the URL requested ${gene}. The report was not rendered to avoid showing stale variant facts.`,
          })
          return
        }
        writeCachedReport(requestKey, data)
        setState({ kind: 'ready', requestKey, data })
      })
      .catch((error: Error) => {
        if (cancelled || isAbortError(error)) return
        if (cachedData) return
        if (error instanceof TypeError) {
          setState({ kind: 'offline', requestKey })
        } else {
          setState({ kind: 'error', requestKey, message: error.message })
        }
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [
    gene,
    cdna,
    transcript,
    proteinChange,
    q,
    demo,
    negativeFixture,
    attempt,
    router,
    requestKey,
  ])

  const handleSearch = (raw: string) => {
    const href = searchHrefForQuery(raw)
    if (href) router.push(href)
  }

  const handleSelectCandidate = (candidate: SearchInputCandidate) => {
    if (!candidate.gene || !candidate.cdna) return
    const candidateParams = new URLSearchParams({ gene: candidate.gene, cdna: candidate.cdna })
    if (candidate.transcript) candidateParams.set('transcript', candidate.transcript)
    if (candidate.protein_change) {
      candidateParams.set('protein_change', candidate.protein_change)
    }
    router.push(`/report?${candidateParams.toString()}`)
  }

  const queryLabel = `${gene} ${cdna}`.trim() || q
  let activeState: ReportLoadState = { kind: 'loading', requestKey }
  if (negativeFixture) {
    activeState = { kind: 'ready', requestKey, data: RPE65_NEGATIVE_CONTROL_SAMPLE }
  } else if (state.kind !== 'idle' && state.requestKey === requestKey) {
    activeState = state
  }

  return {
    activeState,
    backHref,
    backLabel,
    cdna,
    fromCompare,
    gene,
    handleSearch,
    handleSelectCandidate,
    lazyOverrides,
    negativeFixture,
    queryLabel,
    retry: () => setAttempt((value) => value + 1),
    searchFocused,
    setSearchFocused,
    summaryRequest,
  }
}
