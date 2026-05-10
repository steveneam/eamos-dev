import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  'group relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-2xl text-sm font-semibold transition-[transform,box-shadow,background-color,color,border-color] duration-200 ease-out outline-none disabled:pointer-events-none disabled:opacity-50 active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-[color:var(--teal-soft)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--canvas)]',
  {
    variants: {
      variant: {
        primary:
          'bg-[color:var(--teal)] text-white hover:-translate-y-0.5 hover:bg-[color:var(--teal-deep)] hover:shadow-[0_14px_32px_rgba(44,109,112,0.24)] shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]',
        secondary:
          'border border-[color:var(--line-strong)] bg-white text-[color:var(--ink)] hover:-translate-y-0.5 hover:border-[color:var(--teal-soft)] hover:bg-[color:var(--paper)] hover:shadow-[0_12px_24px_rgba(31,47,56,0.08)]',
        outline:
          'border border-[color:var(--danger-border)] bg-white text-[color:var(--danger)] hover:-translate-y-0.5 hover:border-[color:var(--danger)] hover:bg-[color:var(--danger-faint)] hover:shadow-[0_12px_24px_rgba(184,74,67,0.12)]',
        ghost:
          'text-[color:var(--muted-ink)] hover:-translate-y-0.5 hover:bg-white hover:text-[color:var(--ink)]',
      },
      size: {
        default: 'h-12 px-5',
        sm: 'h-9 rounded-xl px-3',
        lg: 'h-14 rounded-2xl px-7 text-base',
        icon: 'h-11 w-11 rounded-xl',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
  },
)
Button.displayName = 'Button'

export { Button }
