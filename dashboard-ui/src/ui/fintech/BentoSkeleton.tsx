import { motion } from 'framer-motion'
import { BentoCard } from './BentoCard'

function Block({ tall }: { tall?: boolean }) {
  return (
    <BentoCard padding="p-0 overflow-hidden" className={tall ? 'min-h-[140px]' : 'min-h-[96px]'}>
      <motion.div
        animate={{ opacity: [0.45, 0.88, 0.45] }}
        transition={{ duration: 1.45, repeat: Infinity, ease: [0.4, 0, 0.2, 1] }}
        className={`h-full w-full bg-gradient-to-br from-[#ECEAE6] via-[#F7F6F3] to-[#E8E6E1] ${tall ? 'min-h-[140px]' : 'min-h-[96px]'}`}
      />
    </BentoCard>
  )
}

export function BentoSkeleton() {
  return (
    <div className="grid h-full min-h-0 auto-rows-fr grid-cols-12 gap-3">
      <div className="col-span-12 lg:col-span-8">
        <Block tall />
      </div>
      <div className="col-span-12 grid gap-3 sm:grid-cols-2 lg:col-span-4 lg:grid-cols-1">
        <Block />
        <Block />
      </div>
      <div className="col-span-12 md:col-span-6">
        <Block tall />
      </div>
      <div className="col-span-12 md:col-span-6">
        <Block tall />
      </div>
      <div className="col-span-12">
        <Block tall />
      </div>
    </div>
  )
}
