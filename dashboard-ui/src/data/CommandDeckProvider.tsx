import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useArbitrage } from './ArbitrageDataProvider'
import {
  INITIAL_COMMAND_DECK,
  buildStreamPoints,
  sanitizeCommandDeck,
  type CommandDeckSnapshot,
  type RecentDeal,
  type VelocityKey,
  VELOCITY_KEYS,
} from './commandDeck'

type Ctx = {
  deck: CommandDeckSnapshot
  trends: Record<
    | 'revenue_links'
    | 'telegram_reach'
    | 'affiliate_validity_pct'
    | 'anti_bot_success_pct'
    | 'deals_posted_24h',
    'up' | 'down' | 'flat'
  >
  highlightDealIds: Set<string>
}

const CommandDeckContext = createContext<Ctx | null>(null)

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n))
}

function jitter(n: number, span: number) {
  return Math.round((n + (Math.random() - 0.5) * span) * 10) / 10
}

function randomDeal(): RecentDeal {
  const pool = [
    { title: 'Fire-Boltt Phoenix AMOLED', price: '₹1,299', tag: '⚡ Loot' },
    { title: 'Samsung 43" Crystal 4K', price: '₹24,990', tag: '🔥 Trending' },
    { title: 'Prestige Svachh Pressure Cooker', price: '₹1,045', tag: '⚡ Loot' },
    { title: 'Puma Softride Enzo NXT', price: '₹1,879', tag: '📈 Trending' },
    { title: 'Tata Sampann Dal Combo 5kg', price: '₹589', tag: '⚡ Loot' },
    { title: 'Echo Dot 5th Gen', price: '₹3,999', tag: '🔥 Trending' },
  ]
  const pick = pool[Math.floor(Math.random() * pool.length)]!
  return {
    id: `sim-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: pick.title,
    price: pick.price,
    tag: pick.tag,
    time: 'just now',
  }
}

export function CommandDeckProvider({ children }: { children: React.ReactNode }) {
  const { alive, lastSyncAt } = useArbitrage()
  const prevRef = useRef<Omit<CommandDeckSnapshot, 'stream_points'> | null>(null)
  const [deck, setDeck] = useState<CommandDeckSnapshot>(() =>
    sanitizeCommandDeck({
      ...INITIAL_COMMAND_DECK,
      stream_points: buildStreamPoints(56),
    }),
  )
  const [highlightDealIds, setHighlightDealIds] = useState<Set<string>>(() => new Set())

  const trends = useMemo(() => {
    const prev = prevRef.current
    const mk = (key: keyof typeof INITIAL_COMMAND_DECK, cur: number): 'up' | 'down' | 'flat' => {
      if (!prev) return 'flat'
      const p = prev[key]
      if (typeof p !== 'number') return 'flat'
      if (cur > p + 0.05) return 'up'
      if (cur < p - 0.05) return 'down'
      return 'flat'
    }

    return {
      revenue_links: mk('revenue_links', deck.revenue_links),
      telegram_reach: mk('telegram_reach', deck.telegram_reach),
      affiliate_validity_pct: mk('affiliate_validity_pct', deck.affiliate_validity_pct),
      anti_bot_success_pct: mk('anti_bot_success_pct', deck.anti_bot_success_pct),
      deals_posted_24h: mk('deals_posted_24h', deck.deals_posted_24h),
    }
  }, [deck])

  useEffect(() => {
    prevRef.current = {
      revenue_links: deck.revenue_links,
      telegram_reach: deck.telegram_reach,
      affiliate_validity_pct: deck.affiliate_validity_pct,
      anti_bot_success_pct: deck.anti_bot_success_pct,
      deals_posted_24h: deck.deals_posted_24h,
      deals_per_min: deck.deals_per_min,
      deal_velocity: { ...deck.deal_velocity },
      recent_deals: deck.recent_deals,
    }
  }, [deck])

  useEffect(() => {
    const tick = window.setInterval(() => {
      setDeck((s) => {
        const dv = { ...s.deal_velocity }
        for (const k of VELOCITY_KEYS) {
          const key = k as VelocityKey
          dv[key] = clamp(Math.round(jitter(dv[key], 6)), 18, 100)
        }

        const next: CommandDeckSnapshot = {
          ...s,
          revenue_links: Math.max(0, Math.round(jitter(s.revenue_links + (alive ? 1 : 0), 9))),
          telegram_reach: Math.max(0, Math.round(jitter(s.telegram_reach + (alive ? 14 : 3), 40))),
          affiliate_validity_pct: clamp(jitter(s.affiliate_validity_pct, 1.1), 78, 99.2),
          anti_bot_success_pct: clamp(jitter(s.anti_bot_success_pct, 0.35), 92, 99.9),
          deals_posted_24h: Math.max(0, Math.round(jitter(s.deals_posted_24h + (alive ? 0.6 : 0), 5))),
          deals_per_min: clamp(jitter(s.deals_per_min + (alive ? 0.35 : -0.1), 1.8), 4, 28),
          deal_velocity: dv,
        }

        if (Math.random() < 0.42) {
          const incoming = randomDeal()
          const shifted = [incoming, ...s.recent_deals].slice(0, 14)
          next.recent_deals = shifted.map((d, i) => ({
            ...d,
            time: i === 0 ? 'just now' : d.time,
          }))
          setHighlightDealIds(new Set([incoming.id]))
          window.setTimeout(() => setHighlightDealIds(new Set()), 1400)
        }

        return sanitizeCommandDeck(next)
      })
    }, 3200)

    return () => window.clearInterval(tick)
  }, [alive])

  useEffect(() => {
    if (lastSyncAt) {
      setDeck((s) =>
        sanitizeCommandDeck({
          ...s,
          deals_per_min: clamp(jitter(s.deals_per_min + 0.6, 0.9), 4, 28),
        }),
      )
    }
  }, [lastSyncAt])

  useEffect(() => {
    const id = window.setInterval(() => {
      setDeck((s) => {
        const pts = [...s.stream_points]
        const last = pts[pts.length - 1]?.v ?? 40
        const nextV = clamp(last + Math.sin(Date.now() / 900) * 2.2 + (Math.random() - 0.5) * 5, 10, 98)
        pts.shift()
        pts.push({ idx: (pts[pts.length - 1]?.idx ?? 0) + 1, v: Math.round(nextV * 10) / 10 })
        return sanitizeCommandDeck({ ...s, stream_points: pts })
      })
    }, 900)
    return () => window.clearInterval(id)
  }, [])

  const value = useMemo(() => ({ deck, trends, highlightDealIds }), [deck, trends, highlightDealIds])

  return <CommandDeckContext.Provider value={value}>{children}</CommandDeckContext.Provider>
}

export function useCommandDeck() {
  const ctx = useContext(CommandDeckContext)
  if (!ctx) throw new Error('useCommandDeck must be used within CommandDeckProvider')
  return ctx
}
