import { cn } from '@/lib/utils'

type Classification =
  | 'Pathogenic'
  | 'Likely pathogenic'
  | 'VUS'
  | 'Likely benign'
  | 'Benign'
  | string

interface Config {
  bg: string
  text: string
  border: string
  dot: string
}

const CONFIGS: Record<string, Config> = {
  'pathogenic': {
    bg: '#fef2f2',
    text: '#991b1b',
    border: '#fca5a5',
    dot: '#dc2626',
  },
  'likely pathogenic': {
    bg: 'var(--warn-tint)',
    text: '#633806',
    border: 'var(--warn-bdr)',
    dot: 'var(--warn)',
  },
  'vus': {
    bg: 'var(--bg-soft)',
    text: 'var(--ink-3)',
    border: 'var(--line)',
    dot: 'var(--ink-4)',
  },
  'likely benign': {
    bg: '#eff6ff',
    text: '#1e40af',
    border: '#bfdbfe',
    dot: '#3b82f6',
  },
  'benign': {
    bg: 'var(--teal-tint)',
    text: 'var(--teal-deep)',
    border: '#cbe3d8',
    dot: 'var(--teal)',
  },
}

function resolveConfig(classification: string): Config {
  const key = classification.toLowerCase()
  return (
    CONFIGS[key] ??
    CONFIGS['vus']
  )
}

interface ClassificationBadgeProps {
  classification: Classification
  className?: string
}

export function ClassificationBadge({ classification, className }: ClassificationBadgeProps) {
  const cfg = resolveConfig(classification)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] border',
        className,
      )}
      style={{
        background: cfg.bg,
        color: cfg.text,
        borderColor: cfg.border,
        borderWidth: '0.5px',
      }}
    >
      <span
        className="shrink-0 rounded-full"
        style={{ width: 6, height: 6, background: cfg.dot }}
      />
      {classification}
    </span>
  )
}
