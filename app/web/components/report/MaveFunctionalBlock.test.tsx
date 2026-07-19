import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import {
  canonicalMaveScoreSetHref,
  exactMaveStudies,
  MaveFunctionalBlock,
} from '@/components/report/MaveFunctionalBlock'
import type { FunctionalStudy } from '@/lib/backend'

function study(
  scoreSetUrn: string,
  variantUrn: string,
  rawScore: string,
): FunctionalStudy {
  return {
    id: `${scoreSetUrn}:${variantUrn}`,
    url: 'https://attacker.invalid/imported-source-url',
    source_tags: ['mavedb'],
    evidence_codes: [],
    asserted_codes: [],
    origin_kind: 'direct',
    policy_decisions: [],
    score_set_urn: scoreSetUrn,
    variant_urn: variantUrn,
    match_level: 'exact_target_accession_mave_hgvs',
    raw_score: rawScore,
    score_column: 'score',
    score_unit: 'assay_specific_raw',
    target_accession: 'NM_000329.3',
    target_assembly: 'GRCh38',
    mave_hgvs_nt: 'NM_000329.3:c.1301C>T',
    uncertainty_values: [
      {
        column: 'SE',
        source_value: '0.1150',
        parsed_value: '0.115',
        description: 'Source SE',
      },
    ],
    assay_context: 'RPE65 saturation assay',
    method_text: 'Normalized within this assay only.',
    linked_doi_identifiers: ['10.1000/synthetic.mave'],
    linked_publication_identifiers: ['PMID:12345678'],
    deprecated: false,
    provenance: [],
  }
}

describe('MaveFunctionalBlock', () => {
  it('renders every exact score-set match independently with neutral source context', () => {
    const studies = [
      study('urn:mavedb:00000001-a-1', 'urn:mavedb:00000001-a-1#1', '0.1200'),
      study('urn:mavedb:00000002-a-1', 'urn:mavedb:00000002-a-1#1', '1.2300'),
    ]

    const markup = renderToStaticMarkup(
      <MaveFunctionalBlock gene="RPE65" query="NM_000329.3:c.1301C&gt;T" studies={studies} />,
    )

    expect(markup).toContain('2 exact measurements')
    expect(markup).toContain('0.1200')
    expect(markup).toContain('1.2300')
    expect(markup).toContain('Uncurated')
    expect(markup).toContain('no ACMG strength')
    expect(markup).toContain('https://www.mavedb.org/score-sets/urn:mavedb:00000001-a-1')
    expect(markup).toContain('https://doi.org/10.1000/synthetic.mave')
    expect(markup).toContain('https://pubmed.ncbi.nlm.nih.gov/12345678/')
    expect(markup).not.toContain('attacker.invalid')
  })

  it('fails closed on non-exact matches and malformed score-set URNs', () => {
    const valid = study(
      'urn:mavedb:00000001-a-1',
      'urn:mavedb:00000001-a-1#1',
      '0.1200',
    )
    const loose = { ...valid, match_level: 'candidate_text' }
    const inventedExact = { ...valid, match_level: 'exact_attacker_defined' }
    const malformed = { ...valid, score_set_urn: 'urn:mavedb:../../evil' }

    expect(exactMaveStudies([valid, loose, inventedExact, malformed])).toEqual([valid])
    expect(canonicalMaveScoreSetHref('urn:mavedb:00000001-a-1')).toBe(
      'https://www.mavedb.org/score-sets/urn:mavedb:00000001-a-1',
    )
    expect(canonicalMaveScoreSetHref('urn:mavedb:../../evil')).toBeNull()
  })
})
