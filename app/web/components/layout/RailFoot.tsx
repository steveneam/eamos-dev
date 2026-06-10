'use client'
import { AuthMenu } from '@/components/auth/AuthMenu'

/**
 * Pinned bottom cluster for the <WorkRail> foot — the account control (AuthMenu
 * rail-foot variant: icon-led, opens upward, portalled). The parked "Ask Eamos"
 * launcher that used to live here is gone: the rail's Library ⇄ Ask-Eamos toggle
 * is now the single Ask entry point (docs/ai-work-rail/spec.md §6). The foot hides
 * entirely while the rail is in AI mode.
 *
 * Global by construction: WorkRail is shared by report / workbench / compare, so
 * passing this as `foot` lights up the same account control on every surface.
 */
export function RailFoot() {
  return <AuthMenu tone="light" placement="rail-foot" />
}
