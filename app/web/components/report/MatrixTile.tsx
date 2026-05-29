'use client'

import { useState } from 'react'
import type { LookupSummaryTile } from '@/lib/backend'
import { hasClassificationTier, resolveClassificationConfig } from '@/lib/classification'

interface MatrixTileProps {
  tile: LookupSummaryTile
  onNavigate: (tile: LookupSummaryTile) => void
}

/**
 * MatrixTile — one tile inside the MatrixOverture lookahead grid.
 *
 * Visual states (DL-017): a `source_status` of `"premium_gated"` (or a
 * `"premium"` support badge) MUST NOT render identical grey to a no-data tile.
 * Premium uses a neutral surface PLUS the lock glyph as its distinguisher
 * (the glyph, not colour, separates it from no-data — teal-tint was retired
 * 2026-05-30 because green premium clashed with the benign verdict tier).
 * No-data falls back to grey-NA tokens; classification tiles colour by tier;
 * otherwise the tile renders its primary_label + first support badge.
 */

const PREMIUM_STATUSES = new Set(['premium_gated', 'gated', 'premium'])

function isPremiumGated(tile: LookupSummaryTile): boolean {
  if (PREMIUM_STATUSES.has(tile.source_status)) return true
  return tile.support_badges.some((b) => /premium/i.test(b))
}

function isNoData(tile: LookupSummaryTile): boolean {
  if (isPremiumGated(tile)) return false
  if (!tile.primary_label.trim()) return true
  if (tile.source_status === 'missing' || tile.source_status === 'unavailable') return true
  return tile.warnings.some((w) => /no_data|unavailable|missing/.test(w))
}

export function MatrixTile({ tile, onNavigate }: MatrixTileProps) {
  const [hovered, setHovered] = useState(false)
  const premium = isPremiumGated(tile)
  const noData = isNoData(tile)
  const clickable = !noData && !premium

  // Classification fill: tiles the backend themes `classification` AND whose
  // primary_label resolves to a real ACMG tier get coloured in by verdict, so
  // a clinician scans pathogenicity at a glance. Count-only / non-pathogenicity
  // tiles stay `neutral` and never colour.
  const classified =
    !premium && !noData && tile.ui_color_theme === 'classification' && hasClassificationTier(tile.primary_label)
  const clsCfg = classified ? resolveClassificationConfig(tile.primary_label) : null

  // Visual register — distinct per DL-017. Premium uses warm teal-tint (not
  // grey); no-data uses --cls-na tokens; classification uses the verdict ramp;
  // default uses neutral card surface.
  const surface = premium
    ? { background: 'var(--bg-soft2)', border: '0.5px solid var(--line-2)', color: 'var(--ink-3)' }
    : noData
      ? { background: 'var(--cls-na-bg, var(--bg-soft))', border: '0.5px solid var(--cls-na-bdr, var(--line))', color: 'var(--cls-na-text, var(--ink-4))' }
      : clsCfg
        ? { background: clsCfg.bg, border: `0.5px solid ${clsCfg.border}`, color: 'var(--ink)' }
        : { background: 'var(--bg)', border: '0.5px solid var(--line)', color: 'var(--ink)' }

  const handleClick = () => {
    if (clickable) onNavigate(tile)
  }

  return (
    <article
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : -1}
      aria-disabled={!clickable ? true : undefined}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (clickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          handleClick()
        }
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="w-[52vw] max-w-[200px] shrink-0 snap-center sm:w-auto sm:max-w-none"
      style={{
        ...surface,
        borderColor: hovered && clickable ? 'var(--ink-5)' : surface.border.split(' ').pop(),
        borderRadius: 10,
        padding: '12px 14px',
        minHeight: 110,
        cursor: clickable ? 'pointer' : 'default',
        boxShadow: hovered && clickable ? 'var(--elev-2)' : 'var(--elev-1)',
        transition:
          'box-shadow var(--dur-2) var(--ease-standard), border-color var(--dur-2) var(--ease-standard)',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      {/* Title + premium-gate glyph */}
      <div className="flex items-center justify-between gap-2">
        <span
          className="uppercase"
          style={{
            fontSize: 9.5,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--ink-4)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {tile.title}
        </span>
        {premium && (
          <svg
            aria-label="Premium"
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--ink-4)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ flexShrink: 0 }}
          >
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        )}
      </div>

      {/* Primary label */}
      <div
        style={{
          fontFamily: 'var(--display)',
          fontSize: 15,
          fontWeight: 600,
          lineHeight: 1.2,
          color: premium ? 'var(--ink-3)' : noData ? 'var(--cls-na-text, var(--ink-4))' : clsCfg ? clsCfg.text : 'var(--ink)',
          minHeight: 36,
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}
      >
        {premium ? 'Unlock with Premium' : tile.primary_label || 'No source data'}
      </div>

      {/* First support badge (or warning) */}
      {tile.support_badges.length > 0 ? (
        <span
          style={{
            alignSelf: 'flex-start',
            border: '0.5px solid var(--line)',
            background: 'var(--bg-soft)',
            color: 'var(--ink-3)',
            borderRadius: 999,
            padding: '2px 7px',
            fontSize: 9.5,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            whiteSpace: 'nowrap',
            maxWidth: '100%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {tile.support_badges[0]}
        </span>
      ) : null}
    </article>
  )
}
