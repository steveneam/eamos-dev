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
            From the founder
          </span>
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
            As a researcher, I&rsquo;ve felt first-hand how much time disappears into manually sifting
            through countless databases just to annotate and curate a single variant — and how those
            delays push back the genetic reports patients are waiting on. With debilitating, progressive
            genetic disease, every second matters: it can be the difference between the right treatment in
            time and missing it altogether. I built Eamos to give that time back — to researchers and
            clinicians, and to the patients and curious minds who simply want to understand their own
            genetics.
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
