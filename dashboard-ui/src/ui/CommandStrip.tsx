import { motion } from 'framer-motion'
import { Activity, Clock3, Zap } from 'lucide-react'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { useCommandDeck } from '../data/CommandDeckProvider'

export function CommandStrip() {
  const { alive, lastSyncAt, loading } = useArbitrage()
  const {
    deck: { deals_per_min },
  } = useCommandDeck()

  const lastRun = lastSyncAt ? new Date(lastSyncAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className="relative z-10 flex min-h-[52px] items-center justify-between gap-4 border-b border-white/[0.08] bg-black/25 px-4 py-2 backdrop-blur-xl sm:px-5"
    >
      <div className="min-w-0">
        <div className="text-[10px] font-medium tracking-[0.28em] text-slate-400/90">CLASSIFIED OPS // AIS</div>
        <div className="truncate text-base font-semibold tracking-tight text-slate-50 sm:text-lg">
          Arbitrage Intelligence System
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
        <motion.div
          layout
          className="flex items-center gap-2 rounded-full border border-white/[0.1] bg-white/[0.04] px-3 py-1.5 shadow-[0_0_24px_-8px_rgba(34,197,94,0.35)]"
        >
          <span className={`relative flex h-2 w-2`}>
            <span
              className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${alive ? 'animate-ping bg-emerald-400' : 'bg-rose-400'}`}
            />
            <span className={`relative inline-flex h-2 w-2 rounded-full ${alive ? 'bg-emerald-400' : 'bg-rose-500'}`} />
          </span>
          <span className="text-[11px] font-medium tracking-wide text-slate-200/90">
            {alive ? 'Bot Active' : loading ? 'Bot Handshake…' : 'Bot Standby'}
          </span>
        </motion.div>

        <div className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-black/30 px-3 py-1.5">
          <Clock3 className="h-3.5 w-3.5 text-slate-400" />
          <div className="text-[11px] text-slate-300/85">
            <span className="text-slate-500">Last run</span>{' '}
            <span className="font-mono text-slate-100">{lastRun}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-teal-500/25 bg-teal-500/[0.07] px-3 py-1.5 shadow-[0_0_28px_-10px_rgba(45,212,191,0.45)]">
          <Zap className="h-3.5 w-3.5 text-teal-200" />
          <div className="text-[11px] text-teal-50/90">
            <span className="text-teal-200/70">Deals/min</span>{' '}
            <span className="font-mono font-semibold">{deals_per_min.toFixed(1)}</span>
          </div>
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 lg:flex">
          <Activity className="h-3.5 w-3.5 text-violet-200" />
          <div className="text-[11px] text-slate-300/85">
            <span className="text-slate-500">Neural mesh</span> <span className="text-slate-100">synchronized</span>
          </div>
        </div>
      </div>
    </motion.header>
  )
}
