import { cn } from '@/lib/utils'

interface EamosLogoProps {
  size?: number
  showWordmark?: boolean
  className?: string
  tone?: 'light' | 'dark'
}

function SparkMark({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
    </svg>
  )
}

export function EamosLogo({ size = 16, showWordmark = true, className, tone = 'light' }: EamosLogoProps) {
  const isDark = tone === 'dark'
  const mark = isDark ? 'var(--em-bright)' : 'var(--teal)'
  return (
    <span
      className={cn('inline-flex items-center gap-1.5', className)}
      style={{ color: isDark ? 'var(--hero-ink)' : 'var(--ink)', fontFamily: 'var(--display)' }}
    >
      <span style={{ color: mark }}>
        <SparkMark size={size} />
      </span>
      {showWordmark && (
        <span
          className="font-semibold tracking-[-0.01em]"
          style={{ fontSize: size, lineHeight: 1 }}
        >
          <span style={{ color: mark }}>e</span>amos
        </span>
      )}
    </span>
  )
}
