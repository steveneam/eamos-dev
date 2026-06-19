import type React from 'react'
import { TierTag } from '@/components/ui/TierTag'
import { EvidenceChip } from '@/components/ui/EvidenceChip'
import type { EamosComputedClassification, EamosComputedCriterion } from '@/lib/backend'

// §2 Loss-of-function (PVS1) block — the null-variant ACMG axis (NMDetective-B +
// the clean-room Abou-Tayoun PVS1 decision tree). These are computational, so the
// block sits with the in-silico predictions. For non-null variants (e.g.
// missense) PVS1 is genuinely N/A; for null variants, render only the backend
// points-engine criterion when it exists.

const PVS1_TIP =
  'PVS1 — Very Strong evidence that the variant abolishes gene function (a true null / loss-of-function). The single strongest ACMG criterion; applies only to truncating changes.'
const NMD_TIP =
  'Nonsense-mediated decay: the cell destroys mRNAs carrying a premature stop, so no protein is made. Whether a null variant triggers or escapes NMD sets the PVS1 strength.'
const PROTLOST_TIP =
  'How much of the protein is lost or garbled downstream of the change. Larger loss — especially of important regions — strengthens the PVS1 call.'

// Consequence types that invoke PVS1 (Abou-Tayoun 2018 branches A–E).
const NULL_CONSEQUENCES = [
  'stop_gained', 'stop gained', 'nonsense',
  'frameshift',
  'splice_donor', 'splice_acceptor', 'splice donor', 'splice acceptor',
  'start_lost', 'start lost', 'initiator_codon',
  'transcript_ablation', 'exon_loss', 'feature_truncation',
]

function isNullVariant(consequence: string | null | undefined): boolean {
  if (!consequence) return false
  const c = consequence.toLowerCase()
  return NULL_CONSEQUENCES.some((n) => c.includes(n))
}

const LOF_TOOLS: { name: string; tier: 'Free' | 'Pro'; tip: string }[] = [
  { name: 'NMDetective-B', tier: 'Free', tip: 'Predicts whether a premature stop triggers mRNA decay (no protein) or escapes it (truncated protein survives).' },
  { name: 'Abou-Tayoun PVS1 tree', tier: 'Free', tip: 'Eamos clean-room decision tree turning a null variant into a calibrated PVS1 strength, not a blanket flag.' },
  { name: 'VEP NMD', tier: 'Free', tip: 'Ensembl rule-based flag for stop-gain variants likely to escape nonsense-mediated decay.' },
]

function ToolTag({ name, tier, tip }: { name: string; tier: 'Free' | 'Pro'; tip: string }) {
  return (
    <span
      title={tip}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 10.5, color: 'var(--ink-3)',
        cursor: 'help', border: '0.5px solid var(--line)', borderRadius: 999, padding: '1.5px 8px', background: 'var(--bg)',
      }}
    >
      {name}
      <TierTag tier={tier} />
    </span>
  )
}

function Tile({ label, tip, children }: { label: string; tip: string; children: React.ReactNode }) {
  return (
    <div style={{ border: '0.5px solid var(--line)', borderRadius: 'var(--r-sm)', background: 'var(--bg)', padding: '8px 10px' }}>
      <div title={tip} style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-4)', cursor: 'help', marginBottom: 5 }}>{label}</div>
      <div style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{children}</div>
    </div>
  )
}

function FlagChip({ label, state }: { label: string; state: 'yes' | 'no' | 'na' }) {
  const sym = state === 'yes' ? '✓' : state === 'no' ? '✗' : '–'
  const col = state === 'yes' ? 'var(--teal-deep)' : state === 'no' ? 'var(--ink-4)' : 'var(--ink-5)'
  return (
    <span style={{ fontSize: 10.5, color: 'var(--ink-3)', border: '0.5px solid var(--line)', borderRadius: 999, padding: '1.5px 8px', background: 'var(--bg)' }}>
      <span style={{ color: col, fontWeight: 700, marginRight: 4 }}>{sym}</span>
      {label}
    </span>
  )
}

