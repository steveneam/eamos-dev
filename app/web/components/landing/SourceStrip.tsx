import { SOURCES } from '@/lib/sources'
import { Pill, PillStyles } from '@/components/landing/ui/Pill'

export function SourceStrip() {
  return (
    <section className="py-9" style={{ background: 'var(--hero-bot)' }}>
      <PillStyles />
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
            <Pill
              key={src.key}
              as="a"
              href={src.href}
              target="_blank"
              rel="noopener noreferrer"
              title={src.description}
            >
              {src.label}
            </Pill>
          ))}
        </div>
      </div>
    </section>
  )
}
