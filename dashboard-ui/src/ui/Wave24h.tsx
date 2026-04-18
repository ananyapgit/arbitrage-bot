import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { motion } from 'framer-motion'
import { PrismCard } from './PrismCard'
import { useCommandDeck } from '../data/CommandDeckProvider'

export function DealFlowStream() {
  const {
    deck: { stream_points },
  } = useCommandDeck()

  const data = stream_points.map((p, i) => ({
    t: String(i).padStart(2, '0'),
    v: p.v,
  }))

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.05 }}>
      <PrismCard tone="violet" className="flex h-full min-h-0 flex-col p-3 sm:p-4">
        <div className="mb-2 flex shrink-0 items-end justify-between gap-3">
          <div>
            <div className="text-[10px] font-medium tracking-[0.26em] text-violet-200/70">LIVE FEED</div>
            <div className="mt-0.5 text-sm font-semibold text-slate-50">Deal Flow Stream</div>
            <div className="mt-0.5 text-[11px] text-slate-400/90">Synthetic liquidity pulse (demo)</div>
          </div>
          <div className="rounded-full border border-white/10 bg-black/30 px-2 py-1 text-[10px] text-slate-300/85">
            recharts • spline
          </div>
        </div>

        <div className="min-h-[160px] flex-1">
          <ResponsiveContainer width="100%" height="100%" minHeight={160}>
            <AreaChart data={data} margin={{ left: 0, right: 6, top: 6, bottom: 0 }}>
              <defs>
                <linearGradient id="dealFlowFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="4%" stopColor="rgba(167,139,250,0.55)" stopOpacity={0.55} />
                  <stop offset="92%" stopColor="rgba(45,212,191,0.0)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="dealFlowStroke" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="rgba(167,139,250,0.25)" />
                  <stop offset="45%" stopColor="rgba(167,139,250,0.95)" />
                  <stop offset="100%" stopColor="rgba(45,212,191,0.95)" />
                </linearGradient>
                <filter id="glowLine" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="t" stroke="rgba(148,163,184,0.55)" tick={{ fontSize: 10 }} tickMargin={8} hide />
              <YAxis stroke="rgba(148,163,184,0.55)" tick={{ fontSize: 10 }} width={30} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  background: 'rgba(10, 8, 22, 0.72)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  backdropFilter: 'blur(18px)',
                  borderRadius: 12,
                  color: 'rgba(226,232,240,0.95)',
                  boxShadow: '0 0 24px rgba(167,139,250,0.18)',
                }}
                labelStyle={{ color: 'rgba(226,232,240,0.85)' }}
                formatter={(v) => [`${v ?? ''}`, 'Flow']}
              />

              <Area
                type="monotone"
                dataKey="v"
                stroke="url(#dealFlowStroke)"
                strokeWidth={2.4}
                fill="url(#dealFlowFill)"
                isAnimationActive
                animationDuration={650}
                animationEasing="ease-out"
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0, fill: 'rgba(240,253,250,0.95)' }}
                style={{ filter: 'url(#glowLine)' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </PrismCard>
    </motion.div>
  )
}

export const Wave24h = DealFlowStream
