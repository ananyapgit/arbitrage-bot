import { motion } from 'framer-motion'
import { Activity, CheckCircle2, Cpu, Send } from 'lucide-react'
import { type WorkflowHeartbeat } from '../data/useDashboardData'

const STAGES = [
  { id: 'RUNNING', label: 'SCRAPE', icon: Activity },
  { id: 'VALIDATING', label: 'VALIDATE', icon: CheckCircle2 },
  { id: 'MONETIZE', label: 'MONETIZE', icon: Cpu },
  { id: 'SYNC_DISPATCH', label: 'SYNC-DISPATCH', icon: Send },
] as const

export function WorkflowPulse({ heartbeat }: { heartbeat?: WorkflowHeartbeat }) {
  const active = heartbeat?.status || 'RUNNING'
  return (
    <div className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--panel)] px-4 py-3 text-[var(--text)]">
      <motion.div
        className="pointer-events-none absolute inset-y-0 left-[-25%] w-1/4 bg-gradient-to-r from-transparent via-[var(--accent)]/25 to-transparent"
        animate={{ x: ['0%', '500%'] }}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'linear' }}
      />
      <div className="relative z-10 flex items-center gap-3">
        {STAGES.map((s) => {
          const Icon = s.icon
          const isActive = s.id === active
          return (
            <div key={s.id} className="flex items-center gap-3">
              <div
                className={[
                  'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold',
                  isActive
                    ? 'border-[var(--accent)]/60 bg-[var(--accent)]/20 text-[var(--text)]'
                    : 'border-[var(--border)] bg-[var(--panel-2)] text-[var(--muted)]',
                ].join(' ')}
              >
                <Icon className="h-3.5 w-3.5" />
                {s.label}
              </div>
              {s.id !== 'SYNC_DISPATCH' ? <span className="text-[var(--muted)]">→</span> : null}
            </div>
          )
        })}
        <div className="ml-auto text-[11px] text-[var(--muted)]">
          {heartbeat?.timestamp ? new Date(heartbeat.timestamp).toLocaleString() : '—'}
        </div>
      </div>
    </div>
  )
}
