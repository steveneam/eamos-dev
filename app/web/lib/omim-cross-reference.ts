import type { OmimCrossReference } from './backend'
import { sourceFactActionAllowed } from './source-fact-policy'

const OMIM_IDENTIFIER = /^OMIM:([0-9]{6})$/
const OMIM_PHENOTYPE_SUPPLIERS = new Set([
  'clingen_gene_validity',
  'gencc_download',
  'human_phenotype_ontology',
  'mondo_disease_ontology',
])

export function safeOmimCrossReferenceHref(
  identifier: string,
  references: readonly OmimCrossReference[] | null | undefined,
): string | null {
  const match = OMIM_IDENTIFIER.exec(identifier)
  if (!match) return null
  const expectedUrl = `https://omim.org/entry/${match[1]}`
  const reference = (references ?? []).find(
    (candidate) =>
      candidate.identifier === identifier &&
      candidate.identifier_namespace === 'OMIM' &&
      candidate.origin_kind === 'cross_reference' &&
      candidate.external_link_provider === 'omim_web' &&
      candidate.external_url === expectedUrl &&
      candidate.evidence_role === 'identifier_only' &&
      typeof candidate.source_id === 'string' &&
      OMIM_PHENOTYPE_SUPPLIERS.has(candidate.source_id) &&
      candidate.entry_type === 'phenotype' &&
      typeof candidate.source_record_id === 'string' &&
      candidate.source_record_id.length > 0 &&
      sourceFactActionAllowed(candidate, 'public_serialize'),
  )
  return reference ? expectedUrl : null
}

export function omimCrossReferenceOrigins(
  identifiers: readonly string[],
  references: readonly OmimCrossReference[] | null | undefined,
): string[] {
  const identifierSet = new Set(identifiers)
  const origins = (references ?? [])
    .filter(
      (reference) =>
        identifierSet.has(reference.identifier) &&
        safeOmimCrossReferenceHref(reference.identifier, [reference]) !== null,
    )
    .map(
      (reference) =>
        reference.attribution?.trim() || reference.source_id?.trim() || '',
    )
    .filter((origin) => origin.length > 0)
  return Array.from(new Set(origins))
}
