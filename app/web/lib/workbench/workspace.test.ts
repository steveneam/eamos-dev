import { describe, expect, it } from 'vitest'
import {
  clearWorkbenchWorkspace,
  createWorkbenchWorkspace,
  parseWorkbenchWorkspace,
  readWorkbenchWorkspace,
  WORKBENCH_WORKSPACE_TTL_MS,
  workbenchIdentity,
  workspaceExpiryLabel,
} from './workspace'

describe('anonymous Workbench session workspace', () => {
  const now = new Date('2026-07-22T12:00:00.000Z')
  const identity = workbenchIdentity('rpe65', 'c.260A>G', 'NM_000329.3')

  it('restores only the exact identity before its expiry', () => {
    const workspace = createWorkbenchWorkspace(identity, now)
    const raw = JSON.stringify(workspace)
    expect(parseWorkbenchWorkspace(raw, identity, now)?.scope).toBe('browser_session')
    expect(parseWorkbenchWorkspace(raw, workbenchIdentity('ABCA4', 'c.1A>G'), now)).toBeNull()
    expect(
      parseWorkbenchWorkspace(raw, identity, new Date('2026-07-24T12:00:00.000Z')),
    ).toBeNull()
  })

  it('rejects overlarge and malformed state without throwing', () => {
    expect(parseWorkbenchWorkspace('{', identity, now)).toBeNull()
    expect(parseWorkbenchWorkspace('x'.repeat(96_001), identity, now)).toBeNull()
  })

  it('rejects impossible timestamp order and overlong expiry claims', () => {
    const workspace = createWorkbenchWorkspace(identity, now)
    expect(parseWorkbenchWorkspace(JSON.stringify({
      ...workspace,
      expires_at: new Date(now.getTime() + WORKBENCH_WORKSPACE_TTL_MS + 1).toISOString(),
    }), identity, now)).toBeNull()
    expect(parseWorkbenchWorkspace(JSON.stringify({
      ...workspace,
      created_at: '2026-07-22T12:01:00.000Z',
      updated_at: '2026-07-22T12:00:00.000Z',
    }), identity, now)).toBeNull()
  })

  it('sanitizes edits, enforces revision invariants, and allowlists result digests', () => {
    const workspace = createWorkbenchWorkspace(identity, now)
    const parsed = parseWorkbenchWorkspace(JSON.stringify({
      ...workspace,
      selection: {
        genomicStart: 68_916_700,
        genomicEnd: 68_916_710,
        orientation: 'genomic_forward',
        sequenceBasis: 'edited',
        baseAllele: 'reference',
        editRevision: 2,
      },
      edits: [
        { genomicPosition: 68_916_701, kind: 'sub', alt: 'g' },
        { genomicPosition: 68_916_702, kind: 'del', alt: 'do-not-store' },
        { genomicPosition: 68_916_703, kind: 'ins', alt: 'AC' },
        { genomicPosition: 68_916_704, kind: 'sub', alt: 'XY' },
      ],
      result_digests: {
        primer: 'a'.repeat(64),
        crispr: 'B'.repeat(64),
        align: 'not-a-digest',
        unknown: 'c'.repeat(64),
      },
    }), identity, now)
    expect(parsed?.edits).toEqual([
      { genomicPosition: 68_916_701, kind: 'sub', alt: 'G' },
      { genomicPosition: 68_916_703, kind: 'ins', alt: 'AC' },
    ])
    expect(parsed?.selection?.editRevision).toBe(2)
    expect(parsed?.result_digests).toEqual({ primer: 'a'.repeat(64) })

    const inconsistent = parseWorkbenchWorkspace(JSON.stringify({
      ...workspace,
      selection: {
        genomicStart: 1,
        genomicEnd: 1,
        orientation: 'genomic_forward',
        sequenceBasis: 'reference',
        baseAllele: 'reference',
        editRevision: 0,
      },
      edits: [{ genomicPosition: 1, kind: 'sub', alt: 'A' }],
    }), identity, now)
    expect(inconsistent?.selection).toBeNull()
  })

  it('restores bounded derived summaries without raw sequence or unknown fields', () => {
    const workspace = createWorkbenchWorkspace(identity, now)
    const digest = 'a'.repeat(64)
    const parsed = parseWorkbenchWorkspace(JSON.stringify({
      ...workspace,
      result_digests: { align: digest },
      derived_results: {
        align: {
          schema_version: 'workbench_derived_result.v1',
          tool: 'align',
          context_digest: 'b'.repeat(64),
          result_digest: digest,
          recorded_at: now.toISOString(),
          title: '2 reads aligned',
          metrics: {
            read_count: 2,
            mean_identity_percent: 98.4,
            source: 'browser_local_pairwise',
            raw_sequence: 'A'.repeat(500),
            'invalid key': 'discard me',
          },
          raw_trace: [1, 2, 3],
        },
      },
    }), identity, now)
    expect(parsed?.derived_results.align).toEqual({
      schema_version: 'workbench_derived_result.v1',
      tool: 'align',
      context_digest: 'b'.repeat(64),
      result_digest: digest,
      recorded_at: now.toISOString(),
      title: '2 reads aligned',
      metrics: {
        read_count: 2,
        mean_identity_percent: 98.4,
        source: 'browser_local_pairwise',
      },
    })
    expect(JSON.stringify(parsed)).not.toContain('raw_trace')
  })

  it('ignores disabled browser storage without throwing', () => {
    expect(readWorkbenchWorkspace(identity, {
      getItem: () => { throw new DOMException('blocked', 'SecurityError') },
      removeItem: () => undefined,
    }, now)).toBeNull()
  })

  it('clears the browser-session workspace explicitly', () => {
    let removedKey = ''
    clearWorkbenchWorkspace({ removeItem: (key) => { removedKey = key } })
    expect(removedKey).toBe('eamos.workbench.workspace.v1')
  })

  it('describes the bounded tab-session expiry', () => {
    expect(workspaceExpiryLabel('2026-07-24T12:00:00.000Z', now)).toBe('48h')
    expect(workspaceExpiryLabel('2026-07-22T12:07:01.000Z', now)).toBe('8m')
  })
})
