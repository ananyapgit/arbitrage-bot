export type DealVelocity = {
  electronics: number
  fashion: number
  home: number
  groceries: number
}

export type RecentDeal = {
  id: string
  title: string
  price: string
  tag: string
  time: string
}

export type CommandDeckSnapshot = {
  revenue_links: number
  telegram_reach: number
  affiliate_validity_pct: number
  anti_bot_success_pct: number
  deals_posted_24h: number
  deals_per_min: number
  deal_velocity: DealVelocity
  recent_deals: RecentDeal[]
  stream_points: Array<{ idx: number; v: number }>
}

export const VELOCITY_KEYS = ['electronics', 'fashion', 'home', 'groceries'] as const
export type VelocityKey = (typeof VELOCITY_KEYS)[number]

export const INITIAL_COMMAND_DECK: Omit<CommandDeckSnapshot, 'stream_points'> = {
  revenue_links: 1243,
  telegram_reach: 18234,
  affiliate_validity_pct: 92,
  anti_bot_success_pct: 97.4,
  deals_posted_24h: 186,
  deals_per_min: 12.4,
  deal_velocity: {
    electronics: 80,
    fashion: 55,
    home: 60,
    groceries: 40,
  },
  recent_deals: [
    {
      id: 'd1',
      title: 'Boat Airdopes 141',
      price: '₹999',
      tag: '🔥 Trending',
      time: '2 min ago',
    },
    {
      id: 'd2',
      title: 'Noise ColorFit Pro 5',
      price: '₹1,799',
      tag: '⚡ Loot',
      time: '6 min ago',
    },
    {
      id: 'd3',
      title: 'Philips Air Fryer HD9252',
      price: '₹6,499',
      tag: '📈 Trending',
      time: '11 min ago',
    },
    {
      id: 'd4',
      title: 'Lifelong Mixer 750W',
      price: '₹1,299',
      tag: '⚡ Loot',
      time: '18 min ago',
    },
    {
      id: 'd5',
      title: 'Sony WH-CH720N',
      price: '₹6,990',
      tag: '🔥 Trending',
      time: '24 min ago',
    },
  ],
}

export function buildStreamPoints(n = 48): Array<{ idx: number; v: number }> {
  const out: Array<{ idx: number; v: number }> = []
  let v = 42
  for (let i = 0; i < n; i++) {
    v += (Math.sin(i / 3.2) * 6 + (Math.random() - 0.45) * 10) * 0.35
    v = Math.max(8, Math.min(96, v))
    out.push({ idx: i, v: Math.round(v * 10) / 10 })
  }
  return out
}

export function safeNumber(n: unknown, fallback: number): number {
  const x = typeof n === 'number' ? n : Number(n)
  return Number.isFinite(x) ? x : fallback
}

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n))
}

function sanitizeDeal(d: unknown, index: number): RecentDeal {
  const r = d as Partial<RecentDeal> | null | undefined
  return {
    id: typeof r?.id === 'string' && r.id.length ? r.id : `deal-${index}-${Math.random().toString(16).slice(2)}`,
    title: typeof r?.title === 'string' && r.title.length ? r.title : '—',
    price: typeof r?.price === 'string' ? r.price : '—',
    tag: typeof r?.tag === 'string' ? r.tag : '',
    time: typeof r?.time === 'string' ? r.time : '—',
  }
}

/** Coerces partial / corrupted snapshots into a safe shape so KPIs and charts never read undefined. */
export function sanitizeCommandDeck(raw: Partial<CommandDeckSnapshot> | null | undefined): CommandDeckSnapshot {
  const base = INITIAL_COMMAND_DECK
  const dvIn = raw?.deal_velocity
  const deal_velocity: DealVelocity = {
    electronics: clamp(safeNumber(dvIn?.electronics, base.deal_velocity.electronics), 0, 100),
    fashion: clamp(safeNumber(dvIn?.fashion, base.deal_velocity.fashion), 0, 100),
    home: clamp(safeNumber(dvIn?.home, base.deal_velocity.home), 0, 100),
    groceries: clamp(safeNumber(dvIn?.groceries, base.deal_velocity.groceries), 0, 100),
  }

  let stream_points = Array.isArray(raw?.stream_points) && raw.stream_points.length > 0 ? raw.stream_points : buildStreamPoints(56)
  stream_points = stream_points.map((p, i) => ({
    idx: safeNumber(p?.idx, i),
    v: clamp(safeNumber(p?.v, 40), 0, 100),
  }))

  const dealsRaw = raw?.recent_deals
  const recent_deals =
    Array.isArray(dealsRaw) && dealsRaw.length > 0
      ? dealsRaw.map((d, i) => sanitizeDeal(d, i))
      : base.recent_deals.map((d, i) => sanitizeDeal(d, i))

  return {
    revenue_links: Math.max(0, Math.round(safeNumber(raw?.revenue_links, base.revenue_links))),
    telegram_reach: Math.max(0, Math.round(safeNumber(raw?.telegram_reach, base.telegram_reach))),
    affiliate_validity_pct: clamp(safeNumber(raw?.affiliate_validity_pct, base.affiliate_validity_pct), 0, 100),
    anti_bot_success_pct: clamp(safeNumber(raw?.anti_bot_success_pct, base.anti_bot_success_pct), 0, 100),
    deals_posted_24h: Math.max(0, Math.round(safeNumber(raw?.deals_posted_24h, base.deals_posted_24h))),
    deals_per_min: clamp(safeNumber(raw?.deals_per_min, base.deals_per_min), 0, 999),
    deal_velocity,
    recent_deals,
    stream_points,
  }
}

/** Minimum shape required before mounting the KPI stack (avoids CountUp / layout with empty arrays). */
export function isDeckKpiReady(d: CommandDeckSnapshot | null | undefined): boolean {
  if (!d) return false
  if (!Array.isArray(d.stream_points) || d.stream_points.length === 0) return false
  const keys: Array<keyof CommandDeckSnapshot> = [
    'revenue_links',
    'telegram_reach',
    'affiliate_validity_pct',
    'anti_bot_success_pct',
    'deals_posted_24h',
    'deals_per_min',
  ]
  for (const k of keys) {
    if (!Number.isFinite(d[k] as number)) return false
  }
  if (!d.deal_velocity || typeof d.deal_velocity !== 'object') return false
  for (const k of VELOCITY_KEYS) {
    if (!Number.isFinite(d.deal_velocity[k])) return false
  }
  return true
}
