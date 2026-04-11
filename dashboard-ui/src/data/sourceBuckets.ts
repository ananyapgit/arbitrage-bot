import type { ArbitrageRow } from './types'

export type SourceLabel = 'Amazon' | 'Flipkart' | 'Couponami'

export function classifyDealSource(r: ArbitrageRow): SourceLabel | 'Other' {
  const hay = `${r.store} ${r.title} ${r.link} ${r.category}`.toLowerCase()
  if (hay.includes('flipkart')) return 'Flipkart'
  if (hay.includes('couponami')) return 'Couponami'
  if (hay.includes('amazon')) return 'Amazon'
  return 'Other'
}

export function sourceDensity(rows: ArbitrageRow[]): Record<SourceLabel, number> {
  const acc: Record<SourceLabel, number> = { Amazon: 0, Flipkart: 0, Couponami: 0 }
  for (const r of rows) {
    const k = classifyDealSource(r)
    if (k === 'Other') continue
    acc[k] += 1
  }
  return acc
}
