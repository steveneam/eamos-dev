interface CompositeVerdictBarProps {
  selectionAccounting?: string | null
}

export function computationalAccountingItems(value?: string | null): string[] {
  return (value ?? '')
    .split('|')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function CompositeVerdictBar({ selectionAccounting }: CompositeVerdictBarProps) {
  const items = computationalAccountingItems(selectionAccounting)
  if (items.length === 0) return null

  return (
    <aside
      aria-label={`Computational evidence accounting: ${items.join('; ')}`}
      style={{
        marginBottom: 16,
        borderTop: '0.5px solid var(--line)',
        borderBottom: '0.5px solid var(--line)',
        background: 'var(--bg-soft)',
        padding: '10px 12px',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '5px 12px',
          alignItems: 'center',
          fontSize: 11,
          color: 'var(--ink-2)',
        }}
      >
        <span className="eamos-kicker" style={{ color: 'var(--teal-deep)' }}>
          Evidence accounting
        </span>
        {items.map((item) => (
          <span key={item} style={{ fontFamily: 'var(--mono)' }}>
            {item}
          </span>
        ))}
      </div>
    </aside>
  )
}
