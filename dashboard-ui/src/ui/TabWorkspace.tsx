import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import { Cpu, Radar as RadarIcon, Send, Server, Shield } from 'lucide-react'
import { PrismCard } from './PrismCard'
import { isDeckKpiReady } from '../data/commandDeck'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { useCommandDeck } from '../data/CommandDeckProvider'
import { KpiCommandStack } from './KpiCommandStack'
import { KpiStackBoundary } from './KpiStackBoundary'
import { PrismLoader } from './PrismLoader'
import { RadarPrism } from './RadarPrism'
import { DealFlowStream } from './Wave24h'
import { LiveDealStream } from './LiveDealStream'

type TabId = 'overview' | 'sources' | 'telegram' | 'health'

function KpiCommandStackGate() {
  const { deck } = useCommandDeck()
  const metricsReady = isDeckKpiReady(deck)

  if (!metricsReady) {
    return <PrismLoader label="Syncing KPI lattice…" />
  }

  return (
    <KpiStackBoundary>
      <KpiCommandStack />
    </KpiStackBoundary>
  )
}

const tabs: Array<{ id: TabId; label: string; hint: string }> = [
  { id: 'overview', label: 'Overview', hint: 'Command lattice' },
  { id: 'sources', label: 'Source Intelligence', hint: 'Ingest mesh' },
  { id: 'telegram', label: 'Telegram Analytics', hint: 'Distribution' },
  { id: 'health', label: 'System Health', hint: 'Telemetry' },
]

function SourceIntel() {
  const { deck } = useCommandDeck()
  const sources = useMemo(
    () => [
      { name: 'Amazon IN', q: Math.round(deck.deal_velocity.electronics * 12), health: 98 },
      { name: 'Flipkart', q: Math.round(deck.deal_velocity.fashion * 10), health: 96 },
      { name: 'Reliance / JioMart', q: Math.round(deck.deal_velocity.groceries * 9), health: 93 },
      { name: 'Croma / Electronics', q: Math.round(deck.deal_velocity.home * 8), health: 95 },
    ],
    [deck],
  )

  return (
    <div className="grid h-full min-h-0 gap-3 lg:grid-cols-2">
      {sources.map((s) => (
        <PrismCard key={s.name} tone="violet" className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-xs tracking-[0.18em] text-slate-400/90">SOURCE</div>
              <div className="mt-1 text-base font-semibold text-slate-50">{s.name}</div>
              <div className="mt-2 text-[11px] text-slate-400/90">Ingest throughput (synthetic)</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-slate-500">queue</div>
              <div className="font-mono text-lg text-slate-50">{s.q}</div>
              <div className="mt-1 text-[10px] text-emerald-200/90">health {s.health}%</div>
            </div>
          </div>
        </PrismCard>
      ))}
    </div>
  )
}

function TelegramAnalytics() {
  const { deck } = useCommandDeck()
  return (
    <div className="grid h-full min-h-0 gap-3 lg:grid-cols-3">
      <PrismCard tone="green" className="p-4">
        <div className="text-[10px] tracking-[0.22em] text-emerald-200/70">REACH</div>
        <div className="mt-1 text-2xl font-semibold text-slate-50">{deck.telegram_reach.toLocaleString()}</div>
        <div className="mt-1 text-[11px] text-slate-400/90">Projected unique impressions</div>
      </PrismCard>
      <PrismCard tone="teal" className="p-4">
        <div className="text-[10px] tracking-[0.22em] text-teal-200/70">VALIDITY</div>
        <div className="mt-1 text-2xl font-semibold text-slate-50">{deck.affiliate_validity_pct.toFixed(1)}%</div>
        <div className="mt-1 text-[11px] text-slate-400/90">Attribution window integrity</div>
      </PrismCard>
      <PrismCard tone="violet" className="p-4">
        <div className="text-[10px] tracking-[0.22em] text-violet-200/70">FANOUT</div>
        <div className="mt-1 text-2xl font-semibold text-slate-50">{deck.deals_per_min.toFixed(1)}</div>
        <div className="mt-1 text-[11px] text-slate-400/90">Messages / minute (sim)</div>
      </PrismCard>
    </div>
  )
}

