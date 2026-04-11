import { motion } from 'framer-motion'

export function KineticOrbs({ botActive }: { botActive: boolean }) {
  const scale = botActive ? [1, 1.2, 1] : [1, 1.06, 1]
  const duration = botActive ? 5.5 : 7.5

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <motion.div
        className="absolute -right-[12%] -top-[8%] h-[min(52vw,420px)] w-[min(52vw,420px)] rounded-full bg-[#FFD700] opacity-[0.22] blur-[100px]"
        animate={{ scale }}
        transition={{ duration, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute left-[8%] top-[28%] h-[min(44vw,360px)] w-[min(44vw,360px)] rounded-full bg-[#FF4D4D] opacity-[0.18] blur-[110px]"
        animate={{ scale }}
        transition={{ duration, repeat: Infinity, ease: 'easeInOut', delay: 0.7 }}
      />
      <motion.div
        className="absolute -bottom-[10%] right-[22%] h-[min(48vw,400px)] w-[min(48vw,400px)] rounded-full bg-[#22D3EE] opacity-[0.2] blur-[105px]"
        animate={{ scale }}
        transition={{ duration, repeat: Infinity, ease: 'easeInOut', delay: 1.4 }}
      />
    </div>
  )
}
