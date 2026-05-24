'use client'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { PageHeader } from '@/components/pricing/PageHeader'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { useAuth } from '@/components/auth/AuthProvider'
import {
  addSavedVariant,
  clinvarReadiness,
  deleteSavedVariant,
  EVIDENCE_API_ENABLED,
  listSavedVariants,
  listSubmissions,
  submitEvidence,
  type CollectionMethod,
  type EvidenceCode,
  type EvidenceSubmission,
  type EvidenceSubmissionInput,
  type FunctionalEffect,
  type SavedVariant,
} from '@/lib/messenger'

export function AccountClient() {
  const { configured, loading, user } = useAuth()

  return (
    <div style={{ background: 'var(--d-bg)', minHeight: '100vh' }}>
      <PageHeader />
      <main className="mx-auto px-6 pb-28 pt-12" style={{ maxWidth: 920 }}>
        {!configured ? (
          <Notice>
            Auth isn’t configured in this environment yet. Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
            <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to enable accounts.
          </Notice>
        ) : loading ? (
          <p style={{ color: 'var(--hero-ink-3)', fontSize: 14 }}>Loading…</p>
        ) : user ? (
          <Dashboard userId={user.id} email={user.email ?? ''} />
        ) : (
          <SignedOut />
        )}
      </main>
    </div>
  )
}

function SignedOut() {
  return (
    <div className="mx-auto" style={{ maxWidth: 420 }}>
      <h1 className="mb-2 text-center" style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 26, color: 'var(--hero-ink)' }}>
        Sign in to your account
      </h1>
      <p className="mb-6 text-center text-[14px]" style={{ color: 'var(--hero-ink-2)' }}>
        Track variants and manage your ClinVar evidence submissions.
      </p>
      <div style={{ borderRadius: 16, background: 'rgba(5,26,19,0.6)', border: '0.5px solid var(--hero-line)' }}>
        <AuthPanel onClose={() => {}} />
      </div>
    </div>
  )
}

function Dashboard({ userId, email }: { userId: string; email: string }) {
  const [saved, setSaved] = useState<SavedVariant[] | null>(null)
  const [subs, setSubs] = useState<EvidenceSubmission[] | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [s, u] = await Promise.all([listSavedVariants(), listSubmissions()])
      setSaved(s)
      setSubs(u)
      setDataError(null)
    } catch (e) {
      setDataError(e instanceof Error ? e.message : 'Could not load your data.')
      setSaved([])
      setSubs([])
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <>
      <header className="mb-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: 'var(--em-bright)' }}>
          Account
        </p>
        <h1 className="mt-2" style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 30, color: 'var(--hero-ink)' }}>
          Your workspace
        </h1>
        <p className="mt-1.5 text-[13.5px]" style={{ color: 'var(--hero-ink-3)' }}>{email}</p>
      </header>

      {dataError && (
        <Notice tone="warn">
          Couldn’t reach your data: <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{dataError}</span>
          <br />
          If this is a permission error, apply <code>supabase/migrations/0002_grant_authenticated.sql</code> (grants the
          signed-in role access to its own rows).
        </Notice>
      )}

      <SavedVariants userId={userId} rows={saved} onChange={refresh} />
      <Submissions userId={userId} rows={subs} onChange={refresh} />
    </>
  )
}

