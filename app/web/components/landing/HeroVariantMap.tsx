'use client'

import { useState } from 'react'

const REPRESENTATIONS = [
  {
    key: 'genomic',
    label: 'Genomic',
    context: 'GRCh38 · reverse strand',
    value: 'chr1:68,444,869 T>C',
    marker: 'T→C',
  },
  {
    key: 'transcript',
    label: 'Transcript',
    context: 'NM_000329.3 · exon 4',
    value: 'RPE65 c.260A>G',
    marker: 'A→G',
  },
  {
    key: 'protein',
    label: 'Protein',
    context: 'Residue 87 · missense',
    value: 'p.Asp87Gly',
    marker: 'D→G',
  },
  {
    key: 'evidence',
    label: 'Evidence',
    context: 'Full evidence stack',
    value: 'ClinVar · REVEL · SpliceAI',
    marker: '11 engines',
  },
] as const

const RUNGS = Array.from({ length: 15 }, (_, index) => {
  const y = 34 + index * 23
  const phase = Math.sin(index * 0.82)
  return {
    y,
    left: 82 + phase * 38,
    right: 238 - phase * 38,
    front: phase > 0,
    variant: index === 7,
  }
})

export function HeroVariantMap() {
  const [activeIndex, setActiveIndex] = useState(1)
  const active = REPRESENTATIONS[activeIndex]
  const advance = () => setActiveIndex((current) => (current + 1) % REPRESENTATIONS.length)

  return (
    <aside
      className="hidden min-w-0 lg:block"
      aria-label="Interactive mapping of the bundled RPE65 variant"
    >
      <div className="hero-variant-map relative">
        <div className="flex items-start justify-between gap-5">
          <div>
            <span className="hero-variant-kicker">One change, four views</span>
            <h2 className="hero-variant-title">Follow the variant through the evidence.</h2>
          </div>
          <span className="hero-variant-demo">RPE65 demo</span>
        </div>

        <div className="relative mt-4" style={{ height: 350 }}>
          <svg
            viewBox="0 0 320 360"
            className="absolute inset-0 h-full w-full"
            aria-hidden="true"
            fill="none"
          >
            <defs>
              <linearGradient id="hero-dna-a" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="var(--flow-cool)" stopOpacity="0.2" />
                <stop offset="0.5" stopColor="var(--flow-cool)" stopOpacity="0.8" />
                <stop offset="1" stopColor="var(--flow-cool)" stopOpacity="0.2" />
              </linearGradient>
              <linearGradient id="hero-dna-b" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="var(--em)" stopOpacity="0.2" />
                <stop offset="0.5" stopColor="var(--em)" stopOpacity="0.9" />
                <stop offset="1" stopColor="var(--em)" stopOpacity="0.2" />
              </linearGradient>
            </defs>

            <path
              className="hero-dna-strand hero-dna-strand-a"
              d="M82 18 C18 70 150 116 82 174 C18 228 150 276 82 344"
              stroke="url(#hero-dna-a)"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              className="hero-dna-strand hero-dna-strand-b"
              d="M238 18 C302 70 170 116 238 174 C302 228 170 276 238 344"
              stroke="url(#hero-dna-b)"
              strokeWidth="3"
              strokeLinecap="round"
            />

            {RUNGS.map((rung, index) => (
              <g key={rung.y} opacity={rung.variant ? 1 : rung.front ? 0.62 : 0.28}>
                <line
                  x1={rung.left}
                  x2={rung.right}
                  y1={rung.y}
                  y2={rung.y}
                  stroke={rung.variant ? 'var(--em)' : 'var(--hero-line)'}
                  strokeWidth={rung.variant ? 2 : 1}
                  strokeDasharray={rung.variant ? undefined : '2 4'}
                />
                <circle
                  cx={rung.left}
                  cy={rung.y}
                  r={rung.variant ? 5 : 3}
                  fill={rung.variant ? 'var(--flow-cool)' : 'var(--hero-glass)'}
                  stroke={rung.variant ? 'var(--flow-cool)' : 'var(--hero-line)'}
                />
                <circle
                  cx={rung.right}
                  cy={rung.y}
                  r={rung.variant ? 5 : 3}
                  fill={rung.variant ? 'var(--em)' : 'var(--hero-glass)'}
                  stroke={rung.variant ? 'var(--em)' : 'var(--hero-line)'}
                />
                {rung.variant && (
                  <text
                    x="160"
                    y={rung.y - 16}
                    textAnchor="middle"
                    fill="var(--hero-ink-3)"
                    fontFamily="var(--mono)"
                    fontSize="9"
                    letterSpacing="0.08em"
                  >
                    QUERY LOCUS
                  </text>
                )}
              </g>
            ))}
          </svg>

          <button
            type="button"
            className="hero-variant-marker"
            onClick={advance}
            aria-label={`Current view: ${active.label}, ${active.value}. Show next representation.`}
            title="Cycle through genomic, transcript, protein, and evidence views"
          >
            <span>{active.marker}</span>
            <small>{active.label}</small>
          </button>

          <div className="hero-variant-readout" aria-live="polite">
            <span>{active.context}</span>
            <strong>{active.value}</strong>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-px" style={{ background: 'var(--hero-line)' }}>
          {REPRESENTATIONS.map((representation, index) => {
            const selected = index === activeIndex
            return (
              <button
                key={representation.key}
                type="button"
                className="hero-variant-step"
                data-selected={selected ? '' : undefined}
                aria-pressed={selected}
                onClick={() => setActiveIndex(index)}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                {representation.label}
              </button>
            )
          })}
        </div>

        <p className="hero-variant-note">
          The same bundled demo, normalized across genome, transcript, protein, and the full evidence stack.
        </p>
      </div>

      <style>{`
        .hero-variant-map {
          border-top: 0.5px solid var(--hero-line);
          border-left: 0.5px solid var(--hero-line);
          padding: 20px 0 0 24px;
        }
        .hero-variant-kicker,
        .hero-variant-demo {
          font-family: var(--mono);
          font-size: 9.5px;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--hero-ink-3);
        }
        .hero-variant-title {
          max-width: 320px;
          margin: 8px 0 0;
          font-family: var(--display);
          font-size: 20px;
          font-weight: 400;
          line-height: 1.2;
          letter-spacing: -0.015em;
          color: var(--hero-ink);
        }
        .hero-variant-demo {
          border-bottom: 0.5px solid var(--em);
          padding-bottom: 3px;
          color: var(--em-deep);
          white-space: nowrap;
        }
        .hero-dna-strand {
          stroke-dasharray: 520;
          stroke-dashoffset: 520;
          animation: hero-dna-draw 1.4s var(--ease-emphasized) forwards;
        }
        .hero-dna-strand-b { animation-delay: 120ms; }
        .hero-variant-marker {
          position: absolute;
          left: 50%;
          top: 50%;
          width: 78px;
          height: 78px;
          transform: translate(-50%, -50%);
          display: grid;
          place-content: center;
          gap: 3px;
          border: 1px solid var(--em);
          border-radius: 50%;
          background: var(--hero-glass);
          color: var(--hero-ink);
          box-shadow: 0 0 0 8px color-mix(in oklab, var(--em) 9%, transparent), var(--elev-1);
          cursor: pointer;
          transition: transform var(--dur-2) var(--ease-emphasized), box-shadow var(--dur-2) var(--ease-standard);
        }
        .hero-variant-marker:hover {
          transform: translate(-50%, -50%) scale(1.05);
          box-shadow: 0 0 0 12px color-mix(in oklab, var(--em) 12%, transparent), var(--elev-2);
        }
        .hero-variant-marker:focus-visible {
          outline: 2px solid var(--em-deep);
          outline-offset: 5px;
        }
        .hero-variant-marker span {
          font-family: var(--mono);
          font-size: 16px;
          font-weight: 500;
          letter-spacing: -0.03em;
        }
        .hero-variant-marker small {
          font-size: 9px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.09em;
          color: var(--em-deep);
        }
        .hero-variant-readout {
          position: absolute;
          right: 0;
          bottom: 28px;
          width: 190px;
          padding: 10px 12px;
          border-left: 2px solid var(--em);
          background: color-mix(in oklab, var(--hero-glass) 92%, transparent);
        }
        .hero-variant-readout span,
        .hero-variant-readout strong {
          display: block;
        }
        .hero-variant-readout span {
          margin-bottom: 4px;
          font-size: 10px;
          color: var(--hero-ink-3);
        }
        .hero-variant-readout strong {
          font-family: var(--mono);
          font-size: 11px;
          font-weight: 500;
          color: var(--hero-ink);
          overflow-wrap: anywhere;
        }
        .hero-variant-step {
          min-height: 48px;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          justify-content: center;
          gap: 2px;
          padding: 7px 9px;
          border: 0;
          background: var(--hero-glass2);
          color: var(--hero-ink-2);
          font-size: 10px;
          font-weight: 600;
          text-align: left;
          cursor: pointer;
          transition: background var(--dur-1) var(--ease-standard), color var(--dur-1) var(--ease-standard);
        }
        .hero-variant-step span {
          font-family: var(--mono);
          font-size: 8.5px;
          font-weight: 500;
          color: var(--hero-ink-3);
        }
        .hero-variant-step:hover,
        .hero-variant-step[data-selected] {
          background: var(--em-tint);
          color: var(--em-deep);
        }
        .hero-variant-step:focus-visible {
          position: relative;
          z-index: 1;
          outline: 2px solid var(--em-deep);
          outline-offset: -2px;
        }
        .hero-variant-note {
          margin: 11px 0 0;
          max-width: 390px;
          font-size: 10.5px;
          line-height: 1.5;
          color: var(--hero-ink-3);
        }
        @keyframes hero-dna-draw {
          to { stroke-dashoffset: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .hero-dna-strand { animation: none; stroke-dashoffset: 0; }
          .hero-variant-marker,
          .hero-variant-step { transition: none; }
        }
      `}</style>
    </aside>
  )
}
