// The single subscription point for the variant library. Wraps the store's
// subscribe()/getLibrary() in useSyncExternalStore so every surface re-renders
// on 'eamos:library-change' + cross-tab 'storage' without hand-rolling an effect.
//
// getLibrary() is memoized in the store (stable reference between changes), so
// this does not loop on referential inequality — see lib/variant-library.ts.
import { useSyncExternalStore } from 'react'
import { getLibrary, subscribe, type LibraryStore } from '@/lib/variant-library'

const SERVER_SNAPSHOT: LibraryStore = { variants: [], folders: [] }

export function useLibrary(): LibraryStore {
  return useSyncExternalStore(subscribe, getLibrary, () => SERVER_SNAPSHOT)
}
