import type { ReactNode } from 'react'
import type { WorkbenchTool } from '@/lib/backend'

const svgProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function ToolIcon({ tool }: { tool: WorkbenchTool }): ReactNode {
  switch (tool) {
    case 'viewer':
      return (
        <svg {...svgProps}>
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
          <circle cx="14" cy="12" r="2" fill="currentColor" />
        </svg>
      )
    case 'primer':
      return (
        <svg {...svgProps}>
          <polyline points="4 7 10 7 12 10 14 7 20 7" />
          <polyline points="20 17 14 17 12 14 10 17 4 17" />
        </svg>
      )
    case 'crispr':
      return (
        <svg {...svgProps}>
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
      )
    case 'align':
      return (
        <svg {...svgProps}>
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      )
    case 'compare':
      return (
        <svg {...svgProps}>
          <rect x="3" y="3" width="7" height="18" rx="1" />
          <rect x="14" y="3" width="7" height="18" rx="1" />
        </svg>
      )
  }
}
