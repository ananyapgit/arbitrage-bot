import { useMemo } from 'react'
import PlotImport from 'react-plotly.js'
import { motion } from 'framer-motion'
import { PrismCard } from './PrismCard'
import { useCommandDeck } from '../data/CommandDeckProvider'

const SPOKES = ['Electronics', 'Fashion', 'Home', 'Groceries'] as const

export function RadarPrism() {
  const {
    deck: { deal_velocity },
  } = useCommandDeck()
  const Plot = (PlotImport as any)?.default ?? (PlotImport as any)

  const { r, revision } = useMemo(() => {
    const r = SPOKES.map((k) => {
      const key = k.toLowerCase() as keyof typeof deal_velocity
      return deal_velocity[key] ?? 0
    })
    return { r, revision: r.join('|') }
  }, [deal_velocity])

  const closedR = [...r, r[0]!]
  const closedTheta = [...SPOKES, SPOKES[0]!]

  return (
    <motion.div initial={{ opacity: 0, scale: 0.985 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.55 }}>
      <PrismCard tone="teal" className="flex h-full min-h-0 flex-col p-3 sm:p-4">
        <div className="mb-2 shrink-0">
          <div className="text-[10px] font-medium tracking-[0.26em] text-teal-200/70">CORE VISUAL</div>
          <div className="mt-0.5 text-sm font-semibold tracking-tight text-slate-50">Deal Velocity Engine</div>
          <div className="mt-0.5 text-[11px] text-slate-400/90">Polar mesh • category thrust</div>
        </div>

        <div className="relative min-h-[220px] flex-1">
          <div className="pointer-events-none absolute inset-0 rounded-xl bg-[radial-gradient(closest-side_at_50%_55%,rgba(45,212,191,0.14),transparent_70%)]" />
          <Plot
            data={[
              {
                type: 'scatterpolar',
                r: closedR,
                theta: closedTheta,
                fill: 'toself',
                fillcolor: 'rgba(45,212,191,0.16)',
                line: { color: 'rgba(45,212,191,0.95)', width: 2.4, shape: 'spline' },
                marker: { color: 'rgba(240,253,250,0.95)', size: 6, line: { color: 'rgba(45,212,191,0.65)', width: 1 } },
                hovertemplate: '<b>%{theta}</b><br>velocity %{r}<extra></extra>',
              } as any,
            ]}
            layout={{
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              datarevision: revision,
              transition: { duration: 520, easing: 'cubic-in-out' },
              margin: { l: 28, r: 28, t: 8, b: 8 },
              font: { color: 'rgba(226,232,240,0.92)', size: 11 },
              polar: {
                bgcolor: 'rgba(255,255,255,0.02)',
                radialaxis: {
                  visible: true,
                  range: [0, 100],
                  gridcolor: 'rgba(255,255,255,0.08)',
                  tickfont: { color: 'rgba(148,163,184,0.85)', size: 10 },
                },
                angularaxis: {
                  gridcolor: 'rgba(255,255,255,0.08)',
                  tickfont: { color: 'rgba(226,232,240,0.92)', size: 11 },
                  direction: 'counterclockwise',
                },
              },
              showlegend: false,
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </PrismCard>
    </motion.div>
  )
}
