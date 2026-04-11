import CountUp from 'react-countup'
import { motion } from 'framer-motion'
import { useMemo, type ReactNode } from 'react'
import { Link2, Radio, ShieldCheck, Bot, CalendarClock, TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { safeNumber } from '../data/commandDeck'
import { useCommandDeck } from '../data/CommandDeckProvider'
import { KpiCard } from './KpiCard'

type TrendDir = 'up' | 'down' | 'flat'
type Glow = 'teal' | 'red' | 'violet' | 'amber' | 'green'

type KpiMetric = {
  id: string
  title: string
  sub: string
  glow: Glow
  trend: TrendDir
  end: number
  decimals?: number
  suffix?: string
  separator?: string
  icon: ReactNode
}

function Trend({ dir }: { dir: TrendDir }) {
  if (dir === 'up') return <TrendingUp className="h-3.5 w-3.5 text-emerald-300/90" aria-hidden />
  if (dir === 'down') return <TrendingDown className="h-3.5 w-3.5 text-rose-300/85" aria-hidden />
  return <Minus className="h-3.5 w-3.5 text-slate-500" aria-hidden />
}

const list = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.12 },
  },
}

const item = {
  hidden: { opacity: 0, y: 14, filter: 'blur(6px)' },
  show: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.5, ease: [0, 0, 0.2, 1] as const } },
}

function useKpiMetrics(): (KpiMetric | null | undefined)[] {
  const { deck, trends } = useCommandDeck()

  return useMemo(
    () =>
      [
        {
          id: 'kpi-revenue-links',
          title: 'Revenue Links Generated',
          sub: 'Tracked affiliate endpoints',
          glow: 'green' as const,
          trend: (trends?.revenue_links ?? 'flat') as TrendDir,
          end: safeNumber(deck?.revenue_links, 0),
          separator: ',',
          icon: <Link2 size={18} />,
        },
        {
          id: 'kpi-telegram-reach',
          title: 'Telegram Reach',
          sub: 'Unique channel impressions (est.)',
          glow: 'violet' as const,
          trend: (trends?.telegram_reach ?? 'flat') as TrendDir,
          end: safeNumber(deck?.telegram_reach, 0),
          separator: ',',
          icon: <Radio size={18} />,
        },
        {
          id: 'kpi-affiliate-validity',
          title: 'Affiliate Validity Rate',
          sub: 'Attribution integrity window',
          glow: 'green' as const,
          trend: (trends?.affiliate_validity_pct ?? 'flat') as TrendDir,
          end: safeNumber(deck?.affiliate_validity_pct, 0),
          decimals: 1,
          suffix: '%',
          icon: <ShieldCheck size={18} />,
        },
        {
          id: 'kpi-antibot',
          title: 'Anti-Bot Success Rate',
          sub: 'Stealth + fingerprint evasion',
          glow: 'teal' as const,
          trend: (trends?.anti_bot_success_pct ?? 'flat') as TrendDir,
          end: safeNumber(deck?.anti_bot_success_pct, 0),
          decimals: 1,
          suffix: '%',
          icon: <Bot size={18} />,
        },
        {
          id: 'kpi-deals-24h',
          title: 'Deals Posted (24h)',
          sub: 'Live arbitrage throughput',
          glow: 'amber' as const,
          trend: (trends?.deals_posted_24h ?? 'flat') as TrendDir,
          end: safeNumber(deck?.deals_posted_24h, 0),
          icon: <CalendarClock size={18} />,
        },
      ] as (KpiMetric | null | undefined)[],
    [deck, trends],
  )
}

export function KpiCommandStack() {
  const metrics = useKpiMetrics()

  return (
    <motion.div variants={list} initial="hidden" animate="show" className="grid h-full min-h-0 grid-rows-5 gap-2">
      {metrics?.map((kpi) => {
        if (!kpi?.id) return null
        const end = safeNumber(kpi.end, 0)
        const valueNode =
          kpi.decimals != null ? (
            <span>
              <CountUp start={0} end={end} decimals={kpi.decimals} duration={1.1} preserveValue />
              {kpi.suffix ?? ''}
            </span>
          ) : (
            <CountUp
              start={0}
              end={end}
              duration={1.15}
              preserveValue
              {...(kpi.separator ? { separator: kpi.separator } : {})}
            />
          )

        return (
          <motion.div key={kpi.id} variants={item} className="min-h-0">
            <KpiCard
              compact
              title={kpi.title}
              value={valueNode}
              sub={kpi.sub}
              icon={kpi.icon}
              glow={kpi.glow}
              alive
              trend={<Trend dir={kpi.trend ?? 'flat'} />}
            />
          </motion.div>
        )
      })}
    </motion.div>
  )
}
