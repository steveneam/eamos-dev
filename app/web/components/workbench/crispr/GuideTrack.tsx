'use client'

import { useMemo } from 'react'
import type { CrisprGuide } from '@/lib/backend'
import { mapGuide } from '@/lib/workbench/crispr-guide-map'

interface GuideTrackProps {
  guide: CrisprGuide
  /** Design template the guides were scored against, usually ssODN reference arm. */
  template: string | null
  /** The local mapping helper models SpCas9 cut geometry only. */
  showCut: boolean
}

/**
 * Row-hover ribbon painting spacer and PAM onto the design template. The cut
 * marker is shown only when the caller confirms SpCas9 geometry.
 */
export function GuideTrack({ guide, template, showCut }: GuideTrackProps) {
  const m = useMemo(
    () => (template ? mapGuide(guide, template) : null),
    [guide, template],
  )

  if (!template || !m || !m.located) {
    const spacer = guide.guide.toUpperCase()
    return (
      <div
        className="guide-track"
        role="img"
        aria-label={`Guide ${guide.index} spacer and PAM`}
      >
        <div className="gt-strip">
          {spacer.split('').map((b, i) => (
            <span key={`s${i}`} className="gt-base spacer">
              {b}
            </span>
          ))}
          {guide.pam.split('').map((b, i) => (
            <span key={`p${i}`} className="gt-base pam">
              {b}
            </span>
          ))}
        </div>
        <div className="gt-legend">
          <span>
            <i className="sw spacer" /> spacer (20 nt)
          </span>
          <span>
            <i className="sw pam" /> {guide.pam} PAM
          </span>
          <span className="gt-note">
            {template ? 'not located in template; strand-only view' : 'no design template'}
          </span>
        </div>
      </div>
    )
  }

  const bases = template.toUpperCase().split('')
  const ariaLabel = showCut
    ? `Guide ${guide.index} mapped onto the design template; SpCas9 cut at base ${m.cutIndex}`
    : `Guide ${guide.index} mapped onto the design template`

  return (
    <div className="guide-track" role="img" aria-label={ariaLabel}>
      <div className="gt-strip">
        {bases.map((b, i) => {
          const inSpacer = i >= m.spacerStart && i < m.spacerEnd
          const inPam =
            m.pamStart != null && i >= m.pamStart && i < (m.pamEnd as number)
          const cls = inSpacer ? 'gt-base spacer' : inPam ? 'gt-base pam' : 'gt-base'
          return (
            <span key={i} className={cls}>
              {showCut && m.cutIndex === i && (
                <i className="gt-cut" aria-hidden="true" />
              )}
              {b}
            </span>
          )
        })}
      </div>
      <div className="gt-legend">
        <span>
          <i className="sw spacer" /> spacer ({m.spacerEnd - m.spacerStart} nt)
        </span>
        <span>
          <i className="sw pam" /> {guide.pam} PAM
        </span>
        {showCut ? (
          <span>
            <i className="sw cut" /> SpCas9 cut marker
          </span>
        ) : (
          <span className="gt-note">cut marker hidden for non-SpCas9 geometry</span>
        )}
        <span className="gt-note">
          {guide.strand === '-' ? 'reverse strand (revComp shown on +)' : 'forward strand'}
        </span>
      </div>
    </div>
  )
}
