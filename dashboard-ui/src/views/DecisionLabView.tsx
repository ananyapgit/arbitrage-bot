import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { useDashboardData } from '../data/useDashboardData'

export function DecisionLabView() {
  const { rows } = useDashboardData()
  const [q, setQ] = useState('')

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return rows
    return rows.filter(
      (r) =>
        r.title.toLowerCase().includes(s) ||
        r.reason.toLowerCase().includes(s) ||
        r.source.toLowerCase().includes(s) ||
        r.category.toLowerCase().includes(s),
    )
  }, [rows, q])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="rounded-2xl border border-white/10 bg-[#121821] p-3 text-[#E6EDF3]">
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
          <Search className="h-4 w-4 text-white/60" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, reason, source, category..."
            className="w-full bg-transparent text-sm outline-none placeholder:text-white/40"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto rounded-2xl border border-white/10 bg-[#121821]">
        <table className="w-full text-left text-xs text-[#E6EDF3]">
          <thead className="sticky top-0 bg-[#0d1219] text-white/70">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Price</th>
              <th className="px-3 py-2">Original</th>
              <th className="px-3 py-2">Decision</th>
              <th className="px-3 py-2">Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice().reverse().map((r, i) => (
              <tr key={`${r.timestamp}-${i}`} className="border-t border-white/5">
                <td className="px-3 py-2 whitespace-nowrap">{new Date(r.timestamp).toLocaleString()}</td>
                <td className="px-3 py-2">{r.source}</td>
                <td className="px-3 py-2 max-w-[360px] truncate">{r.title}</td>
                <td className="px-3 py-2">{r.price}</td>
                <td className="px-3 py-2">{r.original_price}</td>
                <td className="px-3 py-2">{r.decision}</td>
                <td className="px-3 py-2">{r.reason || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
