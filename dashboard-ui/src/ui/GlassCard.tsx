import { clsx } from 'clsx'
import type { PropsWithChildren } from 'react'

export function GlassCard({
  className,
  children,
}: PropsWithChildren<{
  className?: string
}>) {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-[25px] shadow-[0_18px_55px_-28px_rgba(0,0,0,0.75)]',
        className,
      )}
    >
      <div className="pointer-events-none absolute inset-0 rounded-xl [mask-image:radial-gradient(220px_160px_at_25%_10%,black,transparent_65%)]">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.14),rgba(255,255,255,0)_55%)]" />
      </div>
      <div className="relative">{children}</div>
    </div>
  )
}

