import { describe, expect, it } from 'vitest'

import { safeExportHref } from './report-html'

describe('rich report export links', () => {
  it('allows only absolute HTTP(S) source links', () => {
    expect(safeExportHref('https://example.org/source')).toBe(
      'https://example.org/source',
    )
    expect(safeExportHref('http://example.org/source')).toBe(
      'http://example.org/source',
    )
    expect(safeExportHref('javascript:alert(1)')).toBeNull()
    expect(safeExportHref('data:text/html,unsafe')).toBeNull()
    expect(safeExportHref('/relative/source')).toBeNull()
  })
})
