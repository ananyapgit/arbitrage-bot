import { useMemo, useState } from 'react'
import useSWR from 'swr'
import Papa from 'papaparse'
import { AnimatePresence, motion } from 'framer-motion'
import QRCode from 'react-qr-code'
import {
  Activity,
  BadgeCheck,
  BarChart3,
  ChevronRight,
  Cpu,
  Gauge,
  GitMerge,
  Layers,
  Radio,
  Shield,
  Terminal,
  Timer,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  XCircle,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Radar,
  RadarChart,
  PolarAngleAxis,
  PolarGrid,
  Funnel,
  FunnelChart,
  LabelList,
  Bar,
  BarChart,
  Legend,
} from 'recharts'

type DealRow = {
  timestamp: string
  source: string
  title: string
  price: string
  original_price: string
  category: string
  decision: string
  reason: string
  affiliate_valid: string
}

type TabId = 'source' | 'monetization' | 'health'

  const MASTER_URL = 'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/data/master_log.csv'
  const AUDIT_URL = 'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/delivery_audit.csv'

function parseCsv(text: string): DealRow[] {
  if (!text || !text.trim()) return []
  try {
    const parsed = Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true })
    if (!Array.isArray(parsed.data)) return []
    const out: DealRow[] = []
    for (const raw of parsed.data) {
      if (!raw || typeof raw !== 'object') continue
      const r = raw as Record<string, unknown>
      const ts = String(r.timestamp ?? '').trim()
      if (!ts) continue
      out.push({
        timestamp: ts,
        source: String(r.source ?? r.platform ?? 'Unknown'),
        title: String(r.title ?? '—'),
        price: String(r.price ?? '—'),
        original_price: String(r.original_price ?? '—'),
        category: String(r.category ?? 'general'),
        decision: String(r.decision ?? 'rejected'),
        reason: String(r.reason ?? ''),
        affiliate_valid: String(r.affiliate_valid ?? 'false'),
      })
    }
    return out
  } catch {
    return []
  }
}

function asNum(x: string) {
  const n = Number.parseFloat(String(x).replace(/[^\d.]/g, ''))
  return Number.isFinite(n) ? n : 0
}

function discountPct(r: DealRow) {
  const p = asNum(r.price)
  const o = asNum(r.original_price)
  if (!o || !p || o <= p) return 0
  return ((o - p) / o) * 100
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n))
}

function GaugeArc({ value }: { value: number }) {
  const v = clamp(value, 0, 100)
  const r = 42
  const c = 2 * Math.PI * r
  const a = c * (v / 100)
  return (
    <svg width="120" height="72" viewBox="0 0 120 72" aria-hidden>
      <path d="M18 58a42 42 0 0 1 84 0" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" strokeLinecap="round" />
      <path
        d="M18 58a42 42 0 0 1 84 0"
        fill="none"
        stroke="rgba(0,229,168,0.95)"
        strokeWidth="10"
        strokeLinecap="round"
        style={{
          strokeDasharray: `${a} ${c}`,
          filter: 'drop-shadow(0 0 10px rgba(0,229,168,0.18))',
        }}
      />
    </svg>
  )
}

