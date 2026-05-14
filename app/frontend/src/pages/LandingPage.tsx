import { useNavigate } from 'react-router-dom'
import { TopNav } from '@/components/layout/TopNav'
import { SearchShell, type SearchSubmit } from '@/components/search/SearchShell'
import { SourceStrip } from '@/components/landing/SourceStrip'
import { FeaturesGrid } from '@/components/landing/FeaturesGrid'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { SiteFooter } from '@/components/landing/SiteFooter'

export function LandingPage() {
  const navigate = useNavigate()

  const handleSubmit = (payload: SearchSubmit) => {
    if (payload.mode === 'lookup') {
      const params = new URLSearchParams({
        gene: payload.gene,
        cdna: payload.variant,
      })
      navigate(`/report?${params.toString()}`)
    } else {
      const params = new URLSearchParams({ q: payload.query, mode: 'ai' })
      navigate(`/report?${params.toString()}`)
    }
  }

  return (
    <div style={{ background: 'var(--bg)', minHeight: '100vh' }}>
      <TopNav />

      <section className="relative overflow-hidden" style={{ padding: '96px 0 80px' }}>
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 70% 50% at 50% 0%, rgba(29,158,117,0.06), transparent 70%), radial-gradient(ellipse 50% 40% at 90% 20%, rgba(30,58,95,0.04), transparent 70%)',
          }}
        />
        <div className="relative mx-auto px-8" style={{ maxWidth: 1180 }}>
          <div className="grid items-center gap-16 md:grid-cols-[1.15fr_1fr]">
            <div>
              <span
                className="inline-flex items-center gap-2 rounded-full"
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.12em',
                  color: 'var(--teal-deep)',
                  padding: '5px 11px',
                  background: 'var(--teal-tint)',
                  border: '0.5px solid #cbe3d8',
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 999,
                    background: 'var(--teal)',
                    boxShadow: '0 0 0 3px rgba(29,158,117,0.18)',
                  }}
                />
                Genomic intelligence platform
              </span>
              <h1
                className="my-5"
                style={{
                  fontFamily: 'var(--display)',
                  fontWeight: 600,
                  fontSize: 'clamp(40px, 5.2vw, 64px)',
                  lineHeight: 1.04,
                  letterSpacing: '-0.025em',
                  color: 'var(--ink)',
                  textWrap: 'balance',
                  margin: '20px 0 22px',
                }}
              >
                One variant in.{' '}
                <span
                  style={{
                    color: 'var(--teal-deep)',
                    position: 'relative',
                    display: 'inline-block',
                  }}
                >
                  One structured report
                  <span
                    aria-hidden
                    style={{
                      position: 'absolute',
                      left: 0,
                      right: 0,
                      bottom: '0.04em',
                      height: '0.18em',
                      background: 'rgba(29,158,117,0.18)',
                      zIndex: -1,
                      borderRadius: 2,
                    }}
                  />
                </span>{' '}
                out.
              </h1>
              <p
                className="mb-9"
                style={{
                  fontSize: 18,
                  lineHeight: 1.6,
                  color: 'var(--ink-3)',
                  maxWidth: 540,
                  margin: '0 0 36px',
                }}
              >
                Eamos aggregates ClinVar, gnomAD, SpliceAI, VEP, AlphaMissense, and PubMed into a single
                clinician-readable report. Stop opening six tabs per variant.
              </p>
              <SearchShell variant="hero" onSubmit={handleSubmit} />
            </div>

            <aside className="relative hidden md:block">
              <PreviewCard />
            </aside>
          </div>
        </div>
      </section>

      <SourceStrip />
      <FeaturesGrid />
      <HowItWorks />
      <SiteFooter />
    </div>
  )
}

function PreviewCard() {
  return (
    <div
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: 20,
        boxShadow:
          '0 1px 0 rgba(11,26,43,0.02), 0 20px 60px -28px rgba(11,26,43,0.20), 0 8px 20px -12px rgba(11,26,43,0.08)',
      }}
    >
      <header
        className="mb-3.5 flex items-center justify-between pb-3.5"
        style={{ borderBottom: '0.5px solid var(--line)' }}
      >
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--ink)',
            letterSpacing: '-0.01em',
          }}
        >
          <span style={{ color: 'var(--teal-deep)', fontWeight: 600 }}>RPE65</span>{' '}
          NM_000329.3:c.260A&gt;G
        </span>
        <span
          className="inline-flex items-center gap-1.5"
          style={{
            padding: '3px 9px',
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            background: 'var(--warn-tint)',
            color: '#633806',
            border: '0.5px solid var(--warn-bdr)',
          }}
        >
          <span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--warn)' }} />
          Likely path.
        </span>
      </header>
      <PreviewRow label="ClinVar" value="2 stars · 4 sub." />
      <PreviewRow label="gnomAD AF" value="0.000082" />
      <PreviewRow label="REVEL" value="0.82" />
      <PreviewRow label="SpliceAI Δmax" value="0.04" last />
    </div>
  )
}

function PreviewRow({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <div
      className="flex justify-between"
      style={{
        padding: '8px 0',
        borderBottom: last ? 'none' : '0.5px solid var(--line)',
        fontSize: 12,
      }}
    >
      <span style={{ color: 'var(--ink-4)' }}>{label}</span>
      <span
        style={{
          color: 'var(--ink-2)',
          fontWeight: 500,
          fontFamily: 'var(--mono)',
        }}
      >
        {value}
      </span>
    </div>
  )
}
