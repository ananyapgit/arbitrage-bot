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
    const nowMs = now()
    const dayAgo = nowMs - DAY_MS
    const recent = rows.filter(r => Number(new Date(r.timestamp).getTime()) > dayAgo)
    const recentSuccess = recent.filter(r => isSuccessStatus(String(r.status)))
    
    // System uptime from delivery audit (last 24h)
    const recentAudits = deliveryAudit.filter(
      a => Number(new Date(a.timestamp).getTime()) > dayAgo
    )
    const successfulAudits = recentAudits.filter(a => isSuccessStatus(a.status))
    const systemUptime24h = recentAudits.length > 0 
      ? (successfulAudits.length / recentAudits.length) * 100 
      : 100

    // Loot alerts from broadcast log (last 24h)
    const recentBroadcasts = broadcastLog.filter(
      b => Number(new Date(b.timestamp).getTime()) > dayAgo
    )
    const lootAlertsSent = recentBroadcasts.reduce((sum, b) => sum + (b.recipients || 0), 0)

    // Total Deals = master_log.csv.length (all historical + new)
    const totalDeals = rows.length

    // Active deals (non-duplicate, recent)
    const uniqueDeals = new Set(rows.map(r => r.id))
    const totalActiveDeals = uniqueDeals.size

    // Additional metrics
    const last24hRows = recent
    const discounts = rows.map(r => Number.parseFloat(String(r.discount ?? '').replace('%', '') || '0'))
    const avgDiscount = discounts.length > 0 ? discounts.reduce((sum, d) => sum + d, 0) / discounts.length : 0
    const successRate = rows.length > 0 ? (recentSuccess.length / rows.length) * 100 : 100
    const telegramUptime = systemUptime24h
    const whatsappUptime = systemUptime24h
    const whatsappDeliveries = 0

    return {
      total: totalActiveDeals,
      totalDeals,        // NEW: Total deals in master_log.csv
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
