import { useMemo } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useDashboardData } from '../data/useDashboardData'

const COLORS = ['#6366f1', '#00e5a8', '#ffc857', '#ff4d4f', '#4da3ff']

export function CategoryMatrixView() {
  const { rows } = useDashboardData()
  const data = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const r of rows) {
      const k = (r.category || 'general').toLowerCase()
      counts[k] = (counts[k] || 0) + 1
    }
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [rows])

  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-3">
      <div className="col-span-12 rounded-2xl border border-[var(--border)] bg-[var(--panel)] p-4 text-[var(--text)]">
        <div className="text-[10px] tracking-[0.2em] text-[var(--muted)]">CATEGORY MATRIX</div>
        <div className="mt-2 text-sm font-semibold">Coverage volume and distribution</div>
      </div>
      <div className="col-span-12 rounded-2xl border border-[var(--border)] bg-[var(--panel)] p-4 md:col-span-7">
        <div className="h-[360px]">
          <ResponsiveContainer width="100%" height="100%" minHeight={280}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={64} outerRadius={132} paddingAngle={2}>
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="col-span-12 rounded-2xl border border-[var(--border)] bg-[var(--panel)] p-4 md:col-span-5">
        <div className="text-xs font-semibold text-[var(--text)]">Top categories</div>
        <div className="mt-3 space-y-3">
          {data.slice(0, 8).map((d, i) => {
            const pct = rows.length ? Math.round((d.value / rows.length) * 100) : 0
            return (
              <div key={d.name} className="rounded-xl border border-[var(--border)] bg-[var(--panel-2)] p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[var(--text)]">{d.name}</span>
                  <span className="text-[var(--muted)]">{d.value} · {pct}%</span>
                </div>
                <div className="mt-2 h-2 w-full rounded-full bg-black/10">
                  <div
                    className="h-2 rounded-full"
                    style={{ width: `${pct}%`, background: COLORS[i % COLORS.length] }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
