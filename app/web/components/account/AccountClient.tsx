'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { AuthPanel } from '@/components/auth/AuthPanel'
import { PageHeader } from '@/components/pricing/PageHeader'
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

function AccountStyles() {
  return (
    <style>{`
      .ac-field {
        height: 40px;
        padding: 0 12px;
        border-radius: var(--r-md);
        background: var(--bg-soft);
        border: 0.5px solid var(--line-2);
        color: var(--ink);
        font-size: 13px;
        outline: none;
        min-width: 0;
        width: 100%;
        transition: border-color var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard);
      }
      /* Hover: same teal-axis signal as the rest of the brand surface. */
      .ac-field:hover:not(:focus):not([aria-invalid="true"]) {
        border-color: var(--teal);
      }
      .ac-field:focus-visible,
      .ac-field:focus {
        border-color: var(--teal);
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        outline: none;
      }
      .ac-field[aria-invalid="true"] {
        border-color: var(--err);
      }
      textarea.ac-field {
        height: auto;
        padding: 10px 12px;
        resize: vertical;
      }

      .ac-add-btn {
        height: 40px;
        padding: 0 18px;
        border-radius: var(--r-md);
        border: none;
        background: var(--teal);
        color: #fff;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        white-space: nowrap;
        transition: background var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard),
                    transform var(--dur-1) var(--ease-standard);
      }
      .ac-add-btn:hover:not(:disabled) { background: var(--teal-deep); }
      .ac-add-btn:active:not(:disabled) { transform: translateY(1px); }
      .ac-add-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
      }
      .ac-add-btn:disabled { opacity: 0.55; cursor: not-allowed; }

      .ac-remove-btn {
        background: none;
        border: none;
        color: var(--ink-4);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        padding: 4px 6px;
        border-radius: 5px;
        transition: color var(--dur-1) var(--ease-standard),
                    background var(--dur-1) var(--ease-standard);
      }
      .ac-remove-btn:hover:not(:disabled) {
        color: var(--err);
        background: var(--err-tint);
      }
      .ac-remove-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(184,43,43,0.15);
        color: var(--err);
      }
      .ac-remove-btn:disabled { opacity: 0.4; cursor: not-allowed; }

      /* Inline teal text-button (e.g. "Add ClinVar functional details") —
         teal underline on hover, matches .eamos-text-link / .lnav-link. */
      .ac-text-btn {
        background: none;
        border: none;
        padding: 0;
        cursor: pointer;
        color: var(--teal);
        font-size: 12.5px;
        font-weight: 600;
        text-decoration: underline;
        text-decoration-color: transparent;
        text-decoration-thickness: 1.5px;
        text-underline-offset: 4px;
        transition: text-decoration-color var(--dur-1) var(--ease-standard);
      }
      .ac-text-btn:hover { text-decoration-color: var(--teal); }
      .ac-text-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.18);
        border-radius: 3px;
      }

      /* Inline teal link (e.g. "Upgrade" in plan-status header) — same
         teal-underline hover as .ac-text-btn. */
      .ac-text-link {
        color: var(--teal);
        font-size: 12px;
        font-weight: 600;
        text-decoration: underline;
        text-decoration-color: transparent;
        text-decoration-thickness: 1.5px;
        text-underline-offset: 4px;
        transition: text-decoration-color var(--dur-1) var(--ease-standard);
      }
      .ac-text-link:hover { text-decoration-color: var(--teal); }
      .ac-text-link:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.18);
        border-radius: 3px;
      }

      /* Solid teal CTA Link (action cards in Empty/Notice). Matches the solid
         pricing CTA hover: brightness step. */
      .ac-cta-link {
        display: inline-flex;
        margin-top: 14px;
        padding: 7px 16px;
        border-radius: var(--r-md);
        background: var(--teal);
        color: #fff;
        font-size: 12.5px;
        font-weight: 600;
        text-decoration: none;
        transition: filter var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard),
                    transform var(--dur-1) var(--ease-standard);
      }
      .ac-cta-link:hover { filter: brightness(0.88); }
      .ac-cta-link:active { transform: translateY(1px); }
      .ac-cta-link:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
      }

      /* Evidence-code toggle pills (PS3, BS3, etc.) — when not active, the
         border lifts to teal on hover. Active state already carries the teal
         border baseline. */
      .ac-evcode-pill {
        font-family: var(--mono);
        font-size: 11px;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 100px;
        cursor: pointer;
        background: var(--bg);
        color: var(--ink-3);
        border: 0.5px solid var(--line);
        transition: background var(--dur-1) var(--ease-standard),
                    border-color var(--dur-1) var(--ease-standard),
                    color var(--dur-1) var(--ease-standard);
      }
      .ac-evcode-pill[aria-pressed="true"] {
        background: var(--teal-tint);
        color: var(--teal-deep);
        border-color: var(--teal);
      }
      .ac-evcode-pill:hover:not([aria-pressed="true"]) {
        border-color: var(--teal);
        color: var(--ink);
      }
      .ac-evcode-pill:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.22);
      }
    `}</style>
  )
}

