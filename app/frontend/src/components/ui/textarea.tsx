import * as React from 'react'
import { cn } from '../../lib/utils'

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        'flex min-h-[168px] w-full rounded-3xl border border-[color:var(--line)] bg-white px-6 py-5 text-base text-[color:var(--ink)] shadow-[inset_0_1px_0_rgba(255,255,255,0.65)] outline-none placeholder:text-[color:var(--placeholder)] focus-visible:border-[color:var(--teal-soft)] focus-visible:ring-4 focus-visible:ring-[color:var(--teal-wash)]',
        className,
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = 'Textarea'

export { Textarea }
