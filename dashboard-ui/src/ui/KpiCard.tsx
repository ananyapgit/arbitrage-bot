import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import type { PropsWithChildren, ReactNode } from 'react'
import { clsx } from 'clsx'
import { PrismCard, type PrismTone } from './PrismCard'

const glowToTone = (glow: 'teal' | 'red' | 'violet' | 'amber' | 'green'): PrismTone => {
  if (glow === 'green') return 'green'
  if (glow === 'red') return 'red'
  if (glow === 'amber') return 'amber'
  if (glow === 'violet') return 'violet'
  return 'teal'
}

export type KpiCardProps = PropsWithChildren<{
  title?: string
  value?: ReactNode
  sub?: string
  icon?: ReactNode
  glow?: 'teal' | 'red' | 'violet' | 'amber' | 'green'
  alive?: boolean
  compact?: boolean
  trend?: ReactNode
}>

export function KpiCard(props: KpiCardProps) {
  const {
    title = 'Metric',
    value = '—',
    sub = '',
    icon = null,
    glow = 'teal',
    alive = false,
    compact = false,
    trend = null,
  } = props

  const x = useMotionValue(0)
  const y = useMotionValue(0)

  const rx = useTransform(y, [-0.5, 0.5], [8, -8])
  const ry = useTransform(x, [-0.5, 0.5], [-10, 10])
  const srx = useSpring(rx, { stiffness: 260, damping: 20 })
  const sry = useSpring(ry, { stiffness: 260, damping: 20 })

  const tone = glowToTone(glow)
  const label = (title ?? 'Metric').toUpperCase()

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      whileHover={{ scale: compact ? 1.015 : 1.02 }}
      onMouseMove={(e) => {
        const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect()
        const px = (e.clientX - rect.left) / rect.width - 0.5
        const py = (e.clientY - rect.top) / rect.height - 0.5
        x.set(px)
        y.set(py)
      }}
      onMouseLeave={() => {
        x.set(0)
        y.set(0)
      }}
      style={{ transformStyle: 'preserve-3d', rotateX: srx, rotateY: sry }}
      className="h-full min-h-0"
    >
      <motion.div
        className="h-full"
        animate={alive ? { boxShadow: ['0 0 0 rgba(0,0,0,0)', '0 0 26px rgba(45,212,191,0.12)', '0 0 0 rgba(0,0,0,0)'] } : false}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
      >
        <PrismCard tone={tone} dense={compact} className="h-full min-h-0">
          <div className="flex items-start justify-between gap-2" style={{ transform: 'translateZ(14px)' }}>
            <div className="min-w-0 flex-1">
              <div className={clsx('font-medium tracking-[0.16em] text-slate-400/90', compact ? 'text-[9px]' : 'text-xs')}>
                {label}
              </div>
              <div className="mt-1 flex items-center gap-2">
                <motion.div
                  key={typeof value === 'string' || typeof value === 'number' ? String(value) : label}
                  initial={{ opacity: 0.35, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
                  className={clsx('font-semibold tracking-tight text-slate-50', compact ? 'text-lg leading-tight' : 'text-2xl')}
                >
                  {value ?? '—'}
                </motion.div>
                {trend ? <div className="flex items-center opacity-90">{trend}</div> : null}
              </div>
              <div className={clsx('mt-1 text-slate-400/85', compact ? 'text-[10px] leading-snug' : 'text-xs')}>{sub ?? ''}</div>
            </div>

            {icon ? (
              <div className={clsx('shrink-0 text-slate-200/90', alive && 'alive-icon', compact ? 'mt-0.5' : 'mt-1')}>{icon}</div>
            ) : null}
          </div>
        </PrismCard>
      </motion.div>
    </motion.div>
  )
}