export function AccountClient() {
  const { configured, loading, user } = useAuth()

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <AccountStyles />
      <PageHeader tone="light" />
      <main
        className="mx-auto px-6 pb-28 pt-12"
        style={{ maxWidth: 920 }}
        aria-busy={loading ? 'true' : undefined}
      >
        {!configured ? (
          <Notice>
            Auth is not configured in this environment. Set{' '}
            <code>NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
            <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to enable accounts.
          </Notice>
        ) : loading ? (
          <AccountSkeleton />
        ) : user ? (
          <Dashboard userId={user.id} email={user.email ?? ''} />
        ) : (
          <SignedOut />
        )}
      </main>
    </div>
  )
}

// Account nav comes from the shared PageHeader primitive — same geometry as
// LandingNav (logo left, links centered, AuthMenu right) so the brand surfaces
// read as one system. The bespoke ProductNav this replaced used a
// justify-between layout that pushed everything right of the logo.

function SignedOut() {
  const router = useRouter()
  return (
    <div className="mx-auto" style={{ maxWidth: 420 }}>
      <h1
        className="mb-2 text-center"
        style={{
          fontFamily: 'var(--display)',
          fontWeight: 400,
          fontSize: 28,
          color: 'var(--ink)',
          letterSpacing: '-0.02em',
        }}
      >
        Sign in to continue
      </h1>
      <p
        className="mb-8 text-center"
        style={{ fontSize: 14, color: 'var(--ink-3)', lineHeight: 1.6 }}
      >
        Track variants and manage your ClinVar evidence submissions.
      </p>
      <div
        style={{
          background: 'var(--bg)',
          border: '0.5px solid var(--line)',
          borderRadius: 'var(--r-lg)',
          boxShadow: 'var(--elev-2)',
        }}
      >
        {/* X / Cancel route back to the landing — /account on its own is a
            sign-in gate, so 'close' has to mean 'leave the gate'. */}
        <AuthPanel onClose={() => router.push('/')} tone="light" />
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
    // False positive: refresh() only setState()s after an awaited fetch, so this
    // is the standard load-on-mount sync, not a synchronous cascading render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
  }, [refresh])

  return (
    <>
      {/* Plan status header */}
      <PlanStatusHeader email={email} />

      {dataError && (
        <Notice tone="warn">
          Could not load your data:{' '}
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{dataError}</span>
          <br />
          If this is a permission error, apply{' '}
          <code>supabase/migrations/0002_grant_authenticated.sql</code>.
        </Notice>
      )}

      <SavedVariants userId={userId} rows={saved} onChange={refresh} />
      <Submissions userId={userId} rows={subs} onChange={refresh} />
    </>
  )
}

