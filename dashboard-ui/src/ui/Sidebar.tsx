import { motion } from 'framer-motion'
import { SatelliteDish, Zap, ShieldCheck } from 'lucide-react'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { GlassCard } from './GlassCard'

function levelColor(level: 'INFO' | 'WARN' | 'ERROR') {
  if (level === 'ERROR') return 'text-red-300'
  if (level === 'WARN') return 'text-amber-300'
  return 'text-teal-200'
}

export function Sidebar() {
  const { alive, lastSyncAt, liveFeed } = useArbitrage()

  return (
    <aside className="space-y-6">
      <motion.div
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.55, ease: 'easeOut' }}
      >
        <GlassCard className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs tracking-[0.22em] text-slate-300/70">SYSTEM</div>
              <div className="mt-1 text-lg font-semibold">Realtime Status</div>
              <div className="mt-2 text-xs text-slate-300/70">
                Pulse: <span className={alive ? 'text-teal-300' : 'text-red-300'}>{alive ? 'ALIVE' : 'OFFLINE'}</span>
              </div>
              <div className="mt-1 text-xs text-slate-300/70">
                Last sync:{' '}
                <span className="text-slate-200">
                  {lastSyncAt ? new Date(lastSyncAt).toLocaleTimeString() : '—'}
                </span>
              </div>
            </div>

            <div className="grid gap-2 text-slate-200/90">
              <SatelliteDish size={20} className={alive ? 'alive-icon' : ''} />
              <Zap size={20} className={alive ? 'alive-icon' : ''} />
              <ShieldCheck size={20} className={alive ? 'alive-icon' : ''} />
            </div>
          </div>
        </GlassCard>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut', delay: 0.06 }}
      >
        <GlassCard className="p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div>
              <div className="text-xs tracking-[0.22em] text-slate-300/70">BOT CONSOLE</div>
              <div className="mt-1 text-sm font-medium text-slate-200">Live Feed</div>
            </div>
            <div className="text-[11px] text-slate-300/70">{alive ? 'streaming' : 'buffering'}</div>
          </div>

          <div className="h-[420px] overflow-auto px-4 py-3 font-mono text-[11px] leading-relaxed">
            {liveFeed.map((l, i) => (
              <div key={`${l.ts}-${i}`} className="py-1">
                <span className="text-slate-400/70">{new Date(l.ts).toLocaleTimeString()}</span>{' '}
                <span className={levelColor(l.level)}>[{l.level}]</span>{' '}
                <span className="text-slate-200/90">{l.msg}</span>
                {l.data !== undefined ? (
                  <span className="text-slate-400/80"> {JSON.stringify(l.data)}</span>
                ) : null}
              </div>
            ))}
          </div>
        </GlassCard>
      </motion.div>
    </aside>
  )
}

