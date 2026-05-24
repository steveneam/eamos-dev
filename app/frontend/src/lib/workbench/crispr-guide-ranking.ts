import type { CrisprGuide } from '@/lib/backend'

/**
 * Current fixture contract: lower off-target score is better. Return the
 * guide's stable index, not its array position, so sparse backend indexes
 * do not break highlighting.
 */
export function recommendedGuideIndex(guides: readonly CrisprGuide[]): number {
  if (guides.length === 0) return -1

  return guides.reduce((best, guide) =>
    guide.off_target_score < best.off_target_score ? guide : best,
  ).index
}