// ── Saved variants ────────────────────────────────────────────────────────────
function SavedVariants({
  userId,
  rows,
  onChange,
}: {
  userId: string
  rows: SavedVariant[] | null
  onChange: () => Promise<void>
}) {
  const [hgvs, setHgvs] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!hgvs.trim()) return
    setBusy(true)
    setErr(null)
    try {
      await addSavedVariant(userId, hgvs.trim(), notes.trim())
      setHgvs('')
      setNotes('')
      await onChange()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not save.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Saved variants" subtitle="Bookmark variants to track for reclassification.">
      <form onSubmit={submit} className="flex flex-col gap-2.5 sm:flex-row">
        <input
          data-tone="dark"
          value={hgvs}
          onChange={(e) => setHgvs(e.target.value)}
          placeholder="Variant HGVS — e.g. NM_000257.4:c.1208G>A"
          style={{ ...fieldStyle, flex: 1.4, fontFamily: 'var(--mono)' }}
        />
        <input
          data-tone="dark"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Note (optional)"
          style={{ ...fieldStyle, flex: 1 }}
        />
        <button type="submit" disabled={busy} style={addBtn}>
          {busy ? 'Saving…' : 'Save'}
        </button>
      </form>
      {err && <p style={{ color: '#fca5a5', fontSize: 12, marginTop: 8 }}>{err}</p>}

      <div className="mt-4 flex flex-col gap-2">
        {rows === null ? (
          <Skeleton />
        ) : rows.length === 0 ? (
          <Empty text="No saved variants yet." />
        ) : (
          rows.map((r) => (
            <div key={r.id} style={rowStyle}>
              <div className="min-w-0">
                <p style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--hero-ink)', margin: 0, wordBreak: 'break-all' }}>
                  {r.variant_hgvs}
                </p>
                {r.custom_notes && (
                  <p style={{ fontSize: 12, color: 'var(--hero-ink-3)', margin: '3px 0 0' }}>{r.custom_notes}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <time style={{ fontSize: 11, color: 'var(--hero-ink-3)' }}>{fmtDate(r.created_at)}</time>
                <button
                  type="button"
                  onClick={async () => {
                    await deleteSavedVariant(r.id)
                    await onChange()
                  }}
                  aria-label="Remove"
                  style={delBtn}
                >
                  Remove
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Section>
  )
}

// ── Evidence submissions (Messenger) ───────────────────────────────────────────
const EVIDENCE_CODES: EvidenceCode[] = ['PS3', 'BS3', 'PS3_Supporting', 'BS3_Supporting', 'Other']

function Submissions({
  userId,
  rows,
  onChange,
}: {
  userId: string
  rows: EvidenceSubmission[] | null
  onChange: () => Promise<void>
}) {
  const [hgvs, setHgvs] = useState('')
  const [pmid, setPmid] = useState('')
  const [curatorNotes, setCuratorNotes] = useState('')
  // ClinVar functional-evidence detail — only collected/sent when the live API
  // path is enabled (NEXT_PUBLIC_EVIDENCE_API_ENABLED). Default form is unchanged.
  const [showDetails, setShowDetails] = useState(false)
  const [conditionName, setConditionName] = useState('')
  const [assayType, setAssayType] = useState('')
  const [collectionMethod, setCollectionMethod] = useState<CollectionMethod | ''>('')
  const [functionalEffect, setFunctionalEffect] = useState<FunctionalEffect | ''>('')
  const [functionalConsequence, setFunctionalConsequence] = useState('')
  const [method, setMethod] = useState('')
  const [result, setResult] = useState('')
  const [evidenceCodes, setEvidenceCodes] = useState<EvidenceCode[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)

  const buildInput = (): EvidenceSubmissionInput => ({
    variant_hgvs: hgvs.trim(),
    submitted_pmid: pmid.trim(),
    curator_notes: curatorNotes.trim(),
    condition_name: conditionName.trim(),
    assay_type: assayType.trim(),
    collection_method: collectionMethod || undefined,
    functional_effect: functionalEffect || undefined,
    functional_consequence: functionalConsequence.trim()
      ? functionalConsequence.split(',').map((s) => s.trim()).filter(Boolean)
      : [],
    method: method.trim(),
    result: result.trim(),
    evidence_codes: evidenceCodes,
  })

  const readiness = clinvarReadiness(buildInput())

  const resetForm = () => {
    setHgvs('')
    setPmid('')
    setCuratorNotes('')
    setConditionName('')
    setAssayType('')
    setCollectionMethod('')
    setFunctionalEffect('')
    setFunctionalConsequence('')
    setMethod('')
    setResult('')
    setEvidenceCodes([])
    setShowDetails(false)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!hgvs.trim() || !pmid.trim()) {
      setErr('Variant HGVS and a supporting PMID are required.')
      return
    }
    setBusy(true)
    setErr(null)
    setOkMsg(null)
    try {
      const res = await submitEvidence(userId, buildInput())
      resetForm()
      if (res.payloadStatus === null) {
        setOkMsg('Logged — tracking ID pending.')
      } else if (res.payloadStatus === 'ready_for_clinvar_dry_run') {
        setOkMsg(`Recorded ${res.trackingId} — ready for ClinVar dry-run.`)
      } else {
        setOkMsg(`Saved ${res.trackingId} as a draft — add the curator fields to complete the ClinVar payload.`)
      }
      await onChange()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not submit.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Evidence submissions — Messenger"
      subtitle="Log supporting literature (PS3/BS3) for onward routing to ClinVar. Each submission is recorded in your audit ledger."
    >
      <form onSubmit={submit} className="flex flex-col gap-2.5">
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <input
            data-tone="dark"
            value={hgvs}
            onChange={(e) => setHgvs(e.target.value)}
            placeholder="Variant HGVS — e.g. NM_000257.4:c.1208G>A"
            style={{ ...fieldStyle, flex: 1.4, fontFamily: 'var(--mono)' }}
          />
          <input
            data-tone="dark"
            value={pmid}
            onChange={(e) => setPmid(e.target.value)}
            placeholder="Supporting PMID"
            inputMode="numeric"
            style={{ ...fieldStyle, flex: 1, fontFamily: 'var(--mono)' }}
          />
        </div>
        <textarea
          data-tone="dark"
          value={curatorNotes}
          onChange={(e) => setCuratorNotes(e.target.value)}
          placeholder="Curator rationale (optional) — why this evidence supports the classification."
          rows={3}
          style={{ ...fieldStyle, height: 'auto', padding: '10px 12px', resize: 'vertical' }}
        />

        {EVIDENCE_API_ENABLED && (
          <div style={{ borderRadius: 12, border: '0.5px solid var(--hero-line)', background: 'rgba(5,26,19,0.4)', padding: '12px 14px' }}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setShowDetails((v) => !v)}
                style={{ ...delBtn, color: 'var(--em-bright)', fontSize: 12.5 }}
              >
                {showDetails ? '− Hide ClinVar functional details' : '+ Add ClinVar functional details'}
              </button>
              <span style={readinessChip(readiness.ready)}>
                {readiness.ready ? 'Ready for ClinVar dry-run' : `Draft — needs: ${readiness.missing.join(', ')}`}
              </span>
            </div>

            {showDetails && (
              <div className="mt-3 flex flex-col gap-2.5">
                <div className="grid gap-2.5 sm:grid-cols-2">
                  <input
                    data-tone="dark"
                    value={conditionName}
                    onChange={(e) => setConditionName(e.target.value)}
                    placeholder="Condition — e.g. Leber congenital amaurosis"
                    style={fieldStyle}
                  />
                  <input
                    data-tone="dark"
                    value={assayType}
                    onChange={(e) => setAssayType(e.target.value)}
                    placeholder="Assay type — e.g. minigene splicing assay"
                    style={fieldStyle}
                  />
                  <select
                    data-tone="dark"
                    value={collectionMethod}
                    onChange={(e) => setCollectionMethod(e.target.value as CollectionMethod | '')}
                    style={fieldStyle}
                  >
                    <option value="">Collection method…</option>
                    <option value="in vitro">in vitro</option>
                    <option value="in vivo">in vivo</option>
                  </select>
                  <select
                    data-tone="dark"
                    value={functionalEffect}
                    onChange={(e) => setFunctionalEffect(e.target.value as FunctionalEffect | '')}
                    style={fieldStyle}
                  >
                    <option value="">Functional effect…</option>
                    <option value="functionally abnormal">functionally abnormal</option>
                    <option value="function uncertain">function uncertain</option>
                    <option value="functionally normal">functionally normal</option>
                  </select>
                  <input
                    data-tone="dark"
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                    placeholder="Method — e.g. RT-PCR of patient mRNA"
                    style={fieldStyle}
                  />
                  <input
                    data-tone="dark"
                    value={result}
                    onChange={(e) => setResult(e.target.value)}
                    placeholder="Result — e.g. exon 1 skipping"
                    style={fieldStyle}
                  />
                </div>
                <input
                  data-tone="dark"
                  value={functionalConsequence}
                  onChange={(e) => setFunctionalConsequence(e.target.value)}
                  placeholder="Functional consequence (comma-separated) — e.g. abnormal protein, loss of function"
                  style={fieldStyle}
                />
                <div className="flex flex-wrap items-center gap-1.5">
                  <span style={{ fontSize: 11.5, color: 'var(--hero-ink-3)', marginRight: 4 }}>Evidence codes:</span>
                  {EVIDENCE_CODES.map((code) => {
                    const on = evidenceCodes.includes(code)
                    return (
                      <button
                        key={code}
                        type="button"
                        onClick={() =>
                          setEvidenceCodes((prev) =>
                            prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
                          )
                        }
                        style={codeChip(on)}
                      >
                        {code}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button type="submit" disabled={busy} style={addBtn}>
            {busy ? 'Submitting…' : 'Submit evidence'}
          </button>
          {okMsg && <span style={{ fontSize: 12.5, color: 'var(--em-bright)' }}>{okMsg}</span>}
        </div>
      </form>
      {err && <p style={{ color: '#fca5a5', fontSize: 12, marginTop: 8 }}>{err}</p>}

      <div className="mt-4 flex flex-col gap-2">
        {rows === null ? (
          <Skeleton />
        ) : rows.length === 0 ? (
          <Empty text="No submissions yet." />
        ) : (
          rows.map((r) => (
            <div key={r.id} style={{ ...rowStyle, alignItems: 'flex-start' }}>
              <div className="min-w-0">
                <p style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--hero-ink)', margin: 0, wordBreak: 'break-all' }}>
                  {r.variant_hgvs}
                </p>
                <p style={{ fontSize: 12, color: 'var(--hero-ink-3)', margin: '3px 0 0' }}>
                  PMID{' '}
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${r.submitted_pmid}/`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'var(--em-bright)', textDecoration: 'none' }}
                  >
                    {r.submitted_pmid}
                  </a>
                  {r.curator_notes ? ` · ${r.curator_notes}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <span style={trackingBadge(r.clinvar_tracking_id)}>{r.clinvar_tracking_id}</span>
                <time style={{ fontSize: 11, color: 'var(--hero-ink-3)' }}>{fmtDate(r.created_at)}</time>
              </div>
            </div>
          ))
        )}
      </div>
    </Section>
  )
}

// ── shared bits ─────────────────────────────────────────────────────────────
function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section
      className="mb-6"
      style={{ borderRadius: 16, background: 'var(--d-card)', border: '0.5px solid var(--d-line)', padding: '24px 24px 26px' }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 17, color: 'var(--hero-ink)', margin: 0 }}>
        {title}
      </h2>
      <p className="mt-1.5 mb-4 text-[12.5px] leading-[1.55]" style={{ color: 'var(--hero-ink-3)' }}>{subtitle}</p>
      {children}
    </section>
  )
}

function Notice({ children, tone = 'info' }: { children: React.ReactNode; tone?: 'info' | 'warn' }) {
  const warn = tone === 'warn'
  return (
    <div
      style={{
        borderRadius: 12,
        padding: '14px 16px',
        background: warn ? 'rgba(186,117,23,0.12)' : 'var(--hero-glass)',
        border: `0.5px solid ${warn ? 'rgba(250,199,117,0.4)' : 'var(--hero-line)'}`,
        color: 'var(--hero-ink-2)',
        fontSize: 13,
        lineHeight: 1.55,
      }}
    >
      {children}
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <p style={{ fontSize: 13, color: 'var(--hero-ink-3)', padding: '14px 4px', textAlign: 'center' }}>{text}</p>
  )
}

function Skeleton() {
  return <div style={{ height: 48, borderRadius: 10, background: 'var(--hero-glass)', opacity: 0.5 }} />
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

function trackingBadge(id: string): React.CSSProperties {
  const pending = id === 'PENDING'
  return {
    fontFamily: 'var(--mono)',
    fontSize: 10.5,
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: 100,
    background: pending ? 'rgba(186,117,23,0.16)' : 'rgba(16,185,129,0.16)',
    color: pending ? '#fac775' : 'var(--em-bright)',
    border: `0.5px solid ${pending ? 'rgba(250,199,117,0.35)' : 'rgba(52,211,153,0.4)'}`,
    whiteSpace: 'nowrap',
  }
}

function readinessChip(ready: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 9px',
    borderRadius: 100,
    background: ready ? 'rgba(16,185,129,0.16)' : 'rgba(186,117,23,0.14)',
    color: ready ? 'var(--em-bright)' : '#fac775',
    border: `0.5px solid ${ready ? 'rgba(52,211,153,0.4)' : 'rgba(250,199,117,0.32)'}`,
  }
}

function codeChip(on: boolean): React.CSSProperties {
  return {
    fontFamily: 'var(--mono)',
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 9px',
    borderRadius: 100,
    cursor: 'pointer',
    background: on ? 'rgba(16,185,129,0.18)' : 'var(--hero-glass)',
    color: on ? 'var(--em-bright)' : 'var(--hero-ink-3)',
    border: `0.5px solid ${on ? 'rgba(52,211,153,0.45)' : 'var(--hero-line)'}`,
  }
}

const fieldStyle: React.CSSProperties = {
  height: 40,
  padding: '0 12px',
  borderRadius: 10,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink)',
  fontSize: 13,
  outline: 'none',
  minWidth: 0,
  width: '100%',
}
const addBtn: React.CSSProperties = {
  height: 40,
  padding: '0 18px',
  borderRadius: 10,
  border: 'none',
  background: 'var(--em)',
  color: '#04140e',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}
const delBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'var(--hero-ink-3)',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
  padding: 0,
}
const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 14,
  padding: '12px 14px',
  borderRadius: 10,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
}