function pvs1StrengthLabel(row: EamosComputedCriterion): string {
  if (!row.triggered) return 'Not triggered'
  const strength = row.applied_strength?.replace('_', ' ') ?? 'triggered'
  return `PVS1 ${strength}`
}

function pvs1Tone(row: EamosComputedCriterion) {
  if (!row.triggered) {
    return { bg: 'var(--cls-na-bg)', border: 'var(--cls-na-bdr)', text: 'var(--cls-na-text)' }
  }
  if (row.applied_strength === 'very_strong') {
    return { bg: 'var(--cls-path-bg)', border: 'var(--cls-path-bdr)', text: 'var(--cls-path-text)' }
  }
  return { bg: 'var(--cls-lpath-bg)', border: 'var(--cls-lpath-bdr)', text: 'var(--cls-lpath-text)' }
}

export function LossOfFunctionBlock({
  consequence,
  computed,
}: {
  consequence?: string | null
  computed?: EamosComputedClassification | null
}) {
  const applicable = isNullVariant(consequence)
  const consequenceLabel = consequence ? consequence.replace(/_/g, ' ') : 'this variant'
  const pvs1 = computed?.per_criterion.find((row) => row.code === 'PVS1') ?? null

  return (
    <div style={{ marginTop: 'var(--report-subpanel-gap)', border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: 'var(--report-subpanel-pad)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <span className="eamos-kicker" title={PVS1_TIP} style={{ cursor: 'help', borderBottom: '1px dotted var(--ink-5)' }}>
          Loss-of-function · PVS1
        </span>
        <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {LOF_TOOLS.map((t) => <ToolTag key={t.name} {...t} />)}
        </span>
      </div>

      {applicable ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 10 }}>
            <Tile label="PVS1 strength" tip={PVS1_TIP}>
              {pvs1 ? (
                <EvidenceChip size="md" tone={pvs1Tone(pvs1)}>
                  {pvs1StrengthLabel(pvs1)} · {pvs1.points >= 0 ? '+' : ''}{pvs1.points}
                </EvidenceChip>
              ) : (
                <span style={{ color: 'var(--ink-4)' }}>Unavailable</span>
              )}
            </Tile>
            <Tile label="Predicted NMD" tip={NMD_TIP}>
              <div style={{ fontWeight: 600 }}>{pvs1?.triggered ? 'PVS1 triggered' : 'No source-backed call'}</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>
                {typeof pvs1?.evidence_value === 'string' ? pvs1.evidence_value : 'NMD detail unavailable'}
              </div>
            </Tile>
            <Tile label="Protein lost" tip={PROTLOST_TIP}>
              <div style={{ fontFamily: 'var(--mono)', fontWeight: 600 }}>{pvs1?.threshold ?? 'unavailable'}</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>Backend threshold/source detail</div>
            </Tile>
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
            {pvs1?.triggered ? (
              <>
                Backend points engine applied{' '}
                <strong style={{ color: 'var(--ink-2)' }}>{pvs1StrengthLabel(pvs1)}</strong>
                {pvs1.source_db ? ` from ${pvs1.source_db}` : ''}{pvs1.source_version ? ` (${pvs1.source_version})` : ''}.
              </>
            ) : (
              <>
                This looks like a possible loss-of-function consequence, but no source-backed PVS1/NMD criterion was
                applied for this report.
              </>
            )}
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
            <FlagChip label="PVS1 criterion" state={pvs1?.triggered ? 'yes' : 'no'} />
            <FlagChip label="Source threshold" state={pvs1?.threshold != null ? 'yes' : 'na'} />
            <FlagChip label="Source version" state={pvs1?.source_version ? 'yes' : 'na'} />
          </div>
        </>
      ) : (
        <p style={{ fontSize: 12.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
          <strong style={{ color: 'var(--ink-2)' }}>Not applicable</strong> — {consequenceLabel} is not a predicted
          null (loss-of-function) variant.{' '}
          <span title={PVS1_TIP} style={{ borderBottom: '1px dotted var(--ink-5)', cursor: 'help' }}>PVS1</span> applies
          only to truncating changes (nonsense, frameshift, canonical splice ±1/2, start-loss, whole-exon deletion).
        </p>
      )}
    </div>
  )
}
