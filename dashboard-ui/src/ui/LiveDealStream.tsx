import { AnimatePresence, motion } from 'framer-motion'
import { PrismCard } from './PrismCard'
import { useCommandDeck } from '../data/CommandDeckProvider'
import { clsx } from 'clsx'

export function LiveDealStream() {
  const { deck, highlightDealIds } = useCommandDeck()

  return (
    <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.55 }}>
      <PrismCard tone="red" className="flex h-full min-h-0 flex-col overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-white/[0.08] bg-black/25 px-3 py-2.5 sm:px-4">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400/70 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-400" />
            </span>
            <div>
              <div className="text-[10px] font-medium tracking-[0.26em] text-rose-200/70">LIVE</div>
              <div className="text-sm font-semibold text-slate-50">Deal Stream</div>
            </div>
          </div>
          <div className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] text-slate-300/90">
            in-card scroll
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 py-2 sm:px-3">
          <div className="flex flex-col gap-2">
            <AnimatePresence initial={false}>
              {deck.recent_deals.map((d) => {
                const flash = highlightDealIds.has(d.id)
                return (
                  <motion.div
                    key={d.id}
                    layout
                    initial={{ opacity: 0, x: 18, filter: 'blur(6px)' }}
                    animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ type: 'spring', stiffness: 520, damping: 34 }}
                    className={clsx(
                      'relative overflow-hidden rounded-xl border border-white/[0.08] bg-black/35 px-3 py-2.5 shadow-[0_0_0_1px_rgba(255,255,255,0.03)]',
                      flash && 'shadow-[0_0_28px_-8px_rgba(250,204,21,0.35)]',
                    )}
                  >
                    {flash ? (
                      <motion.div
                        className="pointer-events-none absolute inset-0 bg-gradient-to-r from-amber-400/25 via-transparent to-transparent"
                        initial={{ x: '-40%' }}
                        animate={{ x: '120%' }}
                        transition={{ duration: 0.9, ease: 'easeOut' }}
                      />
                    ) : null}

                    <div className="relative flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-[13px] font-semibold text-slate-50">{d.title}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm text-emerald-200/95">{d.price}</span>
                          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-200/90">
                            {d.tag}
                          </span>
                        </div>
                      </div>
                      <div className="shrink-0 text-[10px] text-slate-500">{d.time}</div>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        </div>
      </PrismCard>
    </motion.div>
  )
}
