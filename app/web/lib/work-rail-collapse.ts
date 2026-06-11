/**
 * Collapse-preference persistence for the shared <WorkRail> shell.
 *
 * Lifted out of WorkRail.tsx (STEP 0 of docs/workbench-task-a/plan.md) so the
 * left rail and — later — the centre viewer pane share one SSR-safe path. Leaf
 * module: depends on nothing in the component tree (no import cycle).
 *
 * Key shape is unchanged: `eamos-rail-<scope>-collapsed`, value '1' | '0'.
 */

function storageKey(scope: string): string {
  return `eamos-rail-${scope}-collapsed`
}

/** Persisted collapse pref, or null when never set / unavailable (private mode). */
export function readCollapsed(scope: string): boolean | null {
  try {
    const v = localStorage.getItem(storageKey(scope))
    return v === null ? null : v === '1'
  } catch {
    return null
  }
}

/** Persist the collapse pref. No-op (swallowed) in private mode. */
export function writeCollapsed(scope: string, value: boolean): void {
  try {
    localStorage.setItem(storageKey(scope), value ? '1' : '0')
  } catch {
    /* private mode — ignore */
  }
}

// ── Workbench viewer-pane pref (3-column canvas, per tool) ──
function paneKey(tool: string) {
  return `eamos-wb-viewer-${tool}`
}

/** Persisted viewer-pane string for a tool, or null when unset / unavailable. */
export function readPane(tool: string): string | null {
  try {
    return localStorage.getItem(paneKey(tool))
  } catch {
    return null
  }
}

/** Persist the viewer-pane pref for a tool. No-op in private mode. */
export function writePane(tool: string, value: string): void {
  try {
    localStorage.setItem(paneKey(tool), value)
  } catch {
    /* private mode — ignore */
  }
}
