import { useMemo } from 'react'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { BentoCard } from '../ui/fintech/BentoCard'
import { BentoSkeleton } from '../ui/fintech/BentoSkeleton'

function cell(ok: boolean) {
  return ok ? 'bg-emerald-500' : 'bg-rose-500'
}

function isOk(s: string) {
  return s.toLowerCase().includes('success') || s.toLowerCase() === 'partial_success'
}

export function HealthView() {
  const { deliveryAudit, loading, error } = useArbitrage()

  if (loading) return <BentoSkeleton />

  const rows = useMemo(() => deliveryAudit.slice(-64).reverse(), [deliveryAudit])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {error ? (
        <BentoCard className="border-amber-200 bg-amber-50/80 text-sm text-amber-950">Sync: {error}</BentoCard>
      ) : null}
      <BentoCard className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Delivery audit</div>
        <div className="mt-1 text-lg font-semibold tracking-tight">Channel uptime heat-map</div>
        <div className="mt-1 text-xs text-[#6B6B6B]">
          Rows from delivery_audit.csv (telegram · whatsapp · delivery). Green = success signal, red = fail.
        </div>

        <div className="mt-4 min-h-0 flex-1 overflow-auto rounded-xl border border-[#ECEAE6]">
          <div className="min-w-[480px]">
            <div className="sticky top-0 z-[1] grid grid-cols-[1.3fr_0.9fr_1fr_1.2fr] gap-px bg-[#ECEAE6] text-[11px] font-semibold uppercase tracking-wide text-[#6B6B6B]">
              <div className="bg-[#F7F7F5] px-2 py-2">Timestamp</div>
              <div className="bg-[#F7F7F5] px-2 py-2">Channel</div>
              <div className="bg-[#F7F7F5] px-2 py-2 text-center">Status</div>
              <div className="bg-[#F7F7F5] px-2 py-2">Deal</div>
            </div>
            {rows.length === 0 ? (
              <div className="p-6 text-sm text-[#6B6B6B]">
                No audit rows yet. The bot appends one row per channel after each delivery attempt — data will appear
                after the next GitHub sync.
              </div>
            ) : (
              rows.map((r, i) => {
                const ok = isOk(r.status)
                return (
                  <div
                    key={`${r.timestamp}-${r.channel}-${i}`}
                    className="grid grid-cols-[1.3fr_0.9fr_1fr_1.2fr] gap-px border-b border-[#F0F0ED] bg-[#ECEAE6] text-[11px]"
                  >
                    <div className="truncate bg-white px-2 py-2 font-mono text-[#1A1A1A]">{r.timestamp}</div>
                    <div className="bg-white px-2 py-2 font-medium capitalize text-[#1A1A1A]">{r.channel}</div>
                    <div className={`flex items-center justify-center bg-white px-1 py-2 ${cell(ok)}`} title={r.status} />
                    <div className="truncate bg-white px-2 py-2 text-[#4B4B4B]" title={r.deal_id}>
                      {r.deal_id || '—'}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </BentoCard>
    </div>
  )
}
