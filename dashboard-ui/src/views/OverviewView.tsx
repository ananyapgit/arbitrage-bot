import { useMemo } from 'react'
import type { ArbitrageRow } from '../data/types'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { BentoCard } from '../ui/fintech/BentoCard'
import { BentoSkeleton } from '../ui/fintech/BentoSkeleton'

function discountValue(r: ArbitrageRow): number {
  const n = Number.parseFloat(String(r.discount ?? '').replace('%', ''))
  return Number.isFinite(n) ? n : 0
}

function confidence(r: ArbitrageRow): number {
  const d = discountValue(r)
  if (d > 0) return Math.min(100, Math.round(d))
  const ok = String(r.status).includes('200')
  return ok ? 78 : 52
}

export function OverviewView() {
  const { rows, deliveryAudit, derived, loading, error, alive, lastSyncAt } = useArbitrage()

  if (loading) return <BentoSkeleton />

  const loot = useMemo(() => {
    return [...rows]
      .sort((a, b) => discountValue(b) - discountValue(a))
      .slice(0, 5)
      .map((r) => ({
        id: r.id || r.timestamp,
        title: r.title || 'Untitled',
        confidence: confidence(r),
      }))
  }, [rows])

  const calendar = useMemo(() => {
    const days: { key: string; ok: boolean | null }[] = []
    for (let i = 34; i >= 0; i--) {
      const d = new Date()
      d.setHours(0, 0, 0, 0)
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      const dayAudits = deliveryAudit.filter(
        (a) => String(a.timestamp).startsWith(key) && a.channel === 'delivery',
      )
      let ok: boolean | null = null
      if (dayAudits.length) {
        const last = dayAudits[dayAudits.length - 1]!
        const s = String(last.status).toLowerCase()
        ok = s.includes('success') || s === 'partial_success'
      } else {
        const dayRows = rows.filter((r) => String(r.timestamp).startsWith(key))
        if (dayRows.length) ok = dayRows.some((r) => String(r.status).includes('200'))
      }
      days.push({ key, ok })
    }
    return days
  }, [deliveryAudit, rows])

  return (
    <div className="grid h-full min-h-0 auto-rows-min grid-cols-12 gap-3 overflow-hidden">
      {error ? (
        <div className="col-span-12">
          <BentoCard className="border-amber-200 bg-amber-50/80 text-sm text-amber-950">Sync: {error}</BentoCard>
        </div>
      ) : null}

      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-[#6B6B6B]">Total Deals</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{derived.totalDeals || derived.totalActiveDeals}</div>
          <div className="mt-1 text-[11px] text-[#9A9A97]">master_log.csv row count (historic + new)</div>
        </BentoCard>
      </div>
      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-[#6B6B6B]">System uptime (24h)</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{derived.systemUptime24h.toFixed(1)}%</div>
          <div className="mt-1 text-[11px] text-[#9A9A97]">Success ratio on delivery_audit (rolling)</div>
        </BentoCard>
      </div>
      <div className="col-span-12 md:col-span-4">
        <BentoCard>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-[#6B6B6B]">Loot alerts sent</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">{derived.lootAlertsSent}</div>
          <div className="mt-1 text-[11px] text-[#9A9A97]">SendGrid recipients (24h, broadcast_log.csv)</div>
        </BentoCard>
      </div>

      <div className="col-span-12 min-h-0 lg:col-span-7">
        <BentoCard className="max-h-full overflow-y-auto overscroll-contain">
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Recent high-loot detects</div>
          <div className="mt-1 text-lg font-semibold tracking-tight">Confidence vs. title</div>
          <ul className="mt-4 space-y-4">
            {loot.length === 0 ? (
              <li className="text-sm text-[#6B6B6B]">No deals yet.</li>
            ) : (
              loot.map((h) => (
                <li key={h.id}>
                  <div className="flex items-center justify-between gap-3 text-sm font-medium text-[#1A1A1A]">
                    <span className="line-clamp-2">{h.title}</span>
                    <span className="shrink-0 tabular-nums text-xs text-[#6B6B6B]">{h.confidence}%</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#EFEEE9]">
                    <div
                      className="h-full rounded-full bg-[#FFD700]"
                      style={{ width: `${h.confidence}%`, maxWidth: '100%' }}
                    />
                  </div>
                </li>
              ))
            )}
          </ul>
        </BentoCard>
      </div>

      <div className="col-span-12 min-h-0 lg:col-span-5">
        <BentoCard className="max-h-full overflow-y-auto overscroll-contain">
          <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Bot run history</div>
          <div className="mt-1 text-lg font-semibold tracking-tight">Last 35 days</div>
          <div className="mt-1 text-xs text-[#6B6B6B]">Yellow = success signal · Gray = no / failed signal</div>
          <div className="mt-4 grid grid-cols-7 gap-2">
            {calendar.map((d) => (
              <div key={d.key} className="flex flex-col items-center gap-1">
                <div
                  className={`h-8 w-8 rounded-full border border-[#E3E3E0] ${
                    d.ok === true ? 'bg-[#FFD700]' : d.ok === false ? 'bg-[#C8C8C4]' : 'bg-[#EFEEE9]'
                  }`}
                  title={d.key}
                />
                <span className="text-[9px] text-[#9A9A97]">{d.key.slice(8)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-[#EFEEE9] pt-3 text-xs text-[#6B6B6B]">
            Bot: <strong className="text-[#1A1A1A]">{alive ? 'active' : 'standby'}</strong>
            {lastSyncAt ? (
              <>
                {' '}
                · Last sync <span className="font-mono text-[#1A1A1A]">{new Date(lastSyncAt).toLocaleTimeString()}</span>
              </>
            ) : null}
          </div>
        </BentoCard>
      </div>
    </div>
  )
}
