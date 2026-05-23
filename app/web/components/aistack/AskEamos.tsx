import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { streamChat } from '@/lib/chat'

interface AskEamosProps {
  runId: string | null
  contextLabel?: string
  suggestions?: string[]
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

export function AskEamos({ runId, contextLabel, suggestions = DEFAULT_SUGGESTIONS }: AskEamosProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const disabled = runId === null

  const send = async (question: string) => {
    if (!runId || !question.trim() || streaming) return
    setError(null)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: question }, { role: 'ai', text: '' }])
    setStreaming(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      for await (const chunk of streamChat(runId, question, controller.signal)) {
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

  return (
    <div
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderTop: 'none',
        borderBottomLeftRadius: 14,
        borderBottomRightRadius: 14,
        overflow: 'hidden',
      }}
    >
      <header
        className="flex items-center gap-2.5"
        style={{
          padding: '14px 26px',
          background: 'linear-gradient(180deg, var(--teal-tint), transparent)',
          borderBottom: '0.5px solid var(--line)',
        }}
      >
        <span
          className="inline-flex items-center justify-center"
          style={{
            width: 26,
            height: 26,
            borderRadius: 999,
            background: 'var(--bg)',
            border: '0.5px solid #cbe3d8',
            color: 'var(--teal)',
          }}
        >
          <SparkIcon />
        </span>
        <h3
          style={{
            fontFamily: 'var(--display)',
            fontWeight: 600,
            fontSize: 14,
            color: 'var(--ink)',
            letterSpacing: '-0.01em',
            margin: 0,
          }}
        >
          Ask Eamos about this variant
        </h3>
        {contextLabel && (
          <span
            className="ml-auto"
            style={{ fontSize: 12, color: 'var(--ink-3)' }}
          >
            Context:{' '}
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink)', fontWeight: 600 }}>
              {contextLabel}
            </span>
          </span>
        )}
      </header>

      <div style={{ padding: '16px 26px 20px' }}>
        {messages.length > 0 && (
          <div
            aria-live="polite"
            className="mb-3.5 flex flex-col gap-4"
          >
            {messages.map((msg, i) => (
              <div key={i} className="flex flex-col gap-1.5">
                <span
                  className="uppercase"
                  style={{
                    fontSize: 10.5,
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    color: msg.role === 'user' ? 'var(--ink-4)' : 'var(--teal-deep)',
                  }}
                >
                  {msg.role === 'user' ? 'You' : 'Eamos'}
                </span>
                <div
                  style={
                    msg.role === 'user'
                      ? {
                          background: 'var(--bg-soft)',
                          padding: '10px 14px',
                          borderRadius: 10,
                          border: '0.5px solid var(--line)',
                          color: 'var(--ink)',
                          fontSize: 14,
                          lineHeight: 1.65,
                        }
                      : {
                          padding: 0,
                          color: 'var(--ink-2)',
                          fontSize: 14,
                          lineHeight: 1.65,
                          whiteSpace: 'pre-wrap',
                        }
                  }
                >
                  {msg.text || (msg.role === 'ai' && streaming ? <TypingDots /> : null)}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div
            className="mb-3"
            style={{
              fontSize: 12,
              color: '#991b1b',
              background: '#fef2f2',
              border: '0.5px solid #fca5a5',
              padding: '8px 12px',
              borderRadius: 10,
            }}
          >
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="flex items-end gap-1.5"
          style={{
            background: 'var(--bg-soft)',
            border: '0.5px solid var(--line)',
            borderRadius: 10,
            padding: '5px 5px 5px 14px',
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || streaming}
            rows={1}
            placeholder={
              disabled
                ? 'Save a patient run to ask questions.'
                : 'Ask a follow-up about this variant, evidence, or therapies…'
            }
            aria-label="Ask Eamos"
            className="min-h-[28px] flex-1 resize-none border-none bg-transparent outline-none disabled:cursor-not-allowed"
            style={{
              fontFamily: 'var(--body)',
              fontSize: 13.5,
              color: 'var(--ink)',
              padding: '9px 0',
              maxHeight: 120,
              lineHeight: 1.5,
            }}
          />
          <button
            type="submit"
            disabled={disabled || streaming || !input.trim()}
            aria-label="Send"
            className="inline-flex shrink-0 items-center justify-center text-white transition-colors disabled:cursor-not-allowed"
            style={{
              width: 32,
              height: 32,
              borderRadius: 999,
              border: 'none',
              background: disabled || streaming || !input.trim() ? 'var(--ink-5)' : 'var(--teal)',
            }}
          >
            <SendIcon />
          </button>
        </form>

        {messages.length === 0 && !disabled && (
          <div
            className="mt-2.5 flex flex-wrap items-center gap-1.5"
          >
            <span
              className="mr-1 uppercase"
              style={{
                fontSize: 10.5,
                color: 'var(--ink-4)',
                fontWeight: 600,
                letterSpacing: '0.08em',
              }}
            >
              Try
            </span>
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void send(s)}
                disabled={streaming}
                className="inline-flex items-center gap-1.5 transition-all"
                style={{
                  background: 'var(--bg)',
                  border: '0.5px solid var(--line)',
                  borderRadius: 999,
                  padding: '5px 11px',
                  fontSize: 11.5,
                  color: 'var(--ink-2)',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div
          className="mt-2.5 flex items-center gap-1.5"
          style={{ fontSize: 10.5, color: 'var(--ink-4)' }}
        >
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
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          Answers cite source databases · not a substitute for clinical judgement
        </div>
      </div>
    </div>
  )
}

function SparkIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
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