function SystemHealth() {
  const { alive, error, loading, lastSyncAt, liveFeed, derived } = useArbitrage()
  const { deck } = useCommandDeck()

  return (
    <div className="grid h-full min-h-0 gap-3 lg:grid-cols-[1.1fr_0.9fr] lg:min-h-0 lg:overflow-hidden">
      <PrismCard tone="teal" className="p-4">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-teal-200" />
          <div className="text-sm font-semibold text-slate-50">Fleet Telemetry</div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 text-[11px]">
          <div className="rounded-xl border border-white/10 bg-black/30 p-3">
            <div className="text-slate-500">CSV uplink</div>
            <div className="mt-1 font-mono text-slate-100">{alive ? 'nominal' : error ? 'degraded' : loading ? 'sync…' : 'idle'}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/30 p-3">
            <div className="text-slate-500">Rows</div>
            <div className="mt-1 font-mono text-slate-100">{derived.total}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/30 p-3">
            <div className="text-slate-500">Last sync</div>
            <div className="mt-1 font-mono text-slate-100">
              {lastSyncAt ? new Date(lastSyncAt).toLocaleTimeString() : '—'}
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/30 p-3">
            <div className="text-slate-500">Sim heartbeat</div>
            <div className="mt-1 font-mono text-slate-100">{deck.deals_per_min.toFixed(2)} d/m</div>
          </div>
        </div>
      </PrismCard>

      <PrismCard tone="neutral" className="flex min-h-0 flex-col p-0 lg:h-full">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-50">
            <Server className="h-4 w-4 text-slate-300" />
            Live console
          </div>
          <div className="text-[10px] text-slate-500">{alive ? 'streaming' : 'buffering'}</div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-2 font-mono text-[10px] leading-relaxed text-slate-200/90">
          {liveFeed.slice(0, 18).map((l, i) => (
            <div key={`${l.ts}-${i}`} className="py-1">
              <span className="text-slate-500">{new Date(l.ts).toLocaleTimeString()}</span>{' '}
              <span className={l.level === 'ERROR' ? 'text-rose-300' : l.level === 'WARN' ? 'text-amber-300' : 'text-teal-200'}>
                [{l.level}]
              </span>{' '}
              <span>{l.msg}</span>
            </div>
          ))}
        </div>
      </PrismCard>
    </div>
  )
}

export function TabWorkspace() {
  const [tab, setTab] = useState<TabId>('overview')

  return (
    <div className="grid min-h-0 grid-rows-[1fr_auto] gap-2 bg-black/20 px-3 py-2 backdrop-blur-xl sm:px-4">
      <div className="relative min-h-0">
        <AnimatePresence mode="wait">
          {tab === 'overview' ? (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
              className="absolute inset-0 min-h-0"
            >
              <div className="grid h-full min-h-0 gap-3 lg:grid-cols-[minmax(220px,280px)_minmax(0,1fr)_minmax(240px,320px)]">
                <div className="min-h-0">
                  <KpiCommandStackGate />
                </div>

                <div className="grid min-h-0 min-w-0 grid-rows-2 gap-3">
                  <div className="min-h-0">
                    <RadarPrism />
                  </div>
                  <div className="min-h-0">
                    <DealFlowStream />
                  </div>
                </div>

                <div className="min-h-0">
                  <LiveDealStream />
                </div>
              </div>
            </motion.div>
          ) : null}

          {tab === 'sources' ? (
            <motion.div
              key="sources"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
              className="absolute inset-0 min-h-0 overflow-hidden"
            >
              <div className="flex h-full min-h-0 flex-col gap-2">
                <div className="flex items-center gap-2 text-[11px] text-slate-400/90">
                  <RadarIcon className="h-4 w-4 text-violet-200" />
                  Multi-source fusion layer (demo projections)
                </div>
                <div className="min-h-0 flex-1">
                  <SourceIntel />
                </div>
              </div>
            </motion.div>
          ) : null}

          {tab === 'telegram' ? (
            <motion.div
              key="telegram"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
              className="absolute inset-0 min-h-0 overflow-hidden"
            >
              <div className="flex h-full min-h-0 flex-col gap-2">
                <div className="flex items-center gap-2 text-[11px] text-slate-400/90">
                  <Send className="h-4 w-4 text-emerald-200" />
                  Distribution analytics tied to simulated command deck metrics
                </div>
                <div className="min-h-0 flex-1">
                  <TelegramAnalytics />
                </div>
              </div>
            </motion.div>
          ) : null}

          {tab === 'health' ? (
            <motion.div
              key="health"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
              className="absolute inset-0 min-h-0 overflow-hidden"
            >
              <div className="flex h-full min-h-0 flex-col gap-2">
                <div className="flex items-center gap-2 text-[11px] text-slate-400/90">
                  <Shield className="h-4 w-4 text-teal-200" />
                  Production-grade posture: live CSV uplink + simulated control deck
                </div>
                <div className="min-h-0 flex-1 overflow-hidden">
                  <SystemHealth />
                </div>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-white/[0.08] pt-2">
        {tabs.map((t) => {
          const active = t.id === tab
          return (
            <motion.button
              key={t.id}
              type="button"
              title={t.hint}
              onClick={() => setTab(t.id)}
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.985 }}
              className={[
                'relative overflow-hidden rounded-full border px-3 py-1.5 text-[11px] font-semibold tracking-wide transition-colors',
                active
                  ? 'border-teal-400/35 bg-teal-500/10 text-teal-50 shadow-[0_0_26px_-10px_rgba(45,212,191,0.55)]'
                  : 'border-white/10 bg-white/[0.03] text-slate-300/90 hover:border-white/15 hover:text-slate-100',
              ].join(' ')}
            >
              {active ? (
                <motion.span
                  layoutId="tabGlow"
                  className="pointer-events-none absolute inset-0 bg-gradient-to-r from-teal-500/15 via-transparent to-violet-500/10"
                  transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                />
              ) : null}
              <span className="relative">{t.label}</span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
