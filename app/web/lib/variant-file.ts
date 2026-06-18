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
  chrom?: string | null
  pos?: number | null
  ref?: string | null
  alt?: string | null
  filter?: string | null
  info_af?: number | null
  warnings?: string[]
}

// Client-parse cap for the small-file inline path. Sits under the backend's
// BATCH_MAX_VARIANTS (5000); larger files negotiate a server-side upload+parse.
export const CLIENT_PARSE_VARIANT_LIMIT = 2000

export interface ParseVariantFileResult {
  variants: ParsedVariant[]
  totalParsed: number
  truncated: boolean
  limit: number
}

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
    const [chrom, pos, , ref, altField, , filter] = cols
    if (!chrom || !pos || !ref || !altField || !/^\d+$/.test(pos)) continue
    const info = parseVcfInfo(cols[7])
    const gene = geneFromVcfInfo(info)
    const variant = firstInfoValue(info, ['HGVS_C', 'HGVSC'])
    const normalizedChrom = chrom.replace(/^chr/i, '')
    const normalizedRef = ref.toUpperCase()
    // Multi-allelic ALT (A,T) → take the first ALT for the v1 single row.
    const alt = altField.split(',')[0].toUpperCase()
    const query = `${normalizedChrom}-${pos}-${normalizedRef}-${alt}`
    out.push({
      raw: clip(trimmed),
      gene,
      variant,
      query,
      chrom: normalizedChrom,
      pos: Number(pos),
      ref: normalizedRef,
      alt,
      filter: filter || null,
      info_af: firstAfValue(info),
    })
  }
  return out
}

function parseVcfInfo(raw: string | undefined): Record<string, string | true> {
  const info: Record<string, string | true> = {}
  if (!raw || raw === '.') return info
  for (const item of raw.split(';')) {
    if (!item) continue
    const eq = item.indexOf('=')
    if (eq < 0) {
      info[item.trim().toUpperCase()] = true
      continue
    }
    info[item.slice(0, eq).trim().toUpperCase()] = item.slice(eq + 1).trim()
  }
  return info
}

function decodeInfoValue(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function firstInfoValue(info: Record<string, string | true>, keys: string[]): string | null {
  for (const key of keys) {
    const value = info[key]
    if (typeof value === 'string' && value.trim()) return decodeInfoValue(value.trim())
  }
  return null
}

function firstAfValue(info: Record<string, string | true>): number | null {
  const value = info.AF
  if (typeof value !== 'string') return null
  const first = Number(value.split(',')[0])
  return Number.isFinite(first) && first >= 0 && first <= 1 ? first : null
}

function geneFromVcfInfo(info: Record<string, string | true>): string | null {
  const direct = firstInfoValue(info, ['GENE', 'SYMBOL', 'HGNC_SYMBOL'])
  if (direct) return direct.toUpperCase()
  const ann = info.ANN
  if (typeof ann === 'string' && ann.trim()) {
    const first = ann.split(',', 1)[0]?.split('|')
    const gene = first?.[3]?.trim()
    if (gene) return gene.toUpperCase()
  }
  return null
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

export function parseVariantFileDetailed(
  text: string,
  filename: string,
  limit = CLIENT_PARSE_VARIANT_LIMIT,
): ParseVariantFileResult {
  const parsed = isVcf(text, filename) ? parseVcf(text) : parseList(text)
  const seen = new Set<string>()
  const deduped: ParsedVariant[] = []
  const max = Math.max(1, limit)
  let totalParsed = 0
  for (const v of parsed) {
    const key = v.query.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    totalParsed += 1
    if (deduped.length < max) deduped.push(v)
    if (totalParsed > max) break
  }
  return {
    variants: deduped,
    totalParsed,
    truncated: totalParsed > max,
    limit: max,
  }
}

export function parseVariantFile(text: string, filename: string): ParsedVariant[] {
  return parseVariantFileDetailed(text, filename).variants
}

// sessionStorage handoff between the search bar and /compare.
const COMPARE_KEY = 'eamos.compare.v1'

export type SourceKind = 'file' | 'paste'

/** One input that contributed to the cohort — a dropped/attached file or a paste.
 *  Tracked individually (not merged into one blob) so /compare can show every
 *  source, let a clinician remove one, and view exactly what was typed: source
 *  consistency. The working variant list is derived via mergeSources(). */
export interface ImportSource {
  id: string
  /** File name(s), or "Pasted text". */
  name: string
  kind: SourceKind
  /** Raw pasted text, kept so the user can review exactly what they typed. */
  text?: string
  variants: ParsedVariant[]
  /** True when the browser preview was capped and Generate should prefer upload_ref. */
  clientTruncated?: boolean
  clientParseLimit?: number
  clientParsedCount?: number
}

/** What VariantImport hands back per import (everything but the id, assigned here). */
export interface ImportMeta {
  name: string
  kind: SourceKind
  text?: string
  uploadFile?: File
  clientTruncated?: boolean
  clientParseLimit?: number
  clientParsedCount?: number
}

export interface CompareStash {
  savedAt: number
  /** Derived label (sources joined) — kept for back-compat readers. */
  source: string
  /** Derived deduped working list — kept for back-compat readers. */
  variants: ParsedVariant[]
  sources: ImportSource[]
}

let sourceSeq = 0
export function makeSourceId(): string {
  sourceSeq += 1
  return `src-${Date.now().toString(36)}-${sourceSeq}`
}

/** Flatten sources into the deduped working cohort (first occurrence wins). */
export function mergeSources(sources: ImportSource[]): ParsedVariant[] {
  const seen = new Set<string>()
  const out: ParsedVariant[] = []
  for (const s of sources) {
    for (const v of s.variants) {
      const key = v.query.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      out.push(v)
    }
  }
  return out
}

export function sourcesLabel(sources: ImportSource[]): string {
  return sources.map((s) => s.name).join(' + ')
}

function buildStash(sources: ImportSource[]): CompareStash {
  return { savedAt: Date.now(), source: sourcesLabel(sources), variants: mergeSources(sources), sources }
}

/** Rich write used by /compare — persists the per-source provenance. */
export function stashCompareSources(sources: ImportSource[]): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(COMPARE_KEY, JSON.stringify(buildStash(sources)))
  } catch {
    // sessionStorage unavailable (private mode / quota) — non-fatal.
  }
}

/** Compat write for the other surfaces (search bar, library, paper) that hand
 *  over a merged list + a label: wrapped as a single source. */
export function stashCompareVariants(variants: ParsedVariant[], source: string): void {
  const kind: SourceKind = /paste/i.test(source) ? 'paste' : 'file'
  stashCompareSources([{ id: makeSourceId(), name: source, kind, variants }])
}

export function clearCompareStash(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(COMPARE_KEY)
  } catch {
    // non-fatal
  }
}

export function readCompareVariants(): CompareStash | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(COMPARE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<CompareStash>
    if (!Array.isArray(parsed.variants)) return null
    // Migrate a pre-sources stash (one merged blob) into a single source.
    if (!Array.isArray(parsed.sources)) {
      const name = parsed.source || 'Imported variants'
      const kind: SourceKind = /paste/i.test(name) ? 'paste' : 'file'
      return buildStash([{ id: makeSourceId(), name, kind, variants: parsed.variants }])
    }
    const stash = parsed as CompareStash
    return {
      ...stash,
      sources: stash.sources.map((source) => ({
        ...source,
        clientTruncated: undefined,
        clientParseLimit: undefined,
        clientParsedCount: undefined,
      })),
    }
  } catch {
    return null
  }
}
