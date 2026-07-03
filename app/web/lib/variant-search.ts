// Freeform search → variant-report routing. Shared by the landing hero search
// and the report-page search so both behave identically: a structured
// "GENE c.…/p.…/rs…" goes straight to the lookup; anything else is sent as a raw
// query for the backend search-input resolver to interpret (gene vs plain text).

const VARIANT_LIKE = /^(c\.|p\.|g\.|m\.|n\.|rs\d|chr|\d+[-:])/i
const BARE_CDNA_LIKE =
  /^\d+(?:[+-]\d+)?(?:[ACGT]>[ACGT]|del(?:[ACGT]+)?|dup(?:[ACGT]+)?|ins[ACGT]+|delins[ACGT]+)$/i
const GENE_LIKE = /^[A-Za-z][A-Za-z0-9-]{1,15}$/

function cleanToken(token: string) {
  return token.trim().replace(/^[("'`]+|[)"'`,.;!?]+$/g, '')
}

function normaliseVariantToken(token: string) {
  const cleaned = cleanToken(token)
  if (!cleaned) return null
  if (VARIANT_LIKE.test(cleaned)) return cleaned
  if (BARE_CDNA_LIKE.test(cleaned)) return `c.${cleaned}`
  return null
}

export function structuredVariantFromText(text: string): { gene: string; variant: string } | null {
  const direct = text.match(/^([A-Za-z][A-Za-z0-9-]+)\s+(.+)$/)
  if (direct) {
    const variant = normaliseVariantToken(direct[2])
    if (variant) return { gene: direct[1].toUpperCase(), variant }
  }

  const tokens = text.split(/\s+/).map(cleanToken).filter(Boolean)
  for (let i = 1; i < tokens.length; i += 1) {
    const gene = tokens[i - 1]
    const variant = normaliseVariantToken(tokens[i])
    if (variant && GENE_LIKE.test(gene)) return { gene: gene.toUpperCase(), variant }
  }
  return null
}

/** Build the `/report` href for a freeform query, or null if the query is empty. */
export function reportHrefForQuery(raw: string): string | null {
  const text = raw.trim()
  if (!text) return null
  const structured = structuredVariantFromText(text)
  const params = structured
    ? new URLSearchParams({ gene: structured.gene, cdna: structured.variant })
    : new URLSearchParams({ q: text })
  return `/report?${params.toString()}`
}

/** Build the primary app search href: structured variants -> /report, free text -> /search. */
export function searchHrefForQuery(raw: string): string | null {
  const text = raw.trim()
  if (!text) return null
  const structured = structuredVariantFromText(text)
  if (structured) return reportHrefForQuery(text)
  return `/search?${new URLSearchParams({ q: text }).toString()}`
}
