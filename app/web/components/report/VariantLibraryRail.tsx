'use client'

import { LibrarySection } from '@/components/library/LibrarySection'
import { useLibrary } from '@/components/library/useLibrary'
import { tierFromText } from '@/components/library/tier'
import { saveVariant } from '@/lib/variant-library'
import type { LookupResponse } from '@/lib/backend'
import { RelatedVariants } from './RelatedVariants'
import { ReportSectionNav } from './ReportSectionNav'
import { IconPlus, IconCheck } from '@/components/icons/Icon'

/**
 * The /report <WorkRail> body: the shared LibrarySection (saved + folders +
 * tray) over the same store every surface uses, plus the report-specific
 * RelatedVariants lanes and the section-nav scroll-spy. The Save-current action
 * (rail head) is exported separately for WorkRail's `action` slot. Spec §1.4.
 */
export function VariantLibraryRail({ data, query }: { data: LookupResponse; query: string }) {
  return (
    <>
      <LibrarySection currentQuery={query} />
      <RelatedVariants data={data} />
      <ReportSectionNav />
    </>
  )
}

/** Identity for the open report, derived from the payload exactly as the
 *  StickyVariantRibbon does (header → variant_summary_rows[0] fallback). */
function reportIdentity(data: LookupResponse) {
  const payload = data.report_payload
  const header = payload.report_profile?.header
  const row0 = payload.variant_summary_rows[0]
  const gene = header?.gene ?? row0?.gene ?? null
  const transcriptHgvs = row0?.transcript_hgvs ?? null
  const cdna = header?.cdna ?? transcriptHgvs?.split(':')[1] ?? null
  const hgvsFull =
    transcriptHgvs ?? (header?.transcript && header?.cdna ? `${header.transcript}:${header.cdna}` : undefined)
  const classification = tierFromText(header?.classification)
  if (!gene || !cdna) return null
  return { gene, cdna, query: `${gene} ${cdna}`.trim(), hgvsFull, classification }
}

export function SaveCurrentButton({ data }: { data: LookupResponse }) {
  const { variants } = useLibrary()
  const identity = reportIdentity(data)
  const saved = identity ? variants.some((v) => v.id === identity.query.toLowerCase()) : false

  if (!identity) {
    return (
      <button type="button" className="lib-save-btn" disabled title="No variant identity available">
        <IconPlus size={13} /> Save
      </button>
    )
  }

  return (
    <button
      type="button"
      className="lib-save-btn"
      data-saved={saved ? 'true' : 'false'}
      aria-pressed={saved}
      onClick={() => {
        if (saved) return
        saveVariant(
          { gene: identity.gene, variant: identity.cdna, query: identity.query, raw: identity.query },
          { classification: identity.classification, hgvs_full: identity.hgvsFull },
        )
      }}
    >
      {saved ? (
        <>
          <IconCheck size={13} /> Saved
        </>
      ) : (
        <>
          <IconPlus size={13} /> Save
        </>
      )}
    </button>
  )
}
