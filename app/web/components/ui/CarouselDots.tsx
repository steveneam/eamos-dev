'use client'
import { useEffect, useState } from 'react'

const TONES = {
  light: { active: 'var(--teal)', inactive: 'var(--line-2)' },
  dark: { active: 'var(--em-bright)', inactive: 'rgba(255,255,255,0.22)' },
} as const

// Pagination dots for a horizontal scroll-snap carousel. Reads the live DOM of
// the scroll container (by id) so it works with server-rendered card lists —
// one dot per direct child, the in-view card highlighted, tap to scroll to it.
// Renders nothing until it sees >1 child (so SSR/first paint match).
export function CarouselDots({
  containerId,
  tone = 'light',
  className,
}: {
  containerId: string
  tone?: 'light' | 'dark'
  className?: string
}) {
  const [count, setCount] = useState(0)
  const [active, setActive] = useState(0)

  useEffect(() => {
    const el = document.getElementById(containerId)
    if (!el) return
    let raf = 0
    const measure = () => {
      raf = 0
      const kids = [...el.children]
      setCount(kids.length)
      const mid = el.clientWidth / 2
      const elLeft = el.getBoundingClientRect().left
      let best = 0
      let bestDist = Infinity
      kids.forEach((k, i) => {
        const r = (k as HTMLElement).getBoundingClientRect()
        const center = r.left - elLeft + r.width / 2
        const dist = Math.abs(center - mid)
        if (dist < bestDist) {
          bestDist = dist
          best = i
        }
      })
      setActive(best)
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(measure)
    }
    measure()
    el.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      if (raf) cancelAnimationFrame(raf)
      el.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [containerId])

  if (count <= 1) return null

  const go = (i: number) => {
    const el = document.getElementById(containerId)
    const kid = el?.children[i] as HTMLElement | undefined
    if (!el || !kid) return
    const elLeft = el.getBoundingClientRect().left
    const r = kid.getBoundingClientRect()
    const delta = r.left - elLeft - (el.clientWidth - r.width) / 2
    el.scrollBy({ left: delta, behavior: 'smooth' })
  }

  const tones = TONES[tone]
  return (
    <div
      className={className}
      role="tablist"
      aria-label="Carousel pagination"
      style={{ display: 'flex', justifyContent: 'center', gap: 6 }}
    >
      {Array.from({ length: count }).map((_, i) => {
        const isActive = i === active
        return (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-label={`Go to card ${i + 1}`}
            onClick={() => go(i)}
            style={{
              width: isActive ? 18 : 6,
              height: 6,
              borderRadius: 999,
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              background: isActive ? tones.active : tones.inactive,
              transition: 'width 0.2s ease, background 0.2s ease',
            }}
          />
        )
      })}
    </div>
  )
}
