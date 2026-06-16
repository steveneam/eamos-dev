import { useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { streamReportChat, type ReportChatTurn } from '@/lib/chat'
import type { ReportPayload } from '@/lib/backend'

interface AskEamosProps {
  /** The report payload — sent as the evidence context the chat is grounded in.
   *  Optional: cohort surfaces (Batch) reuse the shell in its coming-soon state,
   *  where `send` is gated off and no payload is dereferenced. */
  payload?: ReportPayload
  /** Capability flag — flips the chat from the coming-soon state to live. */
  enabled: boolean
  suggestions?: string[]
  /** Rendered at the top of the scrollable conversation area — the AI evidence
   *  summary opens the thread, chat-style (it scrolls as the conversation grows). */
  intro?: ReactNode
}

interface Message {
  role: 'user' | 'ai'
  text: string
}

const DEFAULT_SUGGESTIONS = [
  'What is the clinical significance?',
  'Why is REVEL 0.82 considered high?',
  'What is the next clinical step?',
  'Are there any active trials?',
]

/**
 * The Ask-Eamos chat shell for the work-rail (docs/ai-work-rail/spec.md): a
 * scrollable conversation area (the evidence summary opens it, messages follow)
 * over a composer pinned at the bottom — the familiar assistant layout (Claude /
 * Grok). Streams via `streamChat`, gated on `runId`; today `runId` is null so it
 * renders the guiding coming-soon state, and the AI gateway lights it up with no
 * rebuild. Layout lives in work-rail.css (`.wr-chat*`).
 */
export function AskEamos({ payload, enabled, suggestions = DEFAULT_SUGGESTIONS, intro }: AskEamosProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const disabled = !enabled

  const send = async (question: string) => {
    if (!enabled || !payload || !question.trim() || streaming) return
    setError(null)
    setInput('')
    // Prior completed turns become multi-turn history (the new pair is appended after).
    const history: ReportChatTurn[] = messages
      .filter((m) => m.text.trim())
      .map((m) => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.text }))
    setMessages((prev) => [...prev, { role: 'user', text: question }, { role: 'ai', text: '' }])
    setStreaming(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      for await (const chunk of streamReportChat(payload, question, history, controller.signal)) {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last && last.role === 'ai') {
            next[next.length - 1] = { ...last, text: last.text + chunk }
          }
          return next
        })
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message ?? 'Chat failed')
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    void send(input)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send(input)
    }
  }

  const sendActive = !disabled && !streaming && !!input.trim()

  return (
    <div className="wr-chat">
      {/* Conversation — the evidence summary is the opening Eamos message, so the
          thread reads as if it already started; user/Eamos turns append below. */}
      <div className="wr-chat-scroll">
        <div aria-live="polite" className="wr-chat-msgs">
          {intro && (
            <div className="wr-chat-msg">
              <span className="wr-chat-role is-ai">Eamos</span>
              {intro}
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className="wr-chat-msg">
              <span className={`wr-chat-role${msg.role === 'ai' ? ' is-ai' : ''}`}>
                {msg.role === 'user' ? 'You' : 'Eamos'}
              </span>
              <div className={msg.role === 'user' ? 'wr-chat-user' : 'wr-chat-ai'}>
                {msg.text || (msg.role === 'ai' && streaming ? <TypingDots /> : null)}
              </div>
            </div>
          ))}
        </div>
        {messages.length === 0 && (
          <div className="wr-chat-starters">
            <span className="wr-chat-starters-label">
              {disabled ? "You'll be able to ask" : 'Try asking'}
            </span>
            <div className="wr-chat-chips">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void send(s)}
                  disabled={disabled || streaming}
                  className="ask-chip"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Composer — pinned at the bottom of the rail. */}
      <div className="wr-chat-composer">
        {error && (
          <div role="alert" className="wr-chat-err">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="ask-form">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || streaming}
            rows={1}
            placeholder={
              disabled
                ? 'Variant-aware chat is coming soon.'
                : 'Ask a follow-up about this variant, evidence, or therapies…'
            }
            aria-label="Ask Eamos"
            className="ask-input"
          />
          <button
            type="submit"
            disabled={!sendActive}
            aria-label="Send"
            className="ask-send"
            data-on={sendActive}
          >
            <SendIcon />
          </button>
        </form>
        <p className="wr-chat-disclaimer">
          <InfoDot />
          Answers cite source databases · not a substitute for clinical judgement
        </p>
      </div>

      <style>{`
        .ask-form:focus-within {
          border-color: var(--teal) !important;
          box-shadow: 0 0 0 3px rgba(29,158,117,0.10);
        }
        .ask-chip:hover:not(:disabled) {
          background: var(--bg-soft);
          border-color: var(--ink-5);
          color: var(--ink);
        }
        .ask-chip:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(29,158,117,0.14);
          border-color: var(--teal);
        }
        .ask-chip:active:not(:disabled) {
          transform: scale(0.97);
          transition-duration: 80ms;
        }
      `}</style>
    </div>
  )
}

function InfoDot() {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      style={{ flexShrink: 0 }}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1" aria-label="thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 5,
            height: 5,
            borderRadius: 999,
            background: 'var(--ink-4)',
            opacity: 0.6,
            animation: `eamos-typing 1.2s ${i * 0.15}s infinite`,
          }}
        />
      ))}
      <style>{`@keyframes eamos-typing { 0%,80%,100% { opacity: 0.3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }`}</style>
    </span>
  )
}
