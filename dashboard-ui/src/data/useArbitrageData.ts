import { useEffect, useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import type { BroadcastLogEntry, CsvBundle } from './csvSafeParse'
import { fetchCsvBundle } from './csvSafeParse'
import type { ArbitrageDataState, ArbitrageRow, DeliveryAuditEntry } from './types'

const SWR_KEY = 'arbitrage/csv-bundle'
const DAY_MS = 24 * 60 * 60 * 1000

function now() {
  return Date.now()
}

function isSuccessStatus(s: string) {
  const x = s.toLowerCase()
  return x.includes('success') || x === 'partial_success'
}

export function useArbitrageData(pollMs: number = 60_000) {
  const { data, error: swrError, isLoading, isValidating, mutate } = useSWR(SWR_KEY, () => fetchCsvBundle(), {
    refreshInterval: pollMs,
    revalidateOnFocus: false,
    dedupingInterval: 3000,
    shouldRetryOnError: true,
  })

  const rows: ArbitrageRow[] = data?.rows ?? []
  const deliveryAudit: DeliveryAuditEntry[] = data?.deliveryAudit ?? []
  const broadcastLog: BroadcastLogEntry[] = data?.broadcastLog ?? []
  const lastSyncAt = data?.fetchedAt ?? null
  const error = swrError instanceof Error ? swrError.message : swrError ? String(swrError) : null
  const loading = isLoading && data === undefined && swrError === undefined
  const alive = Boolean(data) && !swrError

  const [liveFeed, setLiveFeed] = useState<ArbitrageDataState['liveFeed']>(() => [
    { ts: now(), level: 'INFO' as const, msg: 'SWR bridge online' },
    { ts: now(), level: 'INFO' as const, msg: 'Awaiting CSV bundle…' },
  ])

  const prevKey = useRef<string>('')
  useEffect(() => {
    const key = `${lastSyncAt ?? 'none'}|${error ?? 'ok'}`
    if (key === prevKey.current) return
    prevKey.current = key
    if (loading) return

    setLiveFeed((s) =>
      [
        {
          ts: now(),
          level: error ? ('ERROR' as const) : ('INFO' as const),
          msg: error ? `Sync error: ${error}` : `Bundle refreshed (${rows.length} deals)`,
          data: { validating: isValidating },
        },
        ...s,
      ].slice(0, 60),
    )
  }, [loading, lastSyncAt, error, rows.length, isValidating])

  const derived = useMemo(() => {
    const nowTs = Date.now()
    const totalActiveDeals = rows.length

    const discounts = rows
      .map((r) => Number.parseFloat(String(r.discount ?? '').replace('%', '')))
      .filter((n) => Number.isFinite(n))
    const avgDiscount = discounts.length ? discounts.reduce((a, b) => a + b, 0) / discounts.length : 0

    const last24hRows = rows.filter((r) => {
      const t = new Date(r.timestamp).getTime()
      return Number.isFinite(t) && nowTs - t <= DAY_MS
    })

    const okRows = rows.filter((r) => String(r.status).includes('200')).length
    const successRate = rows.length ? Math.round((okRows / rows.length) * 1000) / 10 : 0

    const audit24 = deliveryAudit.filter((a) => {
      const t = new Date(a.timestamp).getTime()
      return Number.isFinite(t) && nowTs - t <= DAY_MS
    })
    const auditOk = audit24.filter((a) => isSuccessStatus(a.status)).length
    const systemUptime24h = audit24.length ? Math.round((auditOk / audit24.length) * 1000) / 10 : 100

    const br24 = broadcastLog.filter((b) => {
      const t = new Date(b.timestamp).getTime()
      return Number.isFinite(t) && nowTs - t <= DAY_MS
    })
    const lootAlertsSent = br24.reduce((acc, b) => acc + (b.recipients > 0 ? b.recipients : 1), 0)

    const latest = deliveryAudit.slice(-120)
    const tgSuccess = latest.filter((r) => r.channel === 'telegram' && r.status === 'Success').length
    const waSuccess = latest.filter((r) => r.channel === 'whatsapp' && r.status === 'Success').length
    const tgSample = Math.max(latest.filter((r) => r.channel === 'telegram').length, 1)
    const waSample = Math.max(latest.filter((r) => r.channel === 'whatsapp').length, 1)
    const telegramUptime = Math.round((tgSuccess / tgSample) * 1000) / 10
    const whatsappUptime = Math.round((waSuccess / waSample) * 1000) / 10
    const whatsappDeliveries = deliveryAudit.filter((r) => r.channel === 'whatsapp' && r.status === 'Success').length

    return {
      total: totalActiveDeals,
      totalActiveDeals,
      systemUptime24h,
      lootAlertsSent,
      last24hCount: last24hRows.length,
      avgDiscount,
      successRate,
      telegramUptime,
      whatsappUptime,
      whatsappDeliveries,
    }
  }, [rows, deliveryAudit, broadcastLog])

  return {
    rows,
    deliveryAudit,
    broadcastLog,
    lastSyncAt,
    loading,
    error,
    alive,
    liveFeed,
    derived,
    hydrated: !loading || data !== undefined || swrError !== undefined,
    isValidating,
    mutate,
    bundle: (data ?? null) as CsvBundle | null,
  }
}
