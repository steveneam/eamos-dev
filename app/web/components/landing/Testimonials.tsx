import { Reveal } from '@/components/landing/Reveal'

export function Testimonials() {
  return (
    <section
      className="py-28"
      style={{
        background: 'var(--d-bg-2)',
        borderTop: '0.5px solid var(--d-line)',
        borderBottom: '0.5px solid var(--d-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 880 }}>
        <Reveal className="flex flex-col items-center text-center">
          <span
            className="mb-7 text-[11px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: 'var(--em-bright)' }}
          >
            From the bench · illustrative
          </span>
          <span aria-hidden style={{ fontFamily: 'var(--display)', fontSize: 48, lineHeight: 1, color: 'var(--em-bright)' }}>
            “
          </span>
          <blockquote
            className="mt-2"
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 500,
              fontSize: 'clamp(20px, 2.6vw, 28px)',
              lineHeight: 1.4,
              letterSpacing: '-0.015em',
              color: 'var(--hero-ink)',
              margin: 0,
            }}
          >
            Eamos completely changed our laboratory workflow. The dual-badge functional card alone saved
            our curation team over 100 hours of tedious manual review this year.
          </blockquote>
          <div className="mt-8 flex flex-col items-center gap-1">
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--hero-ink)' }}>Dr Sarah Jenkins, PhD</span>
            <span style={{ fontSize: 12.5, color: 'var(--hero-ink-3)' }}>Principal Molecular Geneticist</span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
