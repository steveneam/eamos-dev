'use client'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { fetchLookupSections } from '@/lib/api'
import type {
  LookupRequest,
  LookupSectionEnvelope,
  LookupSectionId,
} from '@/lib/backend'

// LazySection v1 — IntersectionObserver-driven section loader for the M11
// `/api/v1/lookup/sections` endpoint. `eagerData` short-circuits the lazy path
// so offline demos and any payload that still ships sections eagerly keep
// rendering with zero fetches. Once the backend trims the initial response,
// passing a null `eagerData` flips the same call site to lazy-fetch the
// section on scroll-into-view.
//
// Scope is intentionally narrow: this is the read-side wrapper for the lazy
// sections defined by DL-013 (publications + clingen + computational). It
// fires at most one fetch per mount (one-shot); retries are user-driven
// through the error view button.

export interface LazySectionProps<T> {
  /**
   * Pre-loaded section payload. When non-null, the children render-prop is
   * invoked immediately and no IntersectionObserver is attached. This is the
   * path the offline RPE65 demo and any eager-payload live response take.
   */
  eagerData: T | null | undefined
  /** Section to request when lazy fetching kicks in. */
  sectionId: LookupSectionId
  /**
   * Lookup request body. Required when `eagerData` is null — without it the
   * component cannot fetch and renders the `emptyView` instead.
   */
  request?: LookupRequest | null
  /**
   * Narrow the envelope's untyped payload to the section's typed shape. Return
   * `null` to signal the section is missing from the response (renders
   * `emptyView`).
   */
  unwrap: (envelope: LookupSectionEnvelope) => T | null
  /** Render the section once data is available (eager or fetched). */
  children: (data: T) => ReactNode
  /** Rendered while idle (pre-intersection) and during the fetch. */
  placeholder?: ReactNode
  /** Rendered when there is no eager data and no request to drive a fetch. */
  emptyView?: ReactNode
  /** Rendered when the backend returns a non-ready envelope without typed payload. */
  sectionStateView?: (envelope: LookupSectionEnvelope, retryAction: ReactNode) => ReactNode
  /** Rendered when the fetch fails. Defaults include a retry button. */
  errorView?: (message: string, retryAction: ReactNode) => ReactNode
  /**
   * Margin around the observer root. The default starts the fetch ~200px
   * before the section scrolls into the viewport so the network round-trip
   * overlaps the user's approach.
   */
  rootMargin?: string
  /**
   * Test/escape hatch: when true, behaves as if the section has intersected
   * immediately. Used by tests; production call sites should not set this.
   */
  forceLoad?: boolean
}

type LoadState<T> =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; data: T }
  | { kind: 'empty' }
  | { kind: 'section_state'; envelope: LookupSectionEnvelope }
  | { kind: 'error'; message: string }

export function LazySection<T>({
  eagerData,
  sectionId,
  request,
  unwrap,
  children,
  placeholder,
  emptyView,
  sectionStateView,
  errorView,
  rootMargin = '200px',
  forceLoad = false,
}: LazySectionProps<T>): ReactNode {
  // Eager path: render immediately, no observer.
  if (eagerData != null) return <>{children(eagerData)}</>

  // No eager data and no request → nothing to fetch. Render the empty view.
  if (!request) return <>{emptyView ?? null}</>

  return (
    <LazyFetchSection<T>
      sectionId={sectionId}
      request={request}
      unwrap={unwrap}
      placeholder={placeholder}
      emptyView={emptyView}
      sectionStateView={sectionStateView}
      errorView={errorView}
      rootMargin={rootMargin}
      forceLoad={forceLoad}
    >
      {children}
    </LazyFetchSection>
  )
}

interface LazyFetchSectionProps<T> {
  sectionId: LookupSectionId
  request: LookupRequest
  unwrap: (envelope: LookupSectionEnvelope) => T | null
  placeholder?: ReactNode
  emptyView?: ReactNode
  sectionStateView?: (envelope: LookupSectionEnvelope, retryAction: ReactNode) => ReactNode
  errorView?: (message: string, retryAction: ReactNode) => ReactNode
  rootMargin: string
  forceLoad: boolean
  children: (data: T) => ReactNode
}

