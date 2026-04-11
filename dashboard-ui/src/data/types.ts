export type ArbitrageRow = {
  timestamp: string
  id: string
  title: string
  price: string
  original_price: string
  discount: string
  category: string
  store: string
  link: string
  status: string
}

/** Matches bot.py delivery_audit.csv (timestamp, channel, status, deal_id). */
export type DeliveryAuditEntry = {
  timestamp: string
  deal_id: string
  channel: string
  status: string
}

export type ArbitrageDataState = {
  rows: ArbitrageRow[]
  deliveryAudit: DeliveryAuditEntry[]
  lastSyncAt: number | null
  loading: boolean
  error: string | null
  alive: boolean
  liveFeed: Array<{ ts: number; level: 'INFO' | 'WARN' | 'ERROR'; msg: string; data?: unknown }>
}
