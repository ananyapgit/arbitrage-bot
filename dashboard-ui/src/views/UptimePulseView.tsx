import { useMemo } from 'react'
import { useDashboardData } from '../data/useDashboardData'

export function UptimePulseView() {
  const { audit, broadcast } = useDashboardData()
  const cells = useMemo(() => {
    const now = Date.now()
    const out: Array<{ t: string; tg_ok: number; tg_total: number; email_recipients: number }> = []
    for (let i = 6; i >= 0; i--) {
      const d0 = new Date(now - i * 24 * 60 * 60 * 1000)
      const day = d0.toISOString().slice(0, 10)
      const rows = audit.filter((a) => a.timestamp.slice(0, 10) === day)
      const tg = rows.filter((r) => r.channel.includes('telegram'))
      const tg_ok = tg.filter((r) => String(r.status).toLowerCase().includes('success')).length
      const email_recipients = broadcast
        .filter((b) => b.timestamp.slice(0, 10) === day)
        .reduce((acc, b) => acc + (b.recipients || 0), 0)
      out.push({ t: day, tg_ok, tg_total: tg.length, email_recipients })
    }
    return out
  }, [audit, broadcast])

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--panel)] p-4 text-[var(--text)]">
      <div className="text-[10px] tracking-[0.2em] text-[var(--muted)]">UPTIME PULSE</div>
      <div className="mt-2 text-sm font-semibold">Last 7 days activity grid</div>
      <div className="mt-4 grid grid-cols-7 gap-2">
        {cells.map((c) => {
          const ratio = c.tg_total ? c.tg_ok / c.tg_total : 0
          const bg =
            ratio > 0.85
              ? 'bg-[var(--success)]/70'
              : ratio > 0.5
                ? 'bg-[var(--warn)]/65'
                : c.tg_total
                  ? 'bg-[var(--danger)]/60'
                  : 'bg-black/10'
          return (
            <div key={c.t} className="rounded-xl border border-[var(--border)] bg-[var(--panel-2)] p-2">
              <div className={`h-14 rounded-lg ${bg}`} />
              <div className="mt-2 text-[11px] text-[var(--text)]">{c.t.slice(5)}</div>
              <div className="text-[10px] text-[var(--muted)]">
                TG {c.tg_ok}/{c.tg_total} · Email {c.email_recipients}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
