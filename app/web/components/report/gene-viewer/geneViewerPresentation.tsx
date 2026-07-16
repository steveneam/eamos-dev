import type { CSSProperties } from 'react'

import type { GeneWindowData } from '@/lib/workbench/gene-window'

export const CLASS_COLOR: Record<string, string> = {
  p: 'var(--cls-path-dot)',
  lp: 'var(--cls-lpath-dot)',
  vus: 'var(--cls-vus-dot)',
  lb: 'var(--cls-lben-dot)',
  b: 'var(--cls-ben-dot)',
}

export type GeneClinvarMarkerKind = 'missense' | 'truncating' | 'splice'

interface SvgVariantMarkerProps {
  kind: GeneClinvarMarkerKind
  x: number
  y: number
  size: number
  fill: string
  stroke?: string
  strokeWidth?: number
  opacity?: string
  title: string
}

function variantMarkerKindFromText(
  text: string,
  explicitSplice = false,
): GeneClinvarMarkerKind {
  const lower = text.toLowerCase()
  if (explicitSplice || lower.includes('splice') || /c\.[^\s]*[+-][12](?:\D|$)/.test(lower)) {
    return 'splice'
  }
  if (
    lower.includes('ter') ||
    lower.includes('*') ||
    lower.includes('fs') ||
    lower.includes('frameshift') ||
    lower.includes('stop') ||
    lower.includes('nonsense') ||
    lower.includes('trunc')
  ) {
    return 'truncating'
  }
  return 'missense'
}

export function clinvarMarkerKind(
  variant: GeneWindowData['clinvar'][number],
): GeneClinvarMarkerKind {
  return variantMarkerKindFromText(
    `${variant.hgvsC} ${variant.hgvsP}`,
    Boolean(variant.splice),
  )
}

export function queriedVariantMarkerKind(
  variant: GeneWindowData['queriedVariant'],
): GeneClinvarMarkerKind {
  return variantMarkerKindFromText(`${variant.hgvsC} ${variant.hgvsP}`)
}

export function variantMarkerKindLabel(kind: GeneClinvarMarkerKind): string {
  if (kind === 'truncating') return 'truncating variant'
  if (kind === 'splice') return 'splice-site variant'
  return 'missense/coding variant'
}

export function SvgVariantMarker({
  kind,
  x,
  y,
  size,
  fill,
  stroke,
  strokeWidth,
  opacity,
  title,
}: SvgVariantMarkerProps) {
  const common = { fill, stroke, strokeWidth, opacity }
  if (kind === 'truncating') {
    return (
      <circle cx={x} cy={y} r={size} {...common}>
        <title>{title}</title>
      </circle>
    )
  }
  if (kind === 'splice') {
    return (
      <rect x={x - size} y={y - size} width={size * 2} height={size * 2} {...common}>
        <title>{title}</title>
      </rect>
    )
  }
  return (
    <polygon
      points={`${x - size},${y + size} ${x + size},${y + size} ${x},${y - size}`}
      {...common}
    >
      <title>{title}</title>
    </polygon>
  )
}

export function formatInt(value: number): string {
  return value.toLocaleString('en-US')
}

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value))
}

export function StatPill({ label }: { label: string }) {
  return (
    <span
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 999,
        background: 'var(--bg)',
        color: 'var(--ink-3)',
        padding: '3px 9px',
        fontSize: 10.5,
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}

export const trackScrollStyle: CSSProperties = {
  width: '100%',
  overflowX: 'auto',
  overflowY: 'hidden',
  borderRadius: 8,
  scrollbarWidth: 'thin',
}

export const toggleLabelStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  border: '0.5px solid var(--line)',
  borderRadius: 999,
  background: 'var(--bg-soft)',
  color: 'var(--ink-3)',
  padding: '3px 9px',
  fontSize: 10.5,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}
