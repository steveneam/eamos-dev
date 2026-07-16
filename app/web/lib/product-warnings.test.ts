import { describe, expect, it } from 'vitest'
import { visibleProductWarnings } from './product-warnings'

describe('visibleProductWarnings', () => {
  it('hides retired access metadata while retaining data-readiness warnings', () => {
    expect(
      visibleProductWarnings([
        'revel_launch_filter_metadata',
        'source_license_review',
        'public_serialization_locked',
        'commercial_gate_pending',
        'alphamissense_missing_source_file',
        'capice_model_artifact_missing',
      ]),
    ).toEqual([
      'alphamissense_missing_source_file',
      'capice_model_artifact_missing',
    ])
  })
})