export function KineticCommandCenter() {
  const [tab, setTab] = useState<TabId>('source')
  const { data, error, isLoading } = useSWR(MASTER_URL, async (url) => {
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`master_log ${res.status}`)
    const text = await res.text()
    return parseCsv(text)
  }, { refreshInterval: 60_000, dedupingInterval: 2500, revalidateOnFocus: false })

  const { data: auditData } = useSWR(AUDIT_URL, async (url) => {
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) return []
    const text = await res.text()
    try {
      const parsed = Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true })
      if (!Array.isArray(parsed.data)) return []
      return parsed.data
        .map((r) => ({
          timestamp: String(r.timestamp ?? ''),
          channel: String(r.channel ?? r.attempt_type ?? ''),
          status: String(r.status ?? r.success ?? ''),
          deal_id: String(r.deal_id ?? ''),
        }))
        .filter((r) => r.timestamp && r.channel)
    } catch {
      return []
    }
  }, { refreshInterval: 60_000, dedupingInterval: 2500, revalidateOnFocus: false })

  const rows = data ?? []
  const latestTs = rows.length ? rows[rows.length - 1]!.timestamp : null

  const metrics = useMemo(() => {
    const total_scraped = rows.length
    const total_posted = rows.filter((r) => r.decision === 'accepted').length
    const total_rejected = rows.filter((r) => r.decision !== 'accepted').length
    const efficiency_score = total_scraped ? (total_posted / total_scraped) * 100 : 0
    const affiliate_valid_n = rows.filter((r) => String(r.affiliate_valid).toLowerCase() === 'true').length
    const affiliate_valid_rate = total_scraped ? (affiliate_valid_n / total_scraped) * 100 : 0
    const rejection_rate = total_scraped ? (total_rejected / total_scraped) * 100 : 0
    const avg_discount = total_scraped ? rows.reduce((a, r) => a + discountPct(r), 0) / total_scraped : 0

    const cats = ['electronics', 'fashion', 'home', 'groceries'] as const
    const category_distribution = Object.fromEntries(cats.map((c) => [c, 0])) as Record<(typeof cats)[number], number>
    for (const r of rows) {
      const k = String(r.category ?? '').toLowerCase()
      if (k.includes('elect')) category_distribution.electronics += 1
      else if (k.includes('fashion') || k.includes('apparel')) category_distribution.fashion += 1
      else if (k.includes('home') || k.includes('kitchen')) category_distribution.home += 1
      else if (k.includes('grocery')) category_distribution.groceries += 1
    }

    const sources: Record<string, { scraped: number; accepted: number }> = {}
    for (const r of rows) {
      const s = (r.source || 'Unknown').toLowerCase().includes('amazon')
        ? 'Amazon'
        : (r.source || '').toLowerCase().includes('coupon')
          ? 'Coupon'
          : (r.source || 'Other')
      sources[s] = sources[s] ?? { scraped: 0, accepted: 0 }
      sources[s]!.scraped += 1
      if (r.decision === 'accepted') sources[s]!.accepted += 1
    }

    return {
      total_scraped,
      total_posted,
      total_rejected,
      efficiency_score,
      affiliate_valid_rate,
      rejection_rate,
      avg_discount,
      category_distribution,
      sources,
    }
  }, [rows])

  const dealsPerMin = useMemo(() => {
    if (rows.length < 2) return 0
    const t0 = new Date(rows[0]!.timestamp).getTime()
    const t1 = new Date(rows[rows.length - 1]!.timestamp).getTime()
    if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return 0
    const mins = (t1 - t0) / 60000
    return mins > 0 ? rows.length / mins : 0
  }, [rows])

  const funnel = useMemo(() => {
    const scraped = rows.length
    const valid = rows.filter((r) => String(r.affiliate_valid).toLowerCase() === 'true').length
    const filtered = rows.filter((r) => discountPct(r) >= 10).length
    const posted = rows.filter((r) => r.decision === 'accepted').length
    return [
      { name: 'Scraped', value: scraped, fill: 'rgba(77,163,255,0.9)' },
      { name: 'Valid', value: valid, fill: 'rgba(0,229,168,0.9)' },
      { name: 'Filtered', value: filtered, fill: 'rgba(255,200,87,0.9)' },
      { name: 'Posted', value: posted, fill: 'rgba(0,229,168,0.95)' },
    ]
  }, [rows])

  const radarData = useMemo(() => {
    const c = metrics.category_distribution
    return [
      { k: 'Electronics', v: c.electronics },
      { k: 'Fashion', v: c.fashion },
      { k: 'Home', v: c.home },
      { k: 'Groceries', v: c.groceries },
    ]
  }, [metrics.category_distribution])

  const timeline = useMemo(() => {
    // bucket by hour (local)
    const buckets = new Map<string, number>()
    for (const r of rows) {
      const t = new Date(r.timestamp)
      if (!Number.isFinite(t.getTime())) continue
      const key = `${t.getMonth() + 1}/${t.getDate()} ${String(t.getHours()).padStart(2, '0')}:00`
      buckets.set(key, (buckets.get(key) ?? 0) + 1)
    }
    const pairs = [...buckets.entries()].slice(-48)
    return pairs.map(([t, deals]) => ({ t, deals }))
  }, [rows])

  const stream = useMemo(() => [...rows].slice(-40).reverse(), [rows])

  const sourcePerf = useMemo(() => {
    return Object.entries(metrics.sources).map(([name, v]) => ({
      name,
      scraped: v.scraped,
      accepted: v.accepted,
      rate: v.scraped ? Math.round((v.accepted / v.scraped) * 1000) / 10 : 0,
    }))
  }, [metrics.sources])

  const reasons = useMemo(() => {
    const acc: Record<string, number> = {}
    for (const r of rows) {
      if (r.decision !== 'accepted') {
        const key = (r.reason || 'UNKNOWN').slice(0, 28)
        acc[key] = (acc[key] ?? 0) + 1
      }
    }
    return Object.entries(acc)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([reason, count]) => ({ reason, count }))
  }, [rows])

  const tgUrl = 'https://t.me/your_channel_name'

  const neural = useMemo(() => {
    const entries = auditData ?? []
    const last = entries.slice(-80)
    const by: Record<string, { ok: number; total: number }> = {}
    for (const e of last) {
      const ch = (e.channel || 'unknown').toLowerCase()
      by[ch] = by[ch] ?? { ok: 0, total: 0 }
      by[ch]!.total += 1
      const s = (e.status || '').toLowerCase()
      if (s.includes('success')) by[ch]!.ok += 1
    }
    return Object.entries(by).map(([channel, v]) => ({
      channel,
      ok: v.ok,
      total: v.total,
      pct: v.total ? Math.round((v.ok / v.total) * 1000) / 10 : 0,
    }))
  }, [auditData])

  return (
    <div className="relative h-full min-h-0 overflow-hidden rounded-2xl border border-black/10 bg-[#F2F0EB] p-4 text-[#1A1A1A]">
      {/* Glowing Neural Mesh background */}
      <div className="pointer-events-none absolute inset-0">
        <motion.div
          className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-[#FFD700] opacity-[0.18] blur-[90px]"
          animate={{ scale: [1, 1.12, 1] }}
          transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute right-[-120px] top-[10%] h-80 w-80 rounded-full bg-[#22D3EE] opacity-[0.14] blur-[110px]"
          animate={{ scale: [1.02, 1.18, 1.02] }}
          transition={{ duration: 7.8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-[-160px] left-[30%] h-96 w-96 rounded-full bg-[#FF4D4D] opacity-[0.10] blur-[120px]"
          animate={{ scale: [1, 1.14, 1] }}
          transition={{ duration: 8.4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="absolute inset-0 opacity-[0.5]" style={{ backgroundImage: 'radial-gradient(rgba(0,0,0,0.08) 1px, transparent 1px)', backgroundSize: '22px 22px' }} />
      </div>

      {/* Command bar */}
      <div className="relative z-10 mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-black/10 pb-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold tracking-[0.22em] text-black/55">ARBITRAGE SUPERBOT ENGINE</div>
          <div className="mt-1 flex items-center gap-2">
            <Terminal className="h-4 w-4 text-black/85" />
            <div className="truncate text-lg font-semibold text-[#1A1A1A]">Kinetic Engine</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-black/10 bg-white px-3 py-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500/70 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-600" />
            </span>
            <span className="text-[11px] font-semibold text-[#1A1A1A]">LIVE</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-black/10 bg-white px-3 py-1.5 text-[11px] text-black/60">
            <Timer className="h-3.5 w-3.5" />
            <span>Last run</span>
            <span className="font-mono text-[#1A1A1A]">{latestTs ? new Date(latestTs).toLocaleString() : '—'}</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-black/10 bg-white px-3 py-1.5 text-[11px] text-black/60">
            <Activity className="h-3.5 w-3.5 text-black/80" />
            <span>Deals/min</span>
            <span className="font-mono font-semibold text-[#1A1A1A]">{dealsPerMin.toFixed(1)}</span>
          </div>

          {neural.length ? (
            <div className="hidden items-center gap-2 rounded-full border border-black/10 bg-white px-3 py-1.5 text-[11px] text-black/60 lg:flex">
              <Cpu className="h-3.5 w-3.5 text-black/80" />
              <span className="text-black/45">Neural</span>
              <span className="font-mono text-[#1A1A1A]">
                {neural
                  .slice(0, 3)
                  .map((n) => `${n.channel}:${n.pct.toFixed(0)}%`)
                  .join(' · ')}
              </span>
            </div>
          ) : null}
        </div>
      </div>

      {/* Main grid */}
      <div className="relative z-10 grid h-[calc(100%-92px)] min-h-0 grid-rows-[1fr_auto] gap-3">
        <div className="grid min-h-0 grid-cols-12 gap-3">
          {/* LEFT: KPI core */}
          <div className="col-span-12 grid min-h-0 grid-rows-4 gap-3 lg:col-span-3">
            <div className="rounded-2xl border border-white/5 bg-[#121821] p-4 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">TOTAL SCRAPED</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">{metrics.total_scraped}</div>
                </div>
                <Layers className="h-5 w-5 text-[#4DA3FF]" />
              </div>
              <div className="mt-2 text-xs text-[#8B949E]">CSV rows ingested (real)</div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">DEALS POSTED</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">{metrics.total_posted}</div>
                </div>
                <BadgeCheck className="h-5 w-5 text-[#00E5A8]" />
              </div>
              <div className="mt-2 text-xs text-[#8B949E]">decision === accepted</div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">REJECTION RATE</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">
                    {metrics.rejection_rate.toFixed(1)}%
                  </div>
                </div>
                <XCircle className="h-5 w-5 text-[#FF4D4F]" />
              </div>
              <div className="mt-2 text-xs text-[#8B949E]">Rejected / scraped</div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">EFFICIENCY SCORE</div>
                  <div className="mt-1 flex items-end gap-2">
                    <div className="text-3xl font-semibold tabular-nums text-[#E6EDF3]">{metrics.efficiency_score.toFixed(1)}%</div>
                    <div className="pb-1 text-[11px] text-[#8B949E]">{metrics.total_posted}/{metrics.total_scraped}</div>
                  </div>
                </div>
                <Gauge className="h-5 w-5 text-[#00E5A8]" />
              </div>
              <div className="mt-2">
                <GaugeArc value={metrics.efficiency_score} />
              </div>
            </div>
          </div>

          {/* CENTER: Intelligence */}
          <div className="col-span-12 grid min-h-0 grid-rows-3 gap-3 lg:col-span-6">
            <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">PIPELINE FUNNEL</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Scraped → Valid → Filtered → Posted</div>
                </div>
                <GitMerge className="h-5 w-5 text-[#4DA3FF]" />
              </div>
              <div className="mt-3 h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <FunnelChart>
                    <Tooltip
                      contentStyle={{
                        background: '#0B0F14',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: 12,
                        color: '#E6EDF3',
                      }}
                    />
                    <Funnel dataKey="value" data={funnel} isAnimationActive>
                      <LabelList dataKey="name" position="right" fill="#8B949E" />
                    </Funnel>
                  </FunnelChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid min-h-0 grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
                <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">CATEGORY RADAR</div>
                <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Distribution (real counts)</div>
                <div className="mt-3 h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.08)" />
                      <PolarAngleAxis dataKey="k" tick={{ fill: '#8B949E', fontSize: 11 }} />
                      <Radar dataKey="v" stroke="rgba(0,229,168,0.95)" fill="rgba(0,229,168,0.18)" />
                      <Tooltip
                        contentStyle={{
                          background: '#0B0F14',
                          border: '1px solid rgba(255,255,255,0.08)',
                          borderRadius: 12,
                          color: '#E6EDF3',
                        }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-2xl border border-white/5 bg-[#121821] p-4">
                <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">DEAL FLOW TIMELINE</div>
                <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Deals over time (bucketed)</div>
                <div className="mt-3 h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timeline} margin={{ left: 0, right: 8, top: 10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="flow" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="rgba(77,163,255,0.55)" />
                          <stop offset="100%" stopColor="rgba(77,163,255,0.0)" />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="t" hide />
                      <YAxis tick={{ fill: '#8B949E', fontSize: 11 }} width={34} />
                      <Tooltip
                        contentStyle={{
                          background: '#0B0F14',
                          border: '1px solid rgba(255,255,255,0.08)',
                          borderRadius: 12,
                          color: '#E6EDF3',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="deals"
                        stroke="rgba(77,163,255,0.95)"
                        fill="url(#flow)"
                        strokeWidth={2.2}
                        isAnimationActive
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: decision stream */}
          <div className="col-span-12 min-h-0 lg:col-span-3">
            <div className="flex h-full min-h-0 flex-col rounded-2xl border border-white/5 bg-[#121821]">
              <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                <div>
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">LIVE DECISION STREAM</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Accepted / Rejected + reason</div>
                </div>
                <Radio className="h-4 w-4 text-[#FFC857]" />
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3">
                {stream.length === 0 ? (
                  <div className="rounded-xl border border-white/5 bg-white/[0.03] p-3 text-xs text-[#8B949E]">
                    {isLoading ? 'Syncing CSV…' : 'No rows in data/master_log.csv yet.'}
                    {error ? <div className="mt-2 text-[#FF4D4F]">Error: {String(error)}</div> : null}
                  </div>
                ) : (
                  <AnimatePresence initial={false}>
                    {stream.map((r, idx) => {
                      const accepted = r.decision === 'accepted'
                      return (
                        <motion.div
                          key={`${r.timestamp}-${idx}`}
                          initial={{ opacity: 0, x: 16 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -10 }}
                          transition={{ type: 'spring', stiffness: 520, damping: 38 }}
                          className="mb-2 rounded-xl border border-white/5 bg-[#0B0F14]/40 p-3"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-[13px] font-semibold text-[#E6EDF3]">{r.title || '—'}</div>
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[#8B949E]">
                                <span className="font-mono text-[#E6EDF3]">{r.price}</span>
                                <span className="rounded-full border border-white/10 px-2 py-0.5">{r.source || 'Unknown'}</span>
                              </div>
                              <div className="mt-2 flex items-center gap-2 text-[11px]">
                                {accepted ? (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-[#00E5A8]/10 px-2 py-0.5 text-[#00E5A8]">
                                    <TrendingUp className="h-3.5 w-3.5" /> Accepted
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-[#FF4D4F]/10 px-2 py-0.5 text-[#FF4D4F]">
                                    <TrendingDown className="h-3.5 w-3.5" /> Rejected
                                  </span>
                                )}
                                <span className="truncate text-[#8B949E]">{r.reason || 'N/A'}</span>
                              </div>
                            </div>
                            <div className="shrink-0 text-[10px] text-[#8B949E]">
                              {new Date(r.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </motion.div>
                      )
                    })}
                  </AnimatePresence>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom band tabs */}
        <div className="rounded-2xl border border-white/5 bg-[#121821]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              {(
                [
                  { id: 'source', label: 'Source Intelligence', icon: BarChart3 },
                  { id: 'monetization', label: 'Monetization', icon: Shield },
                  { id: 'health', label: 'System Health', icon: Cpu },
                ] as const
              ).map((t) => {
                const active = tab === t.id
                const Icon = t.icon
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTab(t.id)}
                    className={[
                      'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-colors',
                      active
                        ? 'border-white/20 bg-white/[0.06] text-[#E6EDF3]'
                        : 'border-white/10 bg-white/[0.03] text-[#8B949E] hover:text-[#E6EDF3]',
                    ].join(' ')}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                    <ChevronRight className="h-3.5 w-3.5 opacity-40" />
                  </button>
                )
              })}
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[#8B949E]">
              {error ? (
                <span className="inline-flex items-center gap-2 rounded-full border border-[#FF4D4F]/25 bg-[#FF4D4F]/10 px-3 py-1.5 text-[#FF4D4F]">
                  <TriangleAlert className="h-3.5 w-3.5" />
                  CSV uplink degraded
                </span>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
                  <Shield className="h-3.5 w-3.5 text-[#00E5A8]" />
                  Data integrity guarded
                </span>
              )}
            </div>
          </div>

          <div className="p-3">
            {tab === 'source' ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">AMAZON VS COUPON</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Source performance</div>
                  <div className="mt-3 h-[260px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={sourcePerf}>
                        <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                        <XAxis dataKey="name" tick={{ fill: '#8B949E', fontSize: 11 }} />
                        <YAxis tick={{ fill: '#8B949E', fontSize: 11 }} width={34} />
                        <Tooltip
                          contentStyle={{
                            background: '#0B0F14',
                            border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: 12,
                            color: '#E6EDF3',
                          }}
                        />
                        <Legend />
                        <Bar dataKey="scraped" fill="rgba(77,163,255,0.75)" radius={[8, 8, 0, 0]} />
                        <Bar dataKey="accepted" fill="rgba(0,229,168,0.75)" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">JOIN LIVE DEALS</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Telegram QR onboarding</div>
                  <div className="mt-3 flex flex-wrap items-center gap-4">
                    <div className="rounded-xl border border-white/10 bg-white p-2">
                      <QRCode value={tgUrl} size={120} />
                    </div>
                    <div className="min-w-[220px]">
                      <div className="text-xs text-[#8B949E]">Scan to join</div>
                      <div className="mt-1 font-mono text-xs text-[#E6EDF3]">{tgUrl}</div>
                      <a
                        href={tgUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-3 inline-flex items-center gap-2 rounded-lg bg-[#4DA3FF] px-3 py-2 text-xs font-semibold text-[#0B0F14]"
                      >
                        <Radio className="h-4 w-4" />
                        Join Telegram
                      </a>
                    </div>
                  </div>
                  <div className="mt-4 text-[11px] text-[#8B949E]">Update `tgUrl` to your real channel.</div>
                </div>
              </div>
            ) : null}

            {tab === 'monetization' ? (
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">AFFILIATE VALID RATE</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">{metrics.affiliate_valid_rate.toFixed(1)}%</div>
                  <div className="mt-2 text-xs text-[#8B949E]">affiliate_valid == true</div>
                </div>
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">AVG DISCOUNT</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">{metrics.avg_discount.toFixed(1)}%</div>
                  <div className="mt-2 text-xs text-[#8B949E]">Derived from price vs original</div>
                </div>
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">POTENTIAL EARNINGS</div>
                  <div className="mt-1 text-3xl font-semibold tabular-nums text-[#E6EDF3]">₹{Math.round(metrics.total_posted * 12).toLocaleString()}</div>
                  <div className="mt-2 text-xs text-[#8B949E]">Heuristic demo until EPC is logged</div>
                </div>
              </div>
            ) : null}

            {tab === 'health' ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">REJECTION REASONS</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Top failure modes</div>
                  <div className="mt-3 h-[260px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={reasons} layout="vertical" margin={{ left: 12, right: 10, top: 4, bottom: 4 }}>
                        <CartesianGrid stroke="rgba(255,255,255,0.06)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: '#8B949E', fontSize: 11 }} />
                        <YAxis type="category" dataKey="reason" width={150} tick={{ fill: '#8B949E', fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            background: '#0B0F14',
                            border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: 12,
                            color: '#E6EDF3',
                          }}
                        />
                        <Bar dataKey="count" fill="rgba(255,77,79,0.75)" radius={[8, 8, 8, 8]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/5 bg-[#0B0F14]/35 p-4">
                  <div className="text-[10px] font-semibold tracking-[0.22em] text-[#8B949E]">PIPE DIAGNOSTICS</div>
                  <div className="mt-1 text-sm font-semibold text-[#E6EDF3]">Infallible CSV bridge</div>
                  <ul className="mt-4 space-y-3 text-xs text-[#8B949E]">
                    <li className="flex items-start gap-2">
                      <Shield className="mt-0.5 h-4 w-4 text-[#00E5A8]" />
                      <span>Defensive parsing: missing columns fallback to `N/A` / `0`.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Cpu className="mt-0.5 h-4 w-4 text-[#4DA3FF]" />
                      <span>Refresh: SWR polling 60s, non-blocking UI.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <BarChart3 className="mt-0.5 h-4 w-4 text-[#FFC857]" />
                      <span>Charts are always mounted in a 260px container (prevents render crashes).</span>
                    </li>
                  </ul>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
