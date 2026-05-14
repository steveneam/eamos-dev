import { SOURCES } from '@/lib/sources'

export function SourceStrip() {
  return (
    <section
      className="py-12"
      style={{
        background: 'var(--bg-soft)',
        borderTop: '0.5px solid var(--line)',
        borderBottom: '0.5px solid var(--line)',
      }}
    >
      <div
        className="mx-auto flex flex-wrap items-center justify-between gap-10 px-8"
        style={{ maxWidth: 1180 }}
      >
        <span
          className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.12em]"
          style={{ color: 'var(--ink-4)' }}
        >
          Powered by
        </span>
        <div className="flex flex-1 flex-wrap justify-end gap-2.5">
          {SOURCES.map((src) => (
            <a
              key={src.key}
              href={src.href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 transition-all hover:-translate-y-px"
              style={{
                padding: '8px 14px',
                background: 'var(--bg)',
                border: '0.5px solid var(--line)',
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--ink-2)',
                textDecoration: 'none',
              }}
              title={src.description}
            >
              <span
                aria-hidden
                style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--teal)' }}
              />
              {src.label}
            </a>
          ))}
        </div>
      </div>
    </section>
  )
}
