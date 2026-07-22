import { Reveal } from '@/components/landing/Reveal'

export function Testimonials() {
  return (
    <section
      className="py-24"
      style={{
        background: 'var(--page-bg-deep)',
        borderTop: '0.5px solid var(--page-line)',
        borderBottom: '0.5px solid var(--page-line)',
      }}
    >
      <div className="mx-auto px-8" style={{ maxWidth: 880 }}>
        <Reveal className="flex flex-col items-center text-center">
          <span aria-hidden style={{ fontFamily: 'var(--display)', fontSize: 48, lineHeight: 1, color: 'var(--em-bright)' }}>
            “
          </span>
          <blockquote
            className="mt-2"
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 500,
              fontSize: 'clamp(17px, 1.9vw, 22px)',
              lineHeight: 1.5,
              letterSpacing: '-0.01em',
              color: 'var(--hero-ink)',
              margin: 0,
            }}
          >
            As a researcher, I&rsquo;ve seen variant review turn into tab management. I built Eamos as a
            search engine for variant evidence: one query across source-backed records, modern in-silico
            predictors, and versioned criteria that can move as standards evolve. The goal is not to hide
            uncertainty. It is to make every score, source, and decision easier to inspect.
          </blockquote>
          <p
            className="mt-7"
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 600,
              fontSize: 'clamp(18px, 2vw, 22px)',
              letterSpacing: '-0.01em',
              color: 'var(--em-bright)',
              margin: 0,
            }}
          >
            Our mission: Genomics for All.
          </p>
          <div className="mt-6 flex flex-col items-center gap-1">
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--hero-ink)' }}>Steven</span>
            <span style={{ fontSize: 12.5, color: 'var(--hero-ink-3)' }}>Founder, Eamos</span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
