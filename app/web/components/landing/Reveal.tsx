'use client'
import { motion, useReducedMotion } from 'framer-motion'
import { type ReactNode } from 'react'

/** Fade-and-rise as the element scrolls into view. No-op under reduced motion. */
export function Reveal({
  children,
  delay = 0,
  className,
  as = 'div',
}: {
  children: ReactNode
  delay?: number
  className?: string
  as?: 'div' | 'li' | 'article' | 'section'
}) {
  const reduce = useReducedMotion()
  const Comp = motion[as]

  if (reduce) {
    const Plain = as
    return <Plain className={className}>{children}</Plain>
  }

  return (
    <Comp
      className={className}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5, ease: [0.2, 0, 0, 1], delay }}
    >
      {children}
    </Comp>
  )
}
