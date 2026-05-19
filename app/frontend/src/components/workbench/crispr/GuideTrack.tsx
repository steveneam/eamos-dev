import { useMemo } from 'react'
import type { CrisprGuide } from '@/lib/backend'
import { mapGuide } from '@/lib/workbench/crispr-guide-map'

interface GuideTrackProps {
  guide: CrisprGuide
  /** Design template the guides were scored against (ssODN reference arm). */
  template: string | null
}

/**
 * The Blueprint-1 signature: a row-hover ribbon painting the spacer (teal)
 * and PAM (amber) onto the design template, with the predicted Cas9 blunt
 * cut marked. Falls back to a standalone spacer+PAM strip when the guide
 * cannot be located in the template (or none was returned). Hand-rolled —
 * no charting/track dependency, same monospace vocabulary as the aligner.
 */
export function GuideTrack({ guide, template }: GuideTrackProps) {
  const m = useMemo(
    () => (template ? mapGuide(guide, template) : null),
    [guide, template],
  )

  if (!template || !m || !m.located) {
    // Standalone strip: spacer + PAM as returned, no template anchor.
    const spacer = guide.guide.toUpperCase()
    return (
      <div className="guide-track" role="img" aria-label={`Guide ${guide.index} spacer and PAM`}>
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
          <span><i className="sw spacer" /> spacer (20 nt)</span>
          <span><i className="sw pam" /> {guide.pam} PAM</span>
          <span className="gt-note">
            {template ? 'not located in template — strand-only view' : 'no design template'}
          </span>
        </div>
      </div>
    )
  }

  const bases = template.toUpperCase().split('')
  return (
    <div
      className="guide-track"
      role="img"
      aria-label={`Guide ${guide.index} mapped onto the design template; cut at base ${m.cutIndex}`}
    >
      <div className="gt-strip">
        {bases.map((b, i) => {
          const inSpacer = i >= m.spacerStart && i < m.spacerEnd
          const inPam =
            m.pamStart != null && i >= m.pamStart && i < (m.pamEnd as number)
          const cls = inSpacer ? 'gt-base spacer' : inPam ? 'gt-base pam' : 'gt-base'
          return (
            <span key={i} className={cls}>
              {m.cutIndex === i && <i className="gt-cut" aria-hidden="true" />}
              {b}
            </span>
          )
        })}
      </div>
      <div className="gt-legend">
        <span><i className="sw spacer" /> spacer ({m.spacerEnd - m.spacerStart} nt)</span>
        <span><i className="sw pam" /> {guide.pam} PAM</span>
        <span><i className="sw cut" /> predicted blunt cut</span>
        <span className="gt-note">
          {guide.strand === '-' ? 'reverse strand (revComp shown on +)' : 'forward strand'}
        </span>
      </div>
    </div>
  )
}
