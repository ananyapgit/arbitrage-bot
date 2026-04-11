import { clsx } from 'clsx'
import type { PropsWithChildren } from 'react'

export function BentoCard({
  className,
  children,
  padding = 'p-4',
}: PropsWithChildren<{ className?: string; padding?: string }>) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-[#E3E3E0] bg-white text-[#1A1A1A] shadow-[0_1px_0_rgba(0,0,0,0.04)]',
        padding,
        className,
      )}
    >
      {children}
    </div>
  )
}
