/* Edit + undo/redo history model for the v2 sequence viewer.
   Mirrors the commit / undo / redo / jump logic in `sequence-viewer.js`,
   expressed as a pure reducer so React owns the state. */

export type Edit =
  | { kind: 'sub'; alt: string }
  | { kind: 'del'; alt: '-' }
  | { kind: 'ins'; alt: string }

export type EditMap = Map<number, Edit>

export interface HistoryStep {
  label: string
  before: EditMap
  after: EditMap
  time: number
}

export interface EditState {
  edits: EditMap
  history: HistoryStep[]
  cursor: number
}

export type EditAction =
  | { type: 'commit'; label: string; mutate: (m: EditMap) => void }
  | { type: 'undo' }
  | { type: 'redo' }
  | { type: 'jump'; to: number }

export const initialEditState: EditState = {
  edits: new Map(),
  history: [],
  cursor: 0,
}

const clone = (m: EditMap): EditMap => new Map(m)

export function editReducer(state: EditState, action: EditAction): EditState {
  switch (action.type) {
    case 'commit': {
      const before = clone(state.edits)
      const next = clone(state.edits)
      action.mutate(next)
      const history = state.history.slice(0, state.cursor)
      history.push({ label: action.label, before, after: clone(next), time: Date.now() })
      return { edits: next, history, cursor: state.cursor + 1 }
    }
    case 'undo': {
      if (state.cursor === 0) return state
      const cursor = state.cursor - 1
      return { ...state, edits: clone(state.history[cursor].before), cursor }
    }
    case 'redo': {
      if (state.cursor >= state.history.length) return state
      const step = state.history[state.cursor]
      return { ...state, edits: clone(step.after), cursor: state.cursor + 1 }
    }
    case 'jump': {
      const cursor = Math.max(0, Math.min(action.to, state.history.length))
      if (cursor === state.cursor) return state
      const edits =
        cursor > 0 ? clone(state.history[cursor - 1].after) : new Map<number, Edit>()
      return { ...state, edits, cursor }
    }
    default:
      return state
  }
}
