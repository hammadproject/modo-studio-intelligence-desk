import * as React from 'react'
import { cn } from '../../lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        'h-11 w-full rounded-xl border border-neutral-300 bg-white px-3 text-sm outline-none placeholder:text-neutral-400 focus:border-black focus:ring-1 focus:ring-black disabled:opacity-50',
        className,
      )}
      {...props}
    />
  ),
)
Input.displayName = 'Input'
