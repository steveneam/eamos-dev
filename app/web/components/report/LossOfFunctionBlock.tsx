import type React from 'react'

// §2 Loss-of-function (PVS1) block — the null-variant ACMG axis (NMDetective-B +
// the clean-room Abou-Tayoun PVS1 decision tree). These are computational, so the
// block sits with the in-silico predictions. Mock-first: it shows the planned
// NMD / PVS1 surface, labelled until the backend lands. For non-null variants
// (e.g. missense) PVS1 is genuinely N/A — the block says so rather than inventing
// a strength.

const PVS1_TIP =
  'PVS1 — Very Strong evidence that the variant abolishes gene function (a true null / loss-of-function). The single strongest ACMG criterion; applies only to truncating changes.'
const NMD_TIP =
  'Nonsense-mediated decay: the cell destroys mRNAs carrying a premature stop, so no protein is made. Whether a null variant triggers or escapes NMD sets the PVS1 strength.'
const PROTLOST_TIP =
  'How much of the protein is lost or garbled downstream of the change. Larger loss — especially of important regions — strengthens the PVS1 call.'
const MOCK_TIP = 'Preview — not yet wired to live data. Illustrative until the NMD / PVS1 engine is connected.'

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
      <span style={{ fontSize: 8.5, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: tier === 'Pro' ? 'var(--warn-text)' : 'var(--teal-deep)' }}>{tier}</span>
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

export function LossOfFunctionBlock({ consequence }: { consequence?: string | null }) {
  const applicable = isNullVariant(consequence)
  const consequenceLabel = consequence ? consequence.replace(/_/g, ' ') : 'this variant'

  return (
    <div style={{ marginTop: 18, border: '0.5px solid var(--line)', borderRadius: 'var(--r-md)', background: 'var(--bg-soft)', padding: '14px 16px' }}>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
            <span className="eamos-mock" title={MOCK_TIP}>Illustrative</span>
            <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>preview values until the NMD / PVS1 engine is wired</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 10 }}>
            <Tile label="PVS1 strength" tip={PVS1_TIP}>
              <span style={{ display: 'inline-block', fontWeight: 700, fontSize: 12, color: 'var(--cls-path-text)', background: 'var(--cls-path-bg)', border: '0.5px solid var(--cls-path-bdr)', borderRadius: 999, padding: '1px 8px' }}>
                Very Strong · +8
              </span>
            </Tile>
            <Tile label="Predicted NMD" tip={NMD_TIP}>
              <div style={{ fontWeight: 600 }}>Triggers NMD</div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-4)', marginTop: 2 }}>50-nt rule — PTC well before the final junction</div>
            </Tile>
            <Tile label="Protein lost" tip={PROTLOST_TIP}>
              <div style={{ fontFamily: 'var(--mono)', fontWeight: 600 }}>62%</div>
              <div style={{ marginTop: 4, height: 5, borderRadius: 3, background: 'var(--bg-soft2)', overflow: 'hidden' }}>
                <span style={{ display: 'block', width: '62%', height: '100%', background: 'var(--cls-lpath-dot)' }} />
              </div>
            </Tile>
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--ink-3)', margin: '10px 0 0', lineHeight: 1.55 }}>
            Nonsense in a biologically-relevant transcript, predicted to undergo NMD → no protein (true null) ⇒{' '}
            <strong style={{ color: 'var(--ink-2)' }}>PVS1 Very Strong</strong>. PTC at aa 178 / 466 · MANE Select · exon 4.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
            <FlagChip label="Biologically-relevant transcript" state="yes" />
            <FlagChip label="Clinically-relevant region" state="na" />
            <FlagChip label="Exon LoF-tolerant" state="no" />
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
