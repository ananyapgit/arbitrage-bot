import { useMemo } from 'react'
import useSWR from 'swr'
import Papa from 'papaparse'

export type DealRow = {
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

export type AuditRow = {
  timestamp: string
  channel: string
  status: string
  deal_id: string
}

export type BroadcastRow = {
  timestamp: string
  deal_id: string
  recipients: number
}

export type WorkflowHeartbeat = {
  timestamp: string
  status: 'RUNNING' | 'VALIDATING' | 'SYNC_DISPATCH' | string
  deal_id?: string
}

const GH_BASE = 'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main'
const API_BASE = ((import.meta as any).env?.VITE_API_BASE as string | undefined)?.trim()

const MASTER_URL = API_BASE ? `${API_BASE}/api/data/master_log.csv` : `${GH_BASE}/data/master_log.csv`
const AUDIT_URL = API_BASE ? `${API_BASE}/api/data/delivery_audit.csv` : `${GH_BASE}/dashboard/public/data/delivery_audit.csv`
const BROADCAST_URL = API_BASE ? `${API_BASE}/api/data/broadcast_log.csv` : `${GH_BASE}/dashboard/public/data/broadcast_log.csv`
const HEARTBEAT_URL = API_BASE ? `${API_BASE}/api/data/workflow_heartbeat.json` : `${GH_BASE}/dashboard/public/data/workflow_heartbeat.json`
const DEALS_URL = `${GH_BASE}/deals.json`

const fetchText = async (url: string) => {
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.text()
}

function parseDealsCsv(text: string): DealRow[] {
  try {
    const parsed = Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true })
    const rows = Array.isArray(parsed.data) ? parsed.data : []
    return rows
      .map((r) => ({
        timestamp: String(r.timestamp ?? '').trim(),
        source: String(r.source ?? r.platform ?? 'unknown'),
        title: String(r.title ?? ''),
        price: String(r.price ?? ''),
        original_price: String(r.original_price ?? ''),
        category: String(r.category ?? 'general'),
        decision: String(r.decision ?? 'rejected'),
        reason: String(r.reason ?? ''),
        affiliate_valid: String(r.affiliate_valid ?? 'false'),
      }))
      .filter((r) => r.timestamp.length > 0)
  } catch {
    return []
  }
}

function parseAuditCsv(text: string): AuditRow[] {
  try {
    const parsed = Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true })
    const rows = Array.isArray(parsed.data) ? parsed.data : []
    return rows
      .map((r) => ({
        timestamp: String(r.timestamp ?? '').trim(),
        channel: String(r.channel ?? r.attempt_type ?? '').trim().toLowerCase(),
        status: String(r.status ?? r.success ?? '').trim(),
        deal_id: String(r.deal_id ?? '').trim(),
      }))
      .filter((r) => r.timestamp && r.channel)
  } catch {
    return []
  }
}

function parseBroadcastCsv(text: string): BroadcastRow[] {
  try {
    const parsed = Papa.parse<Record<string, unknown>>(text, { header: true, skipEmptyLines: true })
    const rows = Array.isArray(parsed.data) ? parsed.data : []
    return rows
      .map((r) => ({
        timestamp: String(r.timestamp ?? '').trim(),
        deal_id: String(r.deal_id ?? '').trim(),
        recipients: Number.parseInt(String(r.recipients ?? '0'), 10) || 0,
      }))
      .filter((r) => r.timestamp)
  } catch {
    return []
  }
}

const asNum = (v: string) => {
  const n = Number.parseFloat(String(v || '').replace(/[^\d.]/g, ''))
  return Number.isFinite(n) ? n : 0
}

export function useDashboardData() {
  const { data: masterText = '', error: masterErr } = useSWR(MASTER_URL, fetchText, { refreshInterval: 30_000 })
  const { data: auditText = '', error: auditErr } = useSWR(AUDIT_URL, fetchText, { refreshInterval: 30_000 })
  const { data: broadcastText = '', error: broadcastErr } = useSWR(BROADCAST_URL, fetchText, { refreshInterval: 30_000 })
  const { data: heartbeat, error: hbErr } = useSWR<WorkflowHeartbeat>(
    HEARTBEAT_URL,
    async (url: string) => {
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`heartbeat ${res.status}`)
      return res.json()
    },
    { refreshInterval: 8000, dedupingInterval: 1000, revalidateOnFocus: false },
  )
  const { data: dealsJson = '[]' } = useSWR(DEALS_URL, fetchText, { refreshInterval: 60_000 })

  const rows = useMemo(() => parseDealsCsv(masterText), [masterText])
  const audit = useMemo(() => parseAuditCsv(auditText), [auditText])
  const broadcast = useMemo(() => parseBroadcastCsv(broadcastText), [broadcastText])
  const deals = useMemo(() => {
    try {
      const parsed = JSON.parse(dealsJson)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }, [dealsJson])

  const derived = useMemo(() => {
    const total = rows.length
    const accepted = rows.filter((r) => r.decision === 'accepted').length
    const rejected = total - accepted
    const avgDiscount =
      total > 0
        ? rows.reduce((acc, r) => {
            const p = asNum(r.price)
            const o = asNum(r.original_price)
            if (!o || !p || o <= p) return acc
            return acc + ((o - p) / o) * 100
          }, 0) / total
        : 0
    return { total, accepted, rejected, avgDiscount }
  }, [rows])

  return {
    rows,
    audit,
    broadcast,
    heartbeat,
    deals,
    derived,
    loading: !masterText,
    error: masterErr || auditErr || broadcastErr || hbErr || null,
  }
}
