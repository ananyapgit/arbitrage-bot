import { useEffect, useMemo, useRef, useState } from 'react'
import Papa from 'papaparse'
import type { ArbitrageDataState, ArbitrageRow } from './types'

const CSV_URL =
  'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/master_log.csv'
const DELIVERY_AUDIT_URL =
  'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/delivery_audit.csv'

function coerceRow(r: Record<string, unknown>): ArbitrageRow | null {
  const timestamp = String(r.timestamp ?? '')
  if (!timestamp) return null

  // Accept both old and new column naming (back-compat)
  const id = String(r.id ?? r.deal_id ?? '')
  const title = String(r.title ?? '')
  const price = String(r.price ?? r.new_price ?? '')
  const original_price = String(r.original_price ?? r.old_price ?? '')
  const discount = String(r.discount ?? r.discount_percentage ?? '')
  const category = String(r.category ?? 'general')
  const store = String(r.store ?? r.platform ?? r.marketplace ?? 'Unknown')
  const link = String(r.link ?? r.affiliate_url ?? r.url ?? '')
  const status = String(r.status ?? r.ScraperStatus ?? r.scraper_status ?? '')

  return {
    timestamp,
    id,
    title,
    price,
    original_price,
    discount,
    category,
    store,
    link,
    status,
  }
}

function now() {
  return Date.now()
}

export function useArbitrageData(pollMs: number = 60_000) {
  const [state, setState] = useState<ArbitrageDataState>({
    rows: [],
    deliveryAudit: [],
    lastSyncAt: null,
    loading: true,
    error: null,
    alive: false,
    liveFeed: [
      { ts: now(), level: 'INFO' as const, msg: 'Boot sequence: dashboard online' },
      { ts: now(), level: 'INFO' as const, msg: 'Awaiting CSV sync…', data: { url: CSV_URL } },
    ],
  })

  const timerRef = useRef<number | null>(null)
  const feedTimerRef = useRef<number | null>(null)

  const fetchOnce = async () => {
    setState((s) => ({ ...s, loading: s.lastSyncAt == null, error: null }))

    try {
      const res = await fetch(CSV_URL, { cache: 'no-store' })
      if (!res.ok) throw new Error(`CSV fetch failed (${res.status})`)
      const csvText = await res.text()

      const parsed = Papa.parse<Record<string, unknown>>(csvText, {
        header: true,
        skipEmptyLines: true,
        dynamicTyping: false,
      })
      const deliveryRes = await fetch(DELIVERY_AUDIT_URL, { cache: 'no-store' })
      const deliveryText = deliveryRes.ok ? await deliveryRes.text() : ''
      const deliveryParsed = Papa.parse<Record<string, unknown>>(deliveryText, {
        header: true,
        skipEmptyLines: true,
        dynamicTyping: false,
      })

      const rows: ArbitrageRow[] = []
      for (const raw of parsed.data) {
        const coerced = coerceRow(raw)
        if (coerced) rows.push(coerced)
      }
      const deliveryAudit = deliveryParsed.data.map((r) => ({
        timestamp: String(r.timestamp ?? ''),
        deal_id: String(r.deal_id ?? ''),
        telegram_status: String(r.telegram_status ?? 'Fail'),
        whatsapp_status: String(r.whatsapp_status ?? 'Fail'),
        final_result: String(r.final_result ?? 'fail'),
      }))

      setState((s) => ({
        ...s,
        rows,
        deliveryAudit,
        lastSyncAt: now(),
        loading: false,
        error: null,
        alive: true,
        liveFeed: [
          { ts: now(), level: 'INFO' as const, msg: 'Stealth Bypass Successful', data: { status: 'active' } },
          { ts: now(), level: 'INFO' as const, msg: 'JSON-LD Extracted', data: { rows: rows.length } },
          ...s.liveFeed,
        ].slice(0, 60),
      }))
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      setState((s) => ({
        ...s,
        loading: false,
        error: msg,
        alive: false,
        liveFeed: [
          { ts: now(), level: 'ERROR' as const, msg: 'CSV sync failed', data: { error: msg } },
          ...s.liveFeed,
        ].slice(0, 60),
      }))
    }
  }

  useEffect(() => {
    void fetchOnce()

    timerRef.current = window.setInterval(() => {
      void fetchOnce()
    }, pollMs)

    // Ambient “alive” console ticks (even between fetches)
    feedTimerRef.current = window.setInterval(() => {
      setState((s) => ({
        ...s,
        liveFeed: [
          {
            ts: now(),
            level: 'INFO' as const,
            msg: s.alive ? 'System Pulse' : 'Reconnecting…',
            data: { alive: s.alive, lastSyncAt: s.lastSyncAt },
          },
          ...s.liveFeed,
        ].slice(0, 60),
      }))
    }, 2_000)

    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
      if (feedTimerRef.current) window.clearInterval(feedTimerRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollMs])

  const derived = useMemo(() => {
    const total = state.rows.length

    const discounts = state.rows
      .map((r) => Number.parseFloat(String(r.discount ?? '').replace('%', '')))
      .filter((n) => Number.isFinite(n))
    const avgDiscount = discounts.length ? discounts.reduce((a, b) => a + b, 0) / discounts.length : 0

    const nowTs = Date.now()
    const last24h = state.rows.filter((r) => {
      const t = new Date(r.timestamp).getTime()
      return Number.isFinite(t) && nowTs - t <= 24 * 60 * 60 * 1000
    })

    const ok = state.rows.filter((r) => String(r.status).includes('200')).length
    const successRate = total ? Math.round((ok / total) * 1000) / 10 : 0

    const latest = state.deliveryAudit.slice(-100)
    const tgSuccess = latest.filter((r) => r.telegram_status === 'Success').length
    const waSuccess = latest.filter((r) => r.whatsapp_status === 'Success').length
    const sample = Math.max(latest.length, 1)
    const telegramUptime = Math.round((tgSuccess / sample) * 1000) / 10
    const whatsappUptime = Math.round((waSuccess / sample) * 1000) / 10
    const whatsappDeliveries = state.deliveryAudit.filter((r) => r.whatsapp_status === 'Success').length

    return {
      total,
      last24hCount: last24h.length,
      avgDiscount,
      successRate,
      telegramUptime,
      whatsappUptime,
      whatsappDeliveries,
    }
  }, [state.rows, state.deliveryAudit])

  return { ...state, derived }
}

