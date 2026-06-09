'use client'

import type { EvidenceSourceSummary } from '@/lib/backend'
import { SourceLink } from '@/components/ui/SourceLink'

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

interface ConservationScore {
  name: string
  score: number
  interpretation: string | null
  source_url: string | null
}

// Conservation lives on the `computational_annotations` evidence row (REAL —
// phyloP100way / GERP++ from dbNSFP), separate from molecular_context. Surface it
// here so the locus card answers "does evolution care about this base?".
function readConservation(evidence: EvidenceSourceSummary[]): ConservationScore[] {
  const row = evidence.find((e) => e.source?.toLowerCase() === 'computational_annotations')
  const raw = (row?.summary as Record<string, unknown> | undefined)?.conservation
  if (!Array.isArray(raw)) return []
  const out: ConservationScore[] = []
  for (const item of raw) {
    const obj = readObject(item)
    const name = readString(obj?.name)
    const score = readNumber(obj?.score)
    if (!obj || !name || score == null) continue
    out.push({ name, score, interpretation: readString(obj.interpretation), source_url: readString(obj.source_url) })
  }
  return out
}

// phyloP100way ranges roughly -20 (accelerated) to +10 (deeply conserved); the
// positive half is what matters clinically. Map to a 0..1 fill on a [-2, 8] view.
function phyloPFill(score: number): number {
  return Math.max(0, Math.min(1, (score + 2) / 10))
}

function ChipRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap', minWidth: 0 }}>
      <span className="eamos-kicker" style={{ flex: '0 0 auto' }}>
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
  const dosage = readClinGenDosage(summary.clingen_dosage)
  const overlappingCnvs = Array.isArray(summary.overlapping_cnvs) ? summary.overlapping_cnvs : []
  const cnvCount = overlappingCnvs.length
  const conservation = readConservation(evidence)
  const phyloP = conservation.find((c) => c.name.toLowerCase().startsWith('phylop'))
  const gerp = conservation.find((c) => c.name.toLowerCase().startsWith('gerp'))

  const hasDosage =
    dosage &&
    (dosage.haploinsufficiency ||
      dosage.triplosensitivity ||
      dosage.haploinsufficiency_score ||
      dosage.triplosensitivity_score)

  // gnomAD constraint moved to §3's ConstraintGauge — this block now renders on
  // dosage / overlapping CNVs / conservation only.
  if (!hasDosage && cnvCount === 0 && conservation.length === 0) return null

  return (
    <div
      style={{
        marginTop: 'var(--report-subpanel-gap)',
        padding: 'var(--report-subpanel-pad)',
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

      {phyloP && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <ChipRow label="Conservation">
            <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
              <span
                title="phyloP100way — per-base evolutionary conservation across 100 vertebrates. Positive = conserved (selection against change); ≳ 2 marks a constrained site."
                style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)' }}
              >
                <span style={{ fontFamily: 'var(--mono)', fontSize: 16, fontWeight: 600, color: 'var(--ink)' }}>
                  {phyloP.score.toFixed(2)}
                </span>{' '}
                <span style={{ fontSize: 11.5, color: 'var(--ink-4)' }}>phyloP</span>
              </span>
              {phyloP.interpretation && (
                <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{phyloP.interpretation}</span>
              )}
              {gerp && (
                <span
                  style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)', borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }}
                  title="GERP++ RS — rejected-substitutions score; higher = stronger evolutionary constraint at this position."
                >
                  GERP++ {gerp.score.toFixed(2)}
                </span>
              )}
              {phyloP.source_url && (
                <SourceLink href={phyloP.source_url}>
                  dbNSFP
                </SourceLink>
              )}
            </span>
          </ChipRow>
          {/* phyloP conservation scale: accelerated ↔ conserved */}
          <div style={{ position: 'relative', height: 6, borderRadius: 999, background: 'linear-gradient(90deg, var(--bg-soft2), var(--teal-tint), var(--teal))', border: '0.5px solid var(--line)' }}>
            <span
              style={{
                position: 'absolute',
                top: -3,
                left: `calc(${(phyloPFill(phyloP.score) * 100).toFixed(1)}% - 1px)`,
                width: 2,
                height: 12,
                background: 'var(--ink)',
                borderRadius: 1,
              }}
              aria-hidden
            />
          </div>
        </div>
      )}

      {/* gnomAD LOEUF/pLI live in §3's ConstraintGauge (AfThermometer) — the
          richer coloured gauge owns the constraint readout + the gnomAD source
          link, so this block no longer repeats the numbers (sweep de-dup). */}
      {hasDosage && dosage && (
        <ChipRow label="ClinGen dosage">
          {dosage.haploinsufficiency && (
            <span style={{ marginRight: 12 }}>
              HI: <span style={{ color: 'var(--ink)' }}>{dosage.haploinsufficiency}</span>
            </span>
          )}
          {dosage.triplosensitivity && (
            <span>
              TS: <span style={{ color: 'var(--ink)' }}>{dosage.triplosensitivity}</span>
            </span>
          )}
          {dosage.source_url && (
            <SourceLink href={dosage.source_url} style={{ marginLeft: 10 }}>
              ClinGen
            </SourceLink>
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
