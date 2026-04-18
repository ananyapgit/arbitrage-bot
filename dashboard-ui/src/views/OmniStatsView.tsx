import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDashboardData } from '../data/useDashboardData'

function isOk(status: string) {
  const s = String(status || '').toLowerCase()
  return s.includes('success') || s === '1' || s === 'ok'
}

export function OmniStatsView() {
  const { audit, broadcast } = useDashboardData()
  const data = useMemo(() => {
    const channels = ['telegram', 'email']
    return channels.map((ch) => {
      const rows = audit.filter((a) => a.channel.includes(ch))
      const ok = rows.filter((r) => isOk(r.status)).length
      return { channel: ch, attempts: rows.length, success: ok }
    })
  }, [audit])

  const recipients = broadcast.reduce((a, b) => a + (b.recipients || 0), 0)

  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-3">
      <div className="col-span-12 rounded-2xl border border-white/10 bg-[#121821] p-4 text-[#E6EDF3] md:col-span-4">
        <div className="text-[10px] tracking-[0.2em] text-white/50">TOTAL RECIPIENTS REACHED</div>
        <div className="mt-2 text-3xl font-semibold">{recipients}</div>
      </div>
      <div className="col-span-12 rounded-2xl border border-white/10 bg-[#121821] p-4 text-[#E6EDF3] md:col-span-8">
        <div className="text-[10px] tracking-[0.2em] text-white/50">TELEGRAM + EMAIL DELIVERY</div>
        <div className="mt-2 h-[280px]">
          <ResponsiveContainer width="100%" height="100%" minHeight={220}>
            <BarChart data={data}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="channel" tick={{ fill: '#A6B0C0', fontSize: 11 }} />
              <YAxis tick={{ fill: '#A6B0C0', fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="attempts" fill="rgba(99,102,241,0.8)" radius={[8, 8, 0, 0]} />
              <Bar dataKey="success" fill="rgba(0,229,168,0.8)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
