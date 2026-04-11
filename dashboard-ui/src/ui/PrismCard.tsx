import { clsx } from 'clsx'
import type { PropsWithChildren } from 'react'

export type PrismTone = 'neutral' | 'teal' | 'green' | 'red' | 'violet' | 'amber'

const toneRing: Record<PrismTone, string> = {
  neutral: 'shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_0_0_1px_rgba(255,255,255,0.08),0_22px_80px_-40px_rgba(0,0,0,0.9)]',
  teal: 'shadow-[inset_0_1px_0_rgba(45,212,191,0.12),0_0_0_1px_rgba(45,212,191,0.22),0_0_48px_-12px_rgba(45,212,191,0.22)]',
  green: 'shadow-[inset_0_1px_0_rgba(74,222,128,0.12),0_0_0_1px_rgba(74,222,128,0.22),0_0_48px_-12px_rgba(74,222,128,0.24)]',
  red: 'shadow-[inset_0_1px_0_rgba(248,113,113,0.1),0_0_0_1px_rgba(248,113,113,0.22),0_0_48px_-12px_rgba(248,113,113,0.2)]',
  violet: 'shadow-[inset_0_1px_0_rgba(167,139,250,0.12),0_0_0_1px_rgba(167,139,250,0.22),0_0_48px_-12px_rgba(167,139,250,0.22)]',
  amber: 'shadow-[inset_0_1px_0_rgba(251,191,36,0.12),0_0_0_1px_rgba(251,191,36,0.22),0_0_48px_-12px_rgba(251,191,36,0.18)]',
}

const toneWash: Record<PrismTone, string> = {
  neutral: 'from-white/[0.12] via-white/[0.03] to-transparent',
  teal: 'from-teal-300/25 via-teal-400/5 to-transparent',
  green: 'from-emerald-300/22 via-emerald-400/5 to-transparent',
  red: 'from-red-300/22 via-red-400/5 to-transparent',
  violet: 'from-violet-300/22 via-violet-400/5 to-transparent',
  amber: 'from-amber-300/22 via-amber-400/5 to-transparent',
}

export function PrismCard({
  className,
  children,
  tone = 'neutral',
  dense,
}: PropsWithChildren<{
  className?: string
  tone?: PrismTone
  dense?: boolean
}>) {
  return (
    <div
      className={clsx(
        'relative isolate overflow-hidden rounded-2xl border border-white/[0.09] bg-black/35 backdrop-blur-[26px]',
        toneRing[tone],
        dense ? 'p-3' : 'p-4',
        className,
      )}
    >
      <div
        className="pointer-events-none absolute -inset-[40%] opacity-[0.55] mix-blend-screen"
        style={{
          background:
            'radial-gradient(closest-side at 30% 12%, rgba(167,139,250,0.22), transparent 62%), radial-gradient(closest-side at 78% 18%, rgba(45,212,191,0.16), transparent 58%)',
        }}
      />
      <div
        className={clsx(
          'pointer-events-none absolute inset-0 bg-gradient-to-br opacity-90',
          toneWash[tone],
        )}
      />
      <div className="pointer-events-none absolute inset-0 prism-noise opacity-[0.085] mix-blend-overlay" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/35 to-transparent" />
      <div className="pointer-events-none absolute inset-0 rounded-2xl shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]" />
      <div className="relative">{children}</div>
    </div>
  )
}