function PlanStatusHeader({ email }: { email: string }) {
  return (
    <header
      className="mb-8"
      style={{
        borderRadius: 'var(--r-lg)',
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        padding: '24px 28px',
        boxShadow: 'var(--elev-1)',
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
              color: 'var(--ink-4)',
              margin: 0,
            }}
          >
            Account
          </p>
          <h1
            className="mt-2 truncate"
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 26,
              color: 'var(--ink)',
              letterSpacing: '-0.02em',
              margin: 0,
            }}
          >
            Your workspace
          </h1>
          <p
            className="mt-1.5 truncate"
            style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-3)' }}
          >
            {email}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <span
            style={{
              display: 'inline-block',
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              fontWeight: 600,
              padding: '4px 10px',
              borderRadius: 100,
              background: 'var(--teal-tint)',
              color: 'var(--teal-deep)',
              border: '0.5px solid var(--teal)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Free plan
          </span>
          <div className="mt-2">
            <Link href="/#pricing" className="ac-text-link">
              Upgrade
            </Link>
          </div>
        </div>
      </div>
    </header>
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
  const [removingId, setRemovingId] = useState<string | null>(null)

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

  const handleRemove = async (id: string, hgvsLabel: string) => {
    if (removingId) return
    setRemovingId(id)
    try {
      await deleteSavedVariant(id)
      await onChange()
    } catch {
      // onChange will refresh; on error leave the row in place
    } finally {
      setRemovingId(null)
    }
  }

  return (
    <Section title="Saved variants" subtitle="Bookmark variants to track for reclassification.">
      <form onSubmit={submit} className="flex flex-col gap-2.5 sm:flex-row">
        <input
          value={hgvs}
          onChange={(e) => setHgvs(e.target.value)}
          placeholder="Variant HGVS — e.g. NM_000257.4:c.1208G>A"
          aria-label="Variant HGVS"
          className="ac-field"
          style={{ flex: 1.4, fontFamily: 'var(--mono)' }}
        />
        <input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Note (optional)"
          aria-label="Note"
          className="ac-field"
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={busy} aria-busy={busy} className="ac-add-btn">
          {busy ? 'Saving…' : 'Save'}
        </button>
      </form>
      {err && (
        <p style={{ color: 'var(--err)', fontSize: 12, marginTop: 8 }} role="alert">
          {err}
        </p>
      )}

      <div className="mt-4 flex flex-col gap-2">
        {rows === null ? (
          <RowSkeleton count={2} />
        ) : rows.length === 0 ? (
          <EmptyState
            heading="No saved variants"
            body="Search for a variant on the homepage and bookmark it to track reclassification."
            action={{ label: 'Search variants', href: '/' }}
          />
        ) : (
          rows.map((r) => (
            <div key={r.id} style={rowStyle}>
              <div className="min-w-0">
                <p
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 13,
                    color: 'var(--ink)',
                    margin: 0,
                    wordBreak: 'break-all',
                  }}
                >
                  {r.variant_hgvs}
                </p>
                {r.custom_notes && (
                  <p style={{ fontSize: 12, color: 'var(--ink-3)', margin: '3px 0 0' }}>
                    {r.custom_notes}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <time style={{ fontSize: 11, color: 'var(--ink-4)' }}>
                  {fmtDate(r.created_at)}
                </time>
                <button
                  type="button"
                  onClick={() => handleRemove(r.id, r.variant_hgvs)}
                  disabled={removingId === r.id}
                  aria-busy={removingId === r.id}
                  aria-label={`Remove ${r.variant_hgvs}`}
                  className="ac-remove-btn"
                >
                  {removingId === r.id ? 'Removing…' : 'Remove'}
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
        setOkMsg(`Saved ${res.trackingId} as a draft — add curator fields to complete the ClinVar payload.`)
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
      title="Evidence submissions"
      subtitle="Log supporting literature (PS3/BS3) for routing to ClinVar. Each submission is recorded in your audit ledger."
    >
      <form onSubmit={submit} className="flex flex-col gap-2.5" noValidate>
        <div className="flex flex-col gap-2.5 sm:flex-row">
          <input
            value={hgvs}
            onChange={(e) => setHgvs(e.target.value)}
            placeholder="Variant HGVS — e.g. NM_000257.4:c.1208G>A"
            aria-label="Variant HGVS"
            required
            className="ac-field"
            style={{ flex: 1.4, fontFamily: 'var(--mono)' }}
          />
          <input
            value={pmid}
            onChange={(e) => setPmid(e.target.value)}
            placeholder="Supporting PMID"
            aria-label="Supporting PMID"
            inputMode="numeric"
            required
            className="ac-field"
            style={{ flex: 1, fontFamily: 'var(--mono)' }}
          />
        </div>
        <textarea
          value={curatorNotes}
          onChange={(e) => setCuratorNotes(e.target.value)}
          placeholder="Curator rationale (optional) — why this evidence supports the classification."
          aria-label="Curator rationale"
          rows={3}
          className="ac-field"
        />

        {EVIDENCE_API_ENABLED && (
          <div
            style={{
              borderRadius: 'var(--r-md)',
              border: '0.5px solid var(--line)',
              background: 'var(--bg-soft)',
              padding: '12px 14px',
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setShowDetails((v) => !v)}
                className="ac-text-btn"
              >
                {showDetails ? 'Hide ClinVar details' : 'Add ClinVar functional details'}
              </button>
              <ReadinessChip ready={readiness.ready} missing={readiness.missing} />
            </div>

            {showDetails && (
              <div className="mt-3 flex flex-col gap-2.5">
                <div className="grid gap-2.5 sm:grid-cols-2">
                  <input
                    value={conditionName}
                    onChange={(e) => setConditionName(e.target.value)}
                    placeholder="Condition — e.g. Leber congenital amaurosis"
                    aria-label="Condition name"
                    className="ac-field"
                  />
                  <input
                    value={assayType}
                    onChange={(e) => setAssayType(e.target.value)}
                    placeholder="Assay type — e.g. minigene splicing assay"
                    aria-label="Assay type"
                    className="ac-field"
                  />
                  <select
                    value={collectionMethod}
                    onChange={(e) => setCollectionMethod(e.target.value as CollectionMethod | '')}
                    aria-label="Collection method"
                    className="ac-field"
                  >
                    <option value="">Collection method…</option>
                    <option value="in vitro">in vitro</option>
                    <option value="in vivo">in vivo</option>
                  </select>
                  <select
                    value={functionalEffect}
                    onChange={(e) => setFunctionalEffect(e.target.value as FunctionalEffect | '')}
                    aria-label="Functional effect"
                    className="ac-field"
                  >
                    <option value="">Functional effect…</option>
                    <option value="functionally abnormal">functionally abnormal</option>
                    <option value="function uncertain">function uncertain</option>
                    <option value="functionally normal">functionally normal</option>
                  </select>
                  <input
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                    placeholder="Method — e.g. RT-PCR of patient mRNA"
                    aria-label="Method"
                    className="ac-field"
                  />
                  <input
                    value={result}
                    onChange={(e) => setResult(e.target.value)}
                    placeholder="Result — e.g. exon 1 skipping"
                    aria-label="Result"
                    className="ac-field"
                  />
                </div>
                <input
                  value={functionalConsequence}
                  onChange={(e) => setFunctionalConsequence(e.target.value)}
                  placeholder="Functional consequence (comma-separated) — e.g. abnormal protein, loss of function"
                  aria-label="Functional consequence"
                  className="ac-field"
                />
                <div className="flex flex-wrap items-center gap-1.5">
                  <span style={{ fontSize: 11.5, color: 'var(--ink-4)', marginRight: 4 }}>
                    Evidence codes:
                  </span>
                  {EVIDENCE_CODES.map((code) => {
                    const on = evidenceCodes.includes(code)
                    return (
                      <button
                        key={code}
                        type="button"
                        onClick={() =>
                          setEvidenceCodes((prev) =>
                            prev.includes(code)
                              ? prev.filter((c) => c !== code)
                              : [...prev, code],
                          )
                        }
                        aria-pressed={on}
                        className="ac-evcode-pill"
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

        <div className="flex items-center gap-3 flex-wrap">
          <button type="submit" disabled={busy} aria-busy={busy} className="ac-add-btn">
            {busy ? 'Submitting…' : 'Submit evidence'}
          </button>
          <span
            aria-live="polite"
            aria-atomic="true"
            style={{ fontSize: 12.5, color: 'var(--teal-deep)', minHeight: '1em' }}
          >
            {okMsg ?? ''}
          </span>
        </div>
      </form>
      {err && (
        <p style={{ color: 'var(--err)', fontSize: 12, marginTop: 8 }} role="alert">
          {err}
        </p>
      )}

      <div className="mt-4 flex flex-col gap-2">
        {rows === null ? (
          <RowSkeleton count={2} />
        ) : rows.length === 0 ? (
          <EmptyState
            heading="No submissions yet"
            body="Add a variant HGVS and supporting PMID above to log your first evidence submission."
          />
        ) : (
          rows.map((r) => (
            <div key={r.id} style={{ ...rowStyle, alignItems: 'flex-start' }}>
              <div className="min-w-0">
                <p
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: 13,
                    color: 'var(--ink)',
                    margin: 0,
                    wordBreak: 'break-all',
                  }}
                >
                  {r.variant_hgvs}
                </p>
                <p style={{ fontSize: 12, color: 'var(--ink-3)', margin: '3px 0 0' }}>
                  PMID{' '}
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${r.submitted_pmid}/`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'var(--teal)', textDecoration: 'none', fontWeight: 600 }}
                  >
                    {r.submitted_pmid}
                  </a>
                  {r.curator_notes ? ` · ${r.curator_notes}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <TrackingBadge id={r.clinvar_tracking_id} />
                <time style={{ fontSize: 11, color: 'var(--ink-4)' }}>
                  {fmtDate(r.created_at)}
                </time>
              </div>
            </div>
          ))
        )}
      </div>
    </Section>
  )
}

// ── shared bits ─────────────────────────────────────────────────────────────
function Section({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <section
      className="mb-6"
      style={{
        borderRadius: 'var(--r-lg)',
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        padding: '24px 24px 26px',
        boxShadow: 'var(--elev-1)',
      }}
    >
      <h2
        style={{
          fontFamily: 'var(--display)',
          fontWeight: 400,
          fontSize: 18,
          color: 'var(--ink)',
          margin: 0,
          letterSpacing: '-0.01em',
        }}
      >
        {title}
      </h2>
      <p
        className="mt-1.5 mb-4"
        style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-3)' }}
      >
        {subtitle}
      </p>
      {children}
    </section>
  )
}

function Notice({
  children,
  tone = 'info',
}: {
  children: React.ReactNode
  tone?: 'info' | 'warn'
}) {
  const warn = tone === 'warn'
  return (
    <div
      style={{
        borderRadius: 'var(--r-md)',
        padding: '14px 16px',
        background: warn ? 'var(--warn-tint)' : 'var(--bg-soft)',
        border: `0.5px solid ${warn ? 'var(--warn-bdr)' : 'var(--line)'}`,
        color: warn ? 'var(--warn)' : 'var(--ink-2)',
        fontSize: 13,
        lineHeight: 1.55,
        marginBottom: 20,
      }}
    >
      {children}
    </div>
  )
}

function EmptyState({
  heading,
  body,
  action,
}: {
  heading: string
  body: string
  action?: { label: string; href: string }
}) {
  return (
    <div
      style={{
        padding: '24px 16px',
        textAlign: 'center',
        borderRadius: 'var(--r-md)',
        border: '0.5px dashed var(--line)',
        background: 'var(--bg-soft)',
      }}
    >
      <p
        style={{
          fontSize: 13.5,
          fontWeight: 600,
          color: 'var(--ink-2)',
          margin: 0,
        }}
      >
        {heading}
      </p>
      <p
        style={{
          fontSize: 13,
          color: 'var(--ink-3)',
          margin: '6px 0 0',
          lineHeight: 1.55,
          maxWidth: 380,
          marginLeft: 'auto',
          marginRight: 'auto',
        }}
      >
        {body}
      </p>
      {action && (
        <Link href={action.href} className="ac-cta-link">
          {action.label}
        </Link>
      )}
    </div>
  )
}

function RowSkeleton({ count }: { count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 56,
            borderRadius: 'var(--r-md)',
            background: 'var(--bg-soft2)',
            border: '0.5px solid var(--line)',
            opacity: 1 - i * 0.25,
          }}
          aria-hidden="true"
        />
      ))}
    </>
  )
}

function AccountSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      {[1, 2].map((i) => (
        <div
          key={i}
          style={{
            borderRadius: 'var(--r-lg)',
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            padding: '24px 24px 26px',
            boxShadow: 'var(--elev-1)',
          }}
        >
          <div
            style={{
              height: 20,
              width: '40%',
              borderRadius: 6,
              background: 'var(--bg-soft2)',
              marginBottom: 12,
            }}
          />
          <div
            style={{
              height: 56,
              borderRadius: 'var(--r-md)',
              background: 'var(--bg-soft2)',
              opacity: 0.6,
            }}
          />
        </div>
      ))}
    </div>
  )
}

function TrackingBadge({ id }: { id: string }) {
  const pending = id === 'PENDING'
  return (
    <span
      style={{
        fontFamily: 'var(--mono)',
        fontSize: 10.5,
        fontWeight: 600,
        padding: '3px 8px',
        borderRadius: 100,
        background: pending ? 'var(--warn-tint)' : 'var(--teal-tint)',
        color: pending ? 'var(--warn)' : 'var(--teal-deep)',
        border: `0.5px solid ${pending ? 'var(--warn-bdr)' : 'var(--teal)'}`,
        whiteSpace: 'nowrap' as const,
      }}
    >
      {id}
    </span>
  )
}

function ReadinessChip({ ready, missing }: { ready: boolean; missing: string[] }) {
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        padding: '3px 9px',
        borderRadius: 100,
        background: ready ? 'var(--teal-tint)' : 'var(--warn-tint)',
        color: ready ? 'var(--teal-deep)' : 'var(--warn)',
        border: `0.5px solid ${ready ? 'var(--teal)' : 'var(--warn-bdr)'}`,
      }}
    >
      {ready ? 'Ready for ClinVar dry-run' : `Draft: needs ${missing.join(', ')}`}
    </span>
  )
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

// ── styles ─────────────────────────────────────────────────────────────────
const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 14,
  padding: '12px 14px',
  borderRadius: 'var(--r-md)',
  background: 'var(--bg-soft)',
  border: '0.5px solid var(--line)',
}
