import { motion } from 'framer-motion'
import { PrismCard } from './PrismCard'

export function PrismLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <PrismCard tone="teal" className="flex h-full min-h-[120px] flex-col items-center justify-center gap-3 p-6">
      <motion.div
        className="h-9 w-9 rounded-full border-2 border-teal-400/30 border-t-teal-300"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
        aria-hidden
      />
      <div className="text-center text-xs tracking-wide text-slate-400/90">{label}</div>
    </PrismCard>
  )
}
