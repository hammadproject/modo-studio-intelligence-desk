import * as React from 'react'
import { cn } from '../../lib/utils'

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<'textarea'>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'min-h-24 w-full resize-y rounded-xl border border-neutral-300 bg-white px-3 py-2.5 text-sm outline-none placeholder:text-neutral-400 focus:border-black focus:ring-1 focus:ring-black disabled:opacity-50',
      className,
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'
