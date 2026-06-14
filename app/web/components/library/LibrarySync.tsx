'use client'

import { useEffect, useRef } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { getLibrary, subscribe } from '@/lib/variant-library'
import { pullAndMerge, pushRemoteLibrary } from '@/lib/library-sync'

const PUSH_DEBOUNCE_MS = 1500

/**
 * Account sync for the variant library (docs/library-sync/spec.md). Mounted once
 * globally (in Providers). Anonymous → no-op, localStorage only. On sign-in:
 * pull the account row + union-merge with local, then debounce-push subsequent
 * local changes back to the account row. Renders nothing.
 */
export function LibrarySync() {
  const { user } = useAuth()
  const userId = user?.id ?? null
  const timer = useRef<number | null>(null)

  useEffect(() => {
    if (!userId) return
    const controller = new AbortController()
    // Pull + merge on sign-in; the merged store's change event flows through the
    // subscriber below, which pushes it (debounced) back to the account.
    void pullAndMerge(controller.signal)

    const onChange = () => {
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => {
        void pushRemoteLibrary(getLibrary())
      }, PUSH_DEBOUNCE_MS)
    }
    const unsubscribe = subscribe(onChange)

    return () => {
      controller.abort()
      unsubscribe()
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [userId])

  return null
}
