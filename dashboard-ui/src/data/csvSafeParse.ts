import Papa from 'papaparse'
import type { ArbitrageRow, DeliveryAuditEntry } from './types'

const MASTER_URL =
  'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/master_log.csv'
const AUDIT_URL =
  'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/delivery_audit.csv'
const BROADCAST_URL =
  'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/broadcast_log.csv'

export type BroadcastLogEntry = {
  timestamp: string
  deal_id: string
  recipients: number
}

export function coerceRow(r: unknown): ArbitrageRow | null {
  if (r == null || typeof r !== 'object' || Array.isArray(r)) return null
  const row = r as Record<string, unknown>
  const timestamp = String(row.timestamp ?? '').trim()
  if (!timestamp) return null

  const id = String(row.id ?? row.deal_id ?? '')
  const title = String(row.title ?? '')
  const price = String(row.price ?? row.new_price ?? '')
  const original_price = String(row.original_price ?? row.old_price ?? '')
  const discount = String(row.discount ?? row.discount_percentage ?? '')
  const category = String(row.category ?? 'general')
  const store = String(row.platform ?? row.store ?? row.marketplace ?? row.source_url ?? 'Unknown')
  const link = String(row.affiliate_link ?? row.link ?? row.affiliate_url ?? row.url ?? '')
  const status = String(row.status ?? row.ScraperStatus ?? row.scraper_status ?? '')

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

function parseRecordsLoose(text: string): Record<string, unknown>[] {
  if (typeof text !== 'string' || !text.trim()) return []
  try {
    const parsed = Papa.parse<Record<string, unknown>>(text, {
      header: true,
      skipEmptyLines: true,
      dynamicTyping: false,
      skipFirstNLines: 0,
    })
    const rows = parsed.data
    if (!Array.isArray(rows)) return []
    return rows.filter((cell): cell is Record<string, unknown> => cell != null && typeof cell === 'object' && !Array.isArray(cell))
  } catch {
    return []
  }
}

export function parseMasterLogCsv(text: string): ArbitrageRow[] {
  const out: ArbitrageRow[] = []
  try {
    for (const raw of parseRecordsLoose(text)) {
      const row = coerceRow(raw)
      if (row) out.push(row)
    }
  } catch {
    return out
  }
  return out
}

function pushLegacyAuditRows(raw: Record<string, unknown>, out: DeliveryAuditEntry[]) {
  const timestamp = String(raw.timestamp ?? '').trim()
  if (!timestamp) return
  const deal_id = String(raw.deal_id ?? '')
  const tg = String(raw.telegram_status ?? '')
  const wa = String(raw.whatsapp_status ?? '')
  const fin = String(raw.final_result ?? '')
  out.push({ timestamp, deal_id, channel: 'telegram', status: tg })
  out.push({ timestamp, deal_id, channel: 'whatsapp', status: wa })
  out.push({ timestamp, deal_id, channel: 'delivery', status: fin })
}

export function parseDeliveryAuditCsv(text: string): DeliveryAuditEntry[] {
  const out: DeliveryAuditEntry[] = []
  try {
    for (const raw of parseRecordsLoose(text)) {
      const ch = raw.channel
      if (ch != null && String(ch).trim() !== '') {
        const timestamp = String(raw.timestamp ?? '').trim()
        if (!timestamp) continue
        out.push({
          timestamp,
          deal_id: String(raw.deal_id ?? ''),
          channel: String(ch),
          status: String(raw.status ?? ''),
        })
        continue
      }
      if (raw.telegram_status != null || raw.final_result != null) {
        pushLegacyAuditRows(raw, out)
      }
    }
  } catch {
    return out
  }
  return out
}

export function parseBroadcastLogCsv(text: string): BroadcastLogEntry[] {
  const out: BroadcastLogEntry[] = []
  for (const raw of parseRecordsLoose(text)) {
    const timestamp = String(raw.timestamp ?? '').trim()
    if (!timestamp) continue
    const n = Number.parseInt(String(raw.recipients ?? '0'), 10)
    out.push({
      timestamp,
      deal_id: String(raw.deal_id ?? ''),
      recipients: Number.isFinite(n) ? n : 0,
    })
  }
  return out
}

export type CsvBundle = {
  rows: ArbitrageRow[]
  deliveryAudit: DeliveryAuditEntry[]
  broadcastLog: BroadcastLogEntry[]
  fetchedAt: number
}

export async function fetchCsvBundle(): Promise<CsvBundle> {
  const masterRes = await fetch(MASTER_URL, { cache: 'no-store' })
  if (!masterRes.ok) throw new Error(`master_log ${masterRes.status}`)
  const masterText = await masterRes.text()

  let auditText = ''
  let broadcastText = ''
  try {
    const auditRes = await fetch(AUDIT_URL, { cache: 'no-store' })
    if (auditRes.ok) auditText = await auditRes.text()
  } catch {
    auditText = ''
  }
  try {
    const br = await fetch(BROADCAST_URL, { cache: 'no-store' })
    if (br.ok) broadcastText = await br.text()
  } catch {
    broadcastText = ''
  }

  return {
    rows: parseMasterLogCsv(masterText),
    deliveryAudit: parseDeliveryAuditCsv(auditText),
    broadcastLog: parseBroadcastLogCsv(broadcastText),
    fetchedAt: Date.now(),
  }
}

export { MASTER_URL, AUDIT_URL, BROADCAST_URL }
