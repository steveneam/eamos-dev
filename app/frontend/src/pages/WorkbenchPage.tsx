import { useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import type { WorkbenchTool } from '@/lib/backend'
import { ContextStrip } from '@/components/workbench/ContextStrip'
import { WorkbenchShell } from '@/components/workbench/WorkbenchShell'
import '@/styles/workbench.css'

const DEFAULT_GENE = 'RPE65'
const DEFAULT_CDNA = 'c.260A>G'

// FE-4 ships the shell against the RPE65 fixture (the only variant v2 serves,
// and the mock's subject). Per-variant context metadata is wired in a later
// milestone — same pattern as ReportPage defaulting to the demo payload.
const RPE65_CTX = {
  sub: 'p.Asp87Gly · NM_000329.3 · chr1:68,444,869 T>C · GRCh38 · 21,138 bp gene',
  classification: 'Likely Pathogenic',
  links: [
    { label: 'ClinVar', href: 'https://www.ncbi.nlm.nih.gov/clinvar/variation/99473/' },
    { label: 'gnomAD', href: 'https://gnomad.broadinstitute.org' },
  ],
}

/** Parse "GENE c.123A>G" / "GENE:c.123A>G" → {gene, cdna}, else null. */
function parseQuery(raw: string): { gene: string; cdna: string } | null {
  const s = raw.trim()
  if (!s) return null
  const m = s.match(/^([A-Za-z0-9]+)[\s:]+(.+)$/)
  if (!m) return null
  return { gene: m[1], cdna: m[2].trim() }
}

export function WorkbenchPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  // The shell renders the RPE65 fixture only (see WorkbenchShell `DATA`). The
  // context strip must reflect what's actually on screen — echoing arbitrary
  // URL params here mislabels the RPE65 sequence as another gene/variant.
  const gene = DEFAULT_GENE
  const cdna = DEFAULT_CDNA
  const qs = useMemo(() => {
    const q = params.toString()
    return q ? `?${q}` : ''
  }, [params])

  const [tool, setTool] = useState<WorkbenchTool>('viewer')
  const [search, setSearch] = useState('')

  const onSearch = (e: FormEvent) => {
    e.preventDefault()
    const parsed = parseQuery(search)
    if (parsed) {
      navigate(
        `/workbench?gene=${encodeURIComponent(parsed.gene)}&cdna=${encodeURIComponent(parsed.cdna)}`,
      )
    } else if (search.trim()) {
      navigate(`/report?q=${encodeURIComponent(search.trim())}`)
    }
  }

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <div className="nav-wrap">
        <div className="wrap-wide nav">
          <Link to="/" className="logo" aria-label="Eamos home">
            <svg width="28" height="20" viewBox="0 0 30 22" fill="none" aria-hidden="true">
              <rect x="0" y="2" width="28" height="3" rx="1.5" fill="#0b1a2b" />
              <rect x="0" y="9.5" width="20" height="3" rx="1.5" fill="#0b1a2b" />
              <rect x="0" y="17" width="12" height="3" rx="1.5" fill="#0b1a2b" />
              <circle cx="22.5" cy="11" r="2.8" fill="#1D9E75" />
            </svg>
            <span className="logo-word">
              <span className="e1">e</span>amos
            </span>
            <span className="logo-sub">workbench</span>
          </Link>

          <form className="nav-search" role="search" onSubmit={onSearch}>
            <div className="ns-shell" data-mode="lookup">
              <span className="ns-ic" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="7" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </span>
              <input
                className="ns-input"
                type="text"
                placeholder="Look up another gene or variant…"
                autoComplete="off"
                spellCheck={false}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Look up another gene or variant"
              />
              <button className="ns-submit" type="submit" aria-label="Search">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12,5 19,12 12,19" />
                </svg>
              </button>
            </div>
          </form>

          <div className="nav-actions">
            <div className="mode-pill" role="group" aria-label="View mode">
              <Link to={`/report${qs}`}>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                Report
              </Link>
              <Link to={`/workbench${qs}`} className="active" aria-current="page">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                </svg>
                Workbench
              </Link>
            </div>
          </div>
        </div>
      </div>

      <ContextStrip
        gene={gene}
        variant={cdna}
        sub={RPE65_CTX.sub}
        classification={RPE65_CTX.classification}
        links={RPE65_CTX.links}
      />

      <WorkbenchShell tool={tool} onSelectTool={setTool} />
    </div>
  )
}
