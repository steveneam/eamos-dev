'use client'

import type { EvidenceSourceSummary } from '@/lib/backend'

// MolecularContextBlock — locus-side molecular context for the renamed
// §4 Gene & locus context card.
//
// Reads the `molecular_context` evidence row's `summary`:
//   { gnomad_constraint: { loeuf, pli, source_url, version },
//     clingen_dosage:    { haploinsufficiency*, triplosensitivity*, last_evaluated, source_url, version },
//     overlapping_cnvs:  Array<…> }
//
// Renders nothing when every field it cares about is missing — the card host
// already has the locus diagram + gene snapshot, so an empty molecular-context
// block would just add visual noise.

interface MolecularContextBlockProps {
  evidence: EvidenceSourceSummary[]
}

interface GnomadConstraint {
  loeuf?: number | null
  pli?: number | null
  source_url?: string | null
  version?: string | null
}

interface ClinGenDosage {
  haploinsufficiency?: string | null
  haploinsufficiency_score?: string | null
  triplosensitivity?: string | null
  triplosensitivity_score?: string | null
  last_evaluated?: string | null
  source_url?: string | null
}

function readObject(raw: unknown): Record<string, unknown> | null {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null
  return raw as Record<string, unknown>
}

function readNumber(raw: unknown): number | null {
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : null
}

function readString(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : null
}

function readGnomadConstraint(raw: unknown): GnomadConstraint | null {
  const obj = readObject(raw)
  if (!obj) return null
  return {
    loeuf: readNumber(obj.loeuf),
    pli: readNumber(obj.pli),
    source_url: readString(obj.source_url),
    version: readString(obj.version),
  }
}

function readClinGenDosage(raw: unknown): ClinGenDosage | null {
  const obj = readObject(raw)
  if (!obj) return null
  return {
    haploinsufficiency: readString(obj.haploinsufficiency),
    haploinsufficiency_score: readString(obj.haploinsufficiency_score),
    triplosensitivity: readString(obj.triplosensitivity),
    triplosensitivity_score: readString(obj.triplosensitivity_score),
    last_evaluated: readString(obj.last_evaluated),
    source_url: readString(obj.source_url),
  }
}

function ChipRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap', minWidth: 0 }}>
      <span
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          color: 'var(--ink-4)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          flex: '0 0 auto',
        }}
      >
        {label}
      </span>
      <span style={{ fontSize: 12.5, color: 'var(--ink-2)', minWidth: 0, overflowWrap: 'anywhere' }}>{children}</span>
    </div>
  )
}

export function MolecularContextBlock({ evidence }: MolecularContextBlockProps) {
  const row = evidence.find((e) => e.source?.toLowerCase() === 'molecular_context')
  if (!row || !row.summary) return null

  const summary = row.summary as Record<string, unknown>
  const constraint = readGnomadConstraint(summary.gnomad_constraint)
  const dosage = readClinGenDosage(summary.clingen_dosage)
  const overlappingCnvs = Array.isArray(summary.overlapping_cnvs) ? summary.overlapping_cnvs : []
  const cnvCount = overlappingCnvs.length

  const hasConstraint =
    constraint && (constraint.loeuf != null || constraint.pli != null)
  const hasDosage =
    dosage &&
    (dosage.haploinsufficiency ||
      dosage.triplosensitivity ||
      dosage.haploinsufficiency_score ||
      dosage.triplosensitivity_score)

  if (!hasConstraint && !hasDosage && cnvCount === 0) return null

  return (
    <div
      style={{
        marginTop: 18,
        padding: '14px 16px',
        background: 'var(--bg-soft)',
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="eamos-kicker">
          Molecular context
        </span>
      </div>

      {hasConstraint && constraint && (
        <ChipRow label="gnomAD constraint">
          {constraint.loeuf != null && (
            <span style={{ fontFamily: 'var(--mono)', marginRight: 12 }}>
              LOEUF {constraint.loeuf}
            </span>
          )}
          {constraint.pli != null && (
            <span style={{ fontFamily: 'var(--mono)' }}>
              pLI {constraint.pli}
            </span>
          )}
          {constraint.source_url && (
            <a
              href={constraint.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                marginLeft: 10,
                fontSize: 11.5,
                color: 'var(--teal-deep)',
                textDecoration: 'underline',
                textUnderlineOffset: 3,
              }}
            >
              gnomAD ↗
            </a>
          )}
        </ChipRow>
      )}

      {hasDosage && dosage && (
        <ChipRow label="ClinGen dosage">
          {dosage.haploinsufficiency && (
            <span style={{ marginRight: 12 }}>
              HI: <span style={{ color: 'var(--ink) ' }}>{dosage.haploinsufficiency}</span>
            </span>
          )}
          {dosage.triplosensitivity && (
            <span>
              TS: <span style={{ color: 'var(--ink)' }}>{dosage.triplosensitivity}</span>
            </span>
          )}
          {dosage.source_url && (
            <a
              href={dosage.source_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                marginLeft: 10,
                fontSize: 11.5,
                color: 'var(--teal-deep)',
                textDecoration: 'underline',
                textUnderlineOffset: 3,
              }}
            >
              ClinGen ↗
            </a>
          )}
        </ChipRow>
      )}

      {cnvCount > 0 && (
        <ChipRow label="Overlapping CNVs">
          <span style={{ fontFamily: 'var(--mono)' }}>{cnvCount}</span>
        </ChipRow>
      )}

      {row.warnings && row.warnings.length > 0 && (
        <div style={{ fontSize: 11, color: 'var(--ink-4)', overflowWrap: 'anywhere' }}>
          {row.warnings.join(' · ')}
        </div>
      )}
    </div>
  )
}
