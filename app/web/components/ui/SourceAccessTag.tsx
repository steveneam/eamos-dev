export type SourceAccess = 'Public' | 'License review'

/** Source availability, deliberately separate from clinical evidence strength. */
export function SourceAccessTag({ access }: { access: SourceAccess }) {
  const gated = access === 'License review'
  return (
    <span
      title={
        gated
          ? 'This source can render only when its license and backend launch gate allow distribution.'
          : 'This tool or source can render in public mode when backend row metadata allows it.'
      }
      style={{
        fontSize: 9.5,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        padding: '0.5px 5px',
        borderRadius: 999,
        border: `0.5px solid ${gated ? 'var(--warn-bdr)' : 'var(--teal-bdr)'}`,
        background: gated ? 'var(--warn-tint)' : 'var(--teal-tint)',
        color: gated ? 'var(--warn-text)' : 'var(--teal-deep)',
        whiteSpace: 'nowrap',
      }}
    >
      {access}
    </span>
  )
}
