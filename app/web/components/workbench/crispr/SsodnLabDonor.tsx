'use client'

import { useEffect, useState } from 'react'
import type { CrisprSsodnDesign, CrisprSsodnResponse, SsodnOrientation } from '@/lib/backend'
import { designSsodn } from '@/lib/api'
import { CopyButton } from '@/components/ui/CopyButton'
import { disclosureChipClass, disclosureView } from '@/lib/workbench/source-disclosure'

const MIN_LEN = 60
const MAX_LEN = 200
const DEFAULT_LEN = 120

/** Mock when the route is unreachable (offline fallback) or the backend can't
 *  resolve a real genomic window — both surface as an illustrative donor. */
function isMock(res: CrisprSsodnResponse): boolean {
  return (
    res.warnings.includes('crispr_ssodn_mock_genomic_window') ||
    res.ssodn.template_source.startsWith('mock')
  )
}

/** Offsets of the 3 nucleotides of the codon carrying the edit, framed from the
 *  CDS position so the whole codon (not just the changed base) is highlighted.
 *  Falls back to centring on the edit when `c.` can't be parsed. */
function editedCodon(
  variantOffset: number,
  cdna: string,
): { offsets: Set<number>; number: number | null } {
  const match = cdna.match(/c\.(\d+)/)
  const cdsPos = match ? Number(match[1]) : null
  const start =
    cdsPos != null ? variantOffset - (((cdsPos - 1) % 3) + 3) % 3 : variantOffset - 1
  const offsets = new Set<number>()
  for (let k = 0; k < 3; k++) offsets.add(start + k)
  return { offsets, number: cdsPos != null ? Math.ceil(cdsPos / 3) : null }
}

const COMP: Record<string, string> = { A: 'T', T: 'A', G: 'C', C: 'G' }
const complement = (s: string) => s.split('').map((c) => COMP[c] ?? c).join('')
const revcomp = (s: string) => complement(s).split('').reverse().join('')

/** Reference (wild-type) window + the WT/donor codons. The reference is the
 *  donor with the edited base reverted to the reference allele (parsed from
 *  edits_encoded), so the two sequences align position-for-position. */
function deriveReference(
  ss: CrisprSsodnDesign,
  codonOffsets: Set<number>,
): { wtSeq: string | null; wtCodon: string | null; donorCodon: string } {
  const refAllele = ss.edits_encoded[0]?.match(/c\.\d+([ACGT])>[ACGT]/)?.[1] ?? null
  const arr = ss.oligo_sequence.split('')
  if (refAllele) arr[ss.variant_offset] = refAllele
  const wtSeq = refAllele ? arr.join('') : null
  const offs = [...codonOffsets].sort((a, b) => a - b)
  const donorCodon = offs.map((i) => ss.oligo_sequence[i] ?? '').join('').toUpperCase()
  const wtCodon = wtSeq ? offs.map((i) => wtSeq[i] ?? '').join('').toUpperCase() : null
  return { wtSeq, wtCodon, donorCodon }
}

/** One sequence line: intronic bases lowercased, the edited codon underlined,
 *  and (donor only) the single changed base highlighted. */
