// Client-side parse of a dropped/attached variant file into a list of report
// queries. v1 handles the common shapes a clinician drops on the search bar:
// a VCF (CHROM POS ID REF ALT → hg38 genomic query) or a CSV/TSV/plain-text
// list with one variant per line. Full VCF normalization (multi-allelic split,
// liftover, sample/genotype columns) is the batch backend's job — this keeps to
// the FE-ownable parse so the attach → compare flow works today.
import { structuredVariantFromText } from './variant-search'

export interface ParsedVariant {
  /** The raw source line, for display + provenance (truncated if very long). */
  raw: string
  gene: string | null
  variant: string | null
  /** Freeform query string fed to reportHrefForQuery / the lookup. */
  query: string
}

const MAX_VARIANTS = 50

function clip(line: string): string {
  return line.length > 120 ? `${line.slice(0, 117)}…` : line
}

function isVcf(text: string, filename: string): boolean {
  if (/\.vcf$/i.test(filename)) return true
  return /^##fileformat=VCF/im.test(text) || /^#CHROM\s/im.test(text)
}

function parseVcf(text: string): ParsedVariant[] {
  const out: ParsedVariant[] = []
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const cols = trimmed.split(/\s+/)
    if (cols.length < 5) continue
    const [chrom, pos, , ref, altField] = cols
    if (!chrom || !pos || !ref || !altField || !/^\d+$/.test(pos)) continue
    // Multi-allelic ALT (A,T) → take the first ALT for the v1 single row.
    const alt = altField.split(',')[0]
    const query = `${chrom.replace(/^chr/i, '')}-${pos}-${ref}-${alt}`
    out.push({ raw: clip(trimmed), gene: null, variant: null, query })
  }
  return out
}

function parseList(text: string): ParsedVariant[] {
  const out: ParsedVariant[] = []
  for (const rawLine of text.split(/\r?\n/)) {
    let line = rawLine.trim()
    if (!line || line.startsWith('#') || line.startsWith('//')) continue
    // CSV/TSV: collapse the delimited row into a space-joined token stream so
    // the shared structured-variant matcher can pick out gene + HGVS.
    if (/[,\t]/.test(line)) {
      line = line.split(/[,\t]+/).map((s) => s.trim()).filter(Boolean).join(' ')
    }
    // Skip an obvious header row (no variant punctuation present).
    if (/^(gene|variant|hgvs|chrom|chromosome)\b/i.test(line) && !/[.>]/.test(line)) continue
    const structured = structuredVariantFromText(line)
    out.push({
      raw: clip(line),
      gene: structured?.gene ?? null,
      variant: structured?.variant ?? null,
      query: structured ? `${structured.gene} ${structured.variant}` : line,
    })
  }
  return out
}

export function parseVariantFile(text: string, filename: string): ParsedVariant[] {
  const parsed = isVcf(text, filename) ? parseVcf(text) : parseList(text)
  const seen = new Set<string>()
  const deduped: ParsedVariant[] = []
  for (const v of parsed) {
    const key = v.query.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(v)
    if (deduped.length >= MAX_VARIANTS) break
  }
  return deduped
}

// sessionStorage handoff between the search bar and /compare.
const COMPARE_KEY = 'eamos.compare.v1'

export interface CompareStash {
  savedAt: number
  source: string
  variants: ParsedVariant[]
}

export function stashCompareVariants(variants: ParsedVariant[], source: string): void {
  if (typeof window === 'undefined') return
  try {
    const stash: CompareStash = { savedAt: Date.now(), source, variants }
    window.sessionStorage.setItem(COMPARE_KEY, JSON.stringify(stash))
  } catch {
    // sessionStorage unavailable (private mode / quota) — non-fatal.
  }
}

export function readCompareVariants(): CompareStash | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(COMPARE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as CompareStash
    if (!Array.isArray(parsed.variants)) return null
    return parsed
  } catch {
    return null
  }
}
