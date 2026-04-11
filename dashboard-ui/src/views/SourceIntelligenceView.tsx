import { useMemo } from 'react'
import { Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, ResponsiveContainer, Label } from 'recharts'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { sourceDensity } from '../data/sourceBuckets'
import { BentoCard } from '../ui/fintech/BentoCard'
import { BentoSkeleton } from '../ui/fintech/BentoSkeleton'

const COLORS: Record<string, string> = {
  Amazon: '#FF9900',
  Flipkart: '#2874F0',
  Couponami: '#7C3AED',
}

export function SourceIntelligenceView() {
  const { rows, loading, error } = useArbitrage()

  if (loading) return <BentoSkeleton />

  const bubbleData = useMemo(() => {
    const d = sourceDensity(rows)
    return (['Amazon', 'Flipkart', 'Couponami'] as const).map((name, i) => ({
      name,
      x: i + 1,
      y: 1,
      z: Math.max(d[name] * 14, 36),
      count: d[name],
      fill: COLORS[name] ?? '#64748B',
    }))
  }, [rows])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {error ? (
        <BentoCard className="border-amber-200 bg-amber-50/80 text-sm text-amber-950">Sync: {error}</BentoCard>
      ) : null}
      <BentoCard className="min-h-0 flex-1">
        <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Deal density</div>
        <div className="mt-1 text-lg font-semibold tracking-tight">Amazon vs Flipkart vs Couponami</div>
        <div className="mt-4 h-[min(52vh,420px)] min-h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 24, right: 24, bottom: 24, left: 24 }}>
              <XAxis type="number" dataKey="x" domain={[0.5, 3.5]} tick={false} axisLine={false} tickLine={false}>
                <Label value="Source lane" offset={-8} position="insideBottom" fill="#6B6B6B" fontSize={11} />
              </XAxis>
              <YAxis type="number" dataKey="y" domain={[0.5, 1.5]} tick={false} axisLine={false} tickLine={false} />
              <ZAxis type="number" dataKey="z" range={[120, 2200]} name="score" />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null
                  const p = payload[0].payload as { name?: string; count?: number }
                  return (
                    <div className="rounded-xl border border-[#E3E3E0] bg-white px-3 py-2 text-xs shadow-sm">
                      <div className="font-semibold text-[#1A1A1A]">{p.name}</div>
                      <div className="text-[#6B6B6B]">{p.count ?? 0} deals</div>
                    </div>
                  )
                }}
              />
              {bubbleData.map((b) => (
                <Scatter key={b.name} name={b.name} data={[b]} fill={b.fill} />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-[#6B6B6B]">
          {bubbleData.map((b) => (
            <span key={b.name} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ background: b.fill }} />
              {b.name}: <strong className="text-[#1A1A1A]">{b.count}</strong>
            </span>
          ))}
        </div>
        {rows.length === 0 ? (
          <p className="mt-2 text-[11px] text-[#9A9A97]">
            No rows in master_log yet — chart shows zero-density placeholders until the bot syncs deals to GitHub.
          </p>
        ) : null}
      </BentoCard>
    </div>
  )
}