function SeqRow({
  label,
  seq,
  intronMask,
  codonOffsets,
  editOffset,
  markEdit,
}: {
  label: string
  seq: string
  intronMask: boolean[]
  codonOffsets: Set<number> | null
  editOffset: number
  markEdit: boolean
}) {
  return (
    <div className="ssodn-seq-row">
      <span className="ssodn-seq-label">{label}</span>
      <div className="ssodn-oligo-seq" aria-label={`${label} sequence, 5′ to 3′`}>
        {seq.split('').map((b, i) => {
          const intronic = intronMask[i] ?? false
          const inCodon = codonOffsets?.has(i) ?? false
          const edit = markEdit && i === editOffset
          return (
            <span
              key={i}
              className={`ssodn-nt${intronic ? ' intron' : ''}${inCodon ? ' codon' : ''}${edit ? ' edit' : ''}`}
            >
              {intronic ? b.toLowerCase() : b.toUpperCase()}
            </span>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Lab-order ssODN HDR donor (CRISPR Design tab). Guide-independent,
 * codon-centred corrective donor per docs/crispr-ssodn/spec.md: an adjustable
 * length (120 nt lab default), the orderable single-string oligo with intronic
 * bases lowercased and the corrective edit highlighted, the order name, and a
 * Copy-oligo button. Real workbook-accurate sequences come from the backend
 * `/api/v1/crispr/ssodn` route; the bundled sample renders it offline.
 */
export function SsodnLabDonor({ gene, cdna }: { gene: string; cdna: string }) {
  const [oligoLength, setOligoLength] = useState(DEFAULT_LEN)
  const [orientation, setOrientation] = useState<SsodnOrientation>('sense')
  const [res, setRes] = useState<CrisprSsodnResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const clampedLen = Math.min(
    MAX_LEN,
    Math.max(MIN_LEN, Number.isFinite(oligoLength) ? oligoLength : DEFAULT_LEN),
  )

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(() => {
      setLoading(true)
      setError(null)
      designSsodn({
        gene,
        cdna,
        oligo_length: clampedLen,
        orientation,
        protocol: 'lab_genomic',
      })
        .then((r) => {
          if (cancelled) return
          setRes(r)
          setLoading(false)
        })
        .catch((e) => {
          if (cancelled) return
          setError(e instanceof Error ? e.message : 'ssODN design failed')
          setLoading(false)
        })
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [gene, cdna, clampedLen, orientation])

  const ss = res?.ssodn ?? null
  const sourceDisclosure = disclosureView(res?.source_disclosure, {
    source_status: res && isMock(res) ? 'fallback' : 'source_backed',
    provider_id: res && isMock(res) ? 'crispr_ssodn_mock_window' : 'local_mane_hg38_ssodn',
    provider_label: res && isMock(res) ? 'Mock genomic-window fallback' : 'Local ssODN context',
    warnings: res?.warnings ?? [],
  })
  const mock = res ? sourceDisclosure.preview : false
  const codon = ss ? editedCodon(ss.variant_offset, cdna) : null
  const reference = ss && codon ? deriveReference(ss, codon.offsets) : null

  return (
    <section className="ssodn-donor">
      <div className="crispr-track-h ssodn-donor-h">
        <span>
          Lab order donor (ssODN)
          {mock && (
            <span
              className="eamos-mock ssodn-mock-tag"
              title="Illustrative donor — the real workbook-accurate sequence comes from the genomic donor service"
            >
              {sourceDisclosure.statusLabel}
            </span>
          )}
        </span>
        {ss && !loading && (
          <CopyButton text={ss.oligo_sequence} label="Copy oligo" size="inline" />
        )}
      </div>

      <div className="ssodn-donor-controls">
        <label
          className="field ssodn-len-field"
          title="Total donor length in nt — lab default 120, adjustable 60–200. The corrective edit stays centred."
        >
          <span className="field-label">Length (nt)</span>
          <input
            className="field-input"
            type="number"
            min={MIN_LEN}
            max={MAX_LEN}
            step={2}
            value={oligoLength}
            onChange={(e) => {
              const n = Number(e.target.value)
              setOligoLength(Number.isFinite(n) ? n : DEFAULT_LEN)
            }}
            onBlur={() => setOligoLength(clampedLen)}
          />
        </label>
        <div className="field ssodn-orient-field">
          <span className="field-label">Orientation</span>
          <div className="seg ssodn-orient-seg" role="group" aria-label="Donor orientation">
            <button
              type="button"
              className={orientation === 'sense' ? 'active' : ''}
              aria-pressed={orientation === 'sense'}
              onClick={() => setOrientation('sense')}
              title="Transcript-sense strand (workbook convention)"
            >
              Sense
            </button>
            <button
              type="button"
              className={orientation === 'antisense' ? 'active' : ''}
              aria-pressed={orientation === 'antisense'}
              onClick={() => setOrientation('antisense')}
              title="Reverse-complement of the sense donor"
            >
              Antisense
            </button>
          </div>
        </div>
      </div>

      {loading && <p className="ssodn-donor-status">Designing donor…</p>}
      {error && (
        <p className="ssodn-donor-status error" role="alert">
          {error}
        </p>
      )}

      {ss && !loading && (
        <>
          <div className="workbench-source-line" role="note">
            <span
              className={`workbench-source-chip ${disclosureChipClass(sourceDisclosure.status)}`}
            >
              {sourceDisclosure.statusLabel}
            </span>
            <span>{sourceDisclosure.providerLabel}</span>
            {sourceDisclosure.cacheStatus && (
              <span className="workbench-source-muted">{sourceDisclosure.cacheStatus}</span>
            )}
          </div>
          <div className="ssodn-oligo-name" title="Order name">
            {ss.oligo_name}
          </div>
          {reference?.wtCodon && (
            <div className="ssodn-codon-note">
              Codon{codon?.number != null ? ` ${codon.number}` : ''}:{' '}
              <b>
                {reference.wtCodon} → {reference.donorCodon}
              </b>{' '}
              coding · complement {complement(reference.wtCodon)} →{' '}
              {complement(reference.donorCodon)} · 5′→3′ rev-comp{' '}
              {revcomp(reference.wtCodon)} → {revcomp(reference.donorCodon)}
            </div>
          )}
          <div className="ssodn-seq-block">
            {reference?.wtSeq && (
              <SeqRow
                label="Reference (WT)"
                seq={reference.wtSeq}
                intronMask={ss.intron_mask}
                codonOffsets={codon?.offsets ?? null}
                editOffset={ss.variant_offset}
                markEdit={false}
              />
            )}
            <SeqRow
              label="Donor (ssODN)"
              seq={ss.oligo_sequence}
              intronMask={ss.intron_mask}
              codonOffsets={codon?.offsets ?? null}
              editOffset={ss.variant_offset}
              markEdit
            />
          </div>
          <div className="ssodn-oligo-legend">
            <span>
              <i className="ssodn-key intron" /> intronic (lowercase)
            </span>
            <span>
              <i className="ssodn-key codon" /> edited codon
              {codon?.number != null ? ` ${codon.number}` : ''}
            </span>
            <span>
              <i className="ssodn-key edit" /> changed base
            </span>
            <span className="ssodn-oligo-meta">
              {ss.oligo_length} nt · {ss.strand} strand · {ss.orientation} · ~
              {Math.round(ss.estimated_hdr_efficiency * 100)}% HDR
            </span>
          </div>
          <p className="ssodn-order-note">
            Order: Sigma · SDS-PAGE purity · lyophilised · lowest yield.
            {mock && ` ${sourceDisclosure.caveat}`}
          </p>
        </>
      )}
    </section>
  )
}
