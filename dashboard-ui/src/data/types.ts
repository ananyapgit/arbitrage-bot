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

export type ArbitrageDataState = {
  rows: ArbitrageRow[]
  deliveryAudit: Array<{
    timestamp: string
    deal_id: string
    telegram_status: string
    whatsapp_status: string
    final_result: string
  }>
  lastSyncAt: number | null
  loading: boolean
  error: string | null
  alive: boolean
  liveFeed: Array<{ ts: number; level: 'INFO' | 'WARN' | 'ERROR'; msg: string; data?: unknown }>
}

