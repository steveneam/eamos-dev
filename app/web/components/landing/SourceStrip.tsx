import { SOURCES } from '@/lib/sources'

export function SourceStrip() {
  return (
    <section className="py-9" style={{ background: 'var(--hero-bot)' }}>
      <div
        className="mx-auto flex flex-col items-center gap-5 px-8 sm:flex-row sm:justify-between sm:gap-10"
        style={{ maxWidth: 1180 }}
      >
        <span
          className="shrink-0 text-[10.5px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: 'var(--hero-ink-3)' }}
        >
          Powered by
        </span>
        <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-end">
          {SOURCES.map((src) => (
            <a
              key={src.key}
              href={src.href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 transition-all hover:-translate-y-px"
              style={{
                padding: '6px 13px',
                background: 'var(--d-card)',
                border: '0.5px solid var(--d-line)',
                borderRadius: 999,
                fontSize: 11.5,
                fontWeight: 500,
                color: 'var(--hero-ink-2)',
                textDecoration: 'none',
              }}
              title={src.description}
            >
              <span
                aria-hidden
                style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--em-bright)' }}
              />
              {src.label}
            </a>
          ))}
        </div>
      </div>
    </section>
  )
}