function LazyFetchSection<T>({
  sectionId,
  request,
  unwrap,
  placeholder,
  emptyView,
  sectionStateView,
  errorView,
  rootMargin,
  forceLoad,
  children,
}: LazyFetchSectionProps<T>): ReactNode {
  const [state, setState] = useState<LoadState<T>>({ kind: 'idle' })
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const fetchedRef = useRef(false)
  const fetchIdRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const unwrapRef = useRef(unwrap)
  const requestBody = useMemo(() => ({ ...request, include: [sectionId] }), [request, sectionId])
  const requestSignature = useMemo(() => JSON.stringify(requestBody), [requestBody])

  useEffect(() => {
    unwrapRef.current = unwrap
  }, [unwrap])

  useEffect(() => {
    let cancelled = false
    fetchedRef.current = false
    fetchIdRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    void Promise.resolve().then(() => {
      if (!cancelled) setState({ kind: 'idle' })
    })
    return () => {
      cancelled = true
    }
  }, [requestSignature])

  useEffect(() => {
    return () => {
      fetchIdRef.current += 1
      abortRef.current?.abort()
      abortRef.current = null
    }
  }, [])

  // Mark the active fetch so a stale request whose unwrap returns null doesn't
  // overwrite a fresher result. The request body is the dependency-change
  // signal; deep-equal isn't worth the bytes for the v1 surface.
  const runFetch = useCallback(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const fetchId = fetchIdRef.current + 1
    fetchIdRef.current = fetchId
    setState({ kind: 'loading' })
    fetchLookupSections(requestBody, { signal: controller.signal })
      .then((response) => {
        if (fetchIdRef.current !== fetchId || controller.signal.aborted) return
        const envelope = response.sections[sectionId]
        if (!envelope) {
          setState({ kind: 'error', message: `Section "${sectionId}" missing from response.` })
          return
        }
        const data = unwrapRef.current(envelope)
        if (data == null) {
          if (envelope.status === 'missing' || envelope.status === 'empty' || envelope.status === 'unsupported') {
            setState({ kind: 'empty' })
            return
          }
          if (sectionStateView) {
            setState({ kind: 'section_state', envelope })
            return
          }
          setState({ kind: 'error', message: `Section "${sectionId}" payload could not be narrowed.` })
          return
        }
        setState({ kind: 'ready', data })
      })
      .catch((err: unknown) => {
        if (fetchIdRef.current !== fetchId || controller.signal.aborted || isAbortError(err)) return
        const message = err instanceof Error ? err.message : 'Section fetch failed.'
        setState({ kind: 'error', message })
      })
  }, [requestBody, sectionId, sectionStateView])

  const retry = useCallback(() => {
    fetchedRef.current = false
    runFetch()
  }, [runFetch])

  useEffect(() => {
    if (forceLoad) {
      runFetch()
      return
    }
    const node = sentinelRef.current
    // SSR / no-IO environments: skip lazy and fall through to fetch immediately
    // so the section is never permanently stuck on the placeholder.
    if (typeof IntersectionObserver === 'undefined' || !node) {
      runFetch()
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            observer.disconnect()
            runFetch()
            break
          }
        }
      },
      { rootMargin },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [forceLoad, rootMargin, runFetch])

  if (state.kind === 'ready') return <>{children(state.data)}</>
  if (state.kind === 'empty') return <>{emptyView ?? null}</>
  const retryAction = <RetryAction onRetry={retry} />
  if (state.kind === 'error') {
    if (errorView) return <>{errorView(state.message, retryAction)}</>
    return <DefaultErrorView message={state.message} onRetry={retry} />
  }
  if (state.kind === 'section_state') {
    if (sectionStateView) return <>{sectionStateView(state.envelope, retryAction)}</>
  }

  // idle or loading — same visual state. The sentinel must be in the DOM
  // during 'idle' so IntersectionObserver has something to watch.
  return (
    <div ref={sentinelRef} aria-busy={state.kind === 'loading'} data-lazy-section={sectionId}>
      {placeholder ?? <DefaultPlaceholder sectionId={sectionId} />}
    </div>
  )
}

function isAbortError(err: unknown) {
  return err instanceof Error && err.name === 'AbortError'
}

function RetryAction({ onRetry }: { onRetry: () => void }) {
  return (
    <button type="button" onClick={onRetry} className="eamos-toggle-btn" style={{ fontSize: 11.5 }}>
      Retry
    </button>
  )
}

function DefaultPlaceholder({ sectionId }: { sectionId: LookupSectionId }) {
  return (
    <div
      role="status"
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 8,
        padding: '14px 16px',
        background: 'var(--bg-soft)',
        fontSize: 12,
        color: 'var(--ink-4)',
      }}
    >
      Loading <span style={{ fontFamily: 'var(--mono)' }}>{sectionId}</span>…
    </div>
  )
}

function DefaultErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      style={{
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 8,
        padding: '12px 14px',
        background: 'var(--warn-tint)',
        color: 'var(--warn-text)',
        fontSize: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
      }}
    >
      <span>Could not load section: {message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="eamos-toggle-btn"
        style={{ fontSize: 11.5 }}
      >
        Retry
      </button>
    </div>
  )
}
