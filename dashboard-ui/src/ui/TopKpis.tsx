import CountUpImport from 'react-countup'
import { SatelliteDish, ShieldCheck, Zap, AlertTriangle } from 'lucide-react'
import { useArbitrage } from '../data/ArbitrageDataProvider'
import { KpiCard } from './KpiCard'

export function TopKpis() {
  const { derived, alive, error } = useArbitrage()

  const CountUp = (CountUpImport as any)?.CountUp ?? (CountUpImport as any)?.default ?? (CountUpImport as any)

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
      <KpiCard
        title="Total Deals Sent"
        value={<CountUp start={0} end={derived.total} duration={1.6} preserveValue />}
        sub="Grand counter (CSV row count)"
        icon={<SatelliteDish size={22} />}
        glow="teal"
        alive={alive}
      />

      <KpiCard
        title="24h Volume"
        value={<CountUp start={0} end={derived.last24hCount} duration={1.2} preserveValue />}
        sub="Deals logged in last 24 hours"
        icon={<Zap size={22} />}
        glow="violet"
        alive={alive}
      />

      <KpiCard
        title="Avg Discount"
        value={
          <span>
            <CountUp start={0} end={derived.avgDiscount} decimals={1} duration={1.3} preserveValue />%
          </span>
        }
        sub="Average savings signal"
        icon={<Zap size={22} />}
        glow="amber"
        alive={alive}
      />

      <KpiCard
        title={error ? 'Sync Alert' : 'Anti-Bot Stealth'}
        value={error ? 'Degraded' : `${derived.successRate.toFixed(1)}%`}
        sub={error ? error : 'Success rate (status contains “200”)'}
        icon={error ? <AlertTriangle size={22} /> : <ShieldCheck size={22} />}
        glow={error ? 'red' : 'teal'}
        alive={alive}
      />

      <KpiCard
        title="WhatsApp Delivery"
        value={<CountUp start={0} end={derived.whatsappDeliveries ?? 0} duration={1.2} preserveValue />}
        sub={`TG Uptime ${derived.telegramUptime?.toFixed?.(1) ?? 0}% | WA Uptime ${derived.whatsappUptime?.toFixed?.(1) ?? 0}%`}
        icon={<ShieldCheck size={22} />}
        glow="violet"
        alive={alive}
      />
    </section>
  )
}

