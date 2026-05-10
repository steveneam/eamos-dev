import * as TabsPrimitive from '@radix-ui/react-tabs'
import type * as React from 'react'
import { cn } from '../../lib/utils'

export function Tabs(props: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return <TabsPrimitive.Root {...props} />
}

export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn('inline-flex items-center gap-2 rounded-2xl bg-transparent p-0', className)}
      {...props}
    />
  )
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'inline-flex min-w-13 items-center justify-center rounded-[15px] border border-[color:var(--line)] bg-white px-4 py-3 text-sm font-semibold text-[color:var(--teal)] transition-all data-[state=active]:border-[color:var(--teal-soft)] data-[state=active]:bg-[color:var(--teal-ghost)] data-[state=active]:shadow-[0_0_0_2px_rgba(38,112,114,0.08)]',
        className,
      )}
      {...props}
    />
  )
}

export function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn('outline-none', className)} {...props} />
}
