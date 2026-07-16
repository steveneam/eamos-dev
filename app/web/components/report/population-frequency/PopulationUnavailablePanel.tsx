export function PopulationUnavailablePanel({
  title,
  compact = false,
}: {
  title: string
  compact?: boolean
}) {
  return (
    <div
      style={{
        minHeight: compact ? 118 : 180,
        border: '0.5px dashed var(--line-2)',
        borderRadius: 8,
        background: 'var(--bg-soft)',
        color: 'var(--ink-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 14,
        fontSize: 12,
      }}
    >
      {title}
    </div>
  )
}
