// ClinVar review-status text → 0-4 star count.
//
// ClinVar's `review_status` is a fixed enum on the submission record; mapping
// to a star tier is published in the ClinVar docs and is stable. Used by the
// Evidence-by-source ClinVar header strip to drive `ClassificationBadge`'s
// optional `reviewStars` prop.

const REVIEW_STATUS_STARS: Record<string, number> = {
  'practice guideline': 4,
  'reviewed by expert panel': 3,
  'criteria provided, multiple submitters, no conflicts': 2,
  'criteria provided, conflicting classifications': 1,
  'criteria provided, conflicting interpretations': 1,
  'criteria provided, single submitter': 1,
  'no assertion criteria provided': 0,
  'no classification provided': 0,
  'no classifications from unflagged records': 0,
}

export function reviewStatusToStars(text: string | null | undefined): number | null {
  if (!text) return null
  const key = text.trim().toLowerCase()
  if (key in REVIEW_STATUS_STARS) return REVIEW_STATUS_STARS[key]
  return null
}
