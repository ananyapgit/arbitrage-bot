import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { BentoCard } from '../ui/fintech/BentoCard'
import { BentoSkeleton } from '../ui/fintech/BentoSkeleton'

export function TelegramView() {
  const { derived, loading, error, rows } = useArbitrage()

  if (loading) return <BentoSkeleton />

  const chartData = [
    { name: 'TG uptime %', v: derived.telegramUptime },
    { name: 'WA uptime %', v: derived.whatsappUptime },
    { name: 'Stealth %', v: derived.successRate },
  ]

  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-3">
      {error ? (
        <div className="col-span-12">
          <BentoCard className="border-amber-200 bg-amber-50/80 text-sm text-amber-950">Sync: {error}</BentoCard>
        </div>
      ) : null}
      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Reach signal</div>
          <div className="mt-2 text-3xl font-semibold tabular-nums">{derived.total}</div>
          <div className="mt-1 text-xs text-[#6B6B6B]">Deals in master_log</div>
        </BentoCard>
      </div>
      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">24h volume</div>
          <div className="mt-2 text-3xl font-semibold tabular-nums">{derived.last24hCount}</div>
          <div className="mt-1 text-xs text-[#6B6B6B]">Rows in trailing window</div>
        </BentoCard>
      </div>
      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">WhatsApp OK</div>
          <div className="mt-2 text-3xl font-semibold tabular-nums">{derived.whatsappDeliveries}</div>
          <div className="mt-1 text-xs text-[#6B6B6B]">Successful WA deliveries (audit)</div>
        </BentoCard>
      </div>
      <div className="col-span-12 min-h-[280px]">
        <BentoCard className="h-full min-h-[280px]">
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Channel posture</div>
          <div className="mt-1 text-lg font-semibold tracking-tight">Telegram vs WhatsApp vs scrape health</div>
          <div className="mt-4 h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6B6B6B' }} axisLine={{ stroke: '#E3E3E0' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#6B6B6B' }} width={32} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #E3E3E0',
                    background: '#fff',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="v" fill="#FFD700" radius={[8, 8, 0, 0]} name="%" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-[11px] text-[#6B6B6B]">
            Live rows: {rows.length} · SWR refresh 60s
            {rows.length === 0 ? (
              <span className="mt-1 block text-amber-800/90">
                CSV is empty or still syncing — charts stay mounted so the tab never renders blank.
              </span>
            ) : null}
          </div>
        </BentoCard>
      </div>
    </div>
  )
}
