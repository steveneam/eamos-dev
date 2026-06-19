// The glanceable EAMOS-computed advisory, directly under the four call cards: the
// Evidence Fingerprint (do the axes converge?) on the left and the Posterior Gauge
// chip (how strongly, and what tier?) on the right. The full drawn decision — plane
// + waterfall + gauge — lives in §2 as the synthesis capstone; this strip links
// down to it so the verdict is never buried while §2 stays the home of the detail.

import type { EamosComputedClassification, ReportPayload } from '@/lib/backend'
import { deriveFingerprintAxes } from '@/lib/acmg/fingerprint'
import { EvidenceFingerprint } from './EvidenceFingerprint'
import { PosteriorGauge } from './PosteriorGauge'

export function AdvisorySummaryStrip({
  payload,
  computed,
  populationAf,
}: {
  payload: ReportPayload
  computed: EamosComputedClassification
  populationAf?: number | null
}) {
  const axes = deriveFingerprintAxes(populationAf, computed, {
    conservation: payload.report_profile?.computational_deep_dive?.conservation ?? [],
    loeuf: payload.report_profile?.molecular_context?.loeuf ?? null,
  })

  return (
    <section
      aria-label="EAMOS-computed advisory summary"
      className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-center"
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 'var(--r-md)',
        background: 'var(--bg)',
        padding: '14px 16px',
        boxShadow: 'var(--elev-1)',
      }}
    >
      <EvidenceFingerprint axes={axes} />

      <div className="flex flex-col items-start gap-2 sm:items-end sm:border-l sm:pl-4" style={{ borderColor: 'var(--line)' }}>
        <PosteriorGauge computed={computed} variant="chip" />
        <a
          href="#evidence_by_source"
          style={{
            fontSize: 10.5,
            fontWeight: 600,
            color: 'var(--teal-deep)',
            textDecoration: 'none',
          }}
        >
          See how this was computed →
        </a>
      </div>
    </section>
  )
}
