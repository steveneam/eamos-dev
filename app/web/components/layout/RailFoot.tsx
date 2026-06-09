'use client'
import { IconSparkle } from '@/components/icons/Icon'
import { AuthMenu } from '@/components/auth/AuthMenu'

/**
 * Pinned bottom cluster for the <WorkRail> foot (docs/workbench-task-a Part A):
 *   - a parked "Ask Eamos" launcher (COMING SOON — no LLM key, see
 *     feedback_askeamos_parked), kept in tab order for discoverability.
 *   - the account row (AuthMenu rail-foot variant) — opens upward, portalled.
 *
 * Global by construction: WorkRail is shared by report / workbench / compare,
 * so passing this as `foot` lights up the same cluster on every surface.
 */
export function RailFoot() {
  return (
    <>
      <button
        type="button"
        className="wr-foot-row wr-foot-ask"
        aria-disabled="true"
        title="Variant-aware chat — coming soon"
      >
        <span className="wr-foot-ask-ico" aria-hidden="true">
          <IconSparkle size={15} />
        </span>
        <span className="wr-foot-ask-label">Ask Eamos</span>
        <span className="wr-foot-soon">Soon</span>
      </button>
      <AuthMenu tone="light" placement="rail-foot" />
    </>
  )
}
