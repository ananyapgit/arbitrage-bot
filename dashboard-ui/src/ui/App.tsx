import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { ArbitrageDataProvider } from '../data/ArbitrageDataProvider'
import { KineticCommandCenter } from '../components/KineticCommandCenter'
import { WorkflowPulse } from '../components/WorkflowPulse'
import { useDashboardData } from '../data/useDashboardData'
import { NewsletterCard } from './fintech/NewsletterCard'
import { SidebarNav, type ThesisTabId } from './fintech/SidebarNav'
import { DecisionLabView } from '../views/DecisionLabView'
import { CategoryMatrixView } from '../views/CategoryMatrixView'
import { UptimePulseView } from '../views/UptimePulseView'
import { BotBlueprintView } from '../views/BotBlueprintView'

function ThesisShell() {
  const [currentTab, setCurrentTab] = useState<ThesisTabId>('elite')
  const [dark, setDark] = useState(true)
  const { heartbeat } = useDashboardData()

  return (
    <div
      data-theme={dark ? 'dark' : 'light'}
      className={[
        'relative flex h-dvh w-full overflow-hidden font-sans antialiased',
        'bg-[var(--bg)] text-[var(--text)]',
      ].join(' ')}
    >
      <div className={['pointer-events-none absolute inset-0', dark ? 'opacity-60' : 'opacity-40'].join(' ')}>
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(color-mix(in srgb, var(--accent) 18%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--accent) 18%, transparent) 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />
      </div>
      <div
        className={[
          'relative z-10 flex w-[240px] shrink-0 flex-col border-r',
          'border-[var(--border)] bg-[var(--panel)]',
        ].join(' ')}
      >
        <SidebarNav currentTab={currentTab} onTab={setCurrentTab} />
        <div className="px-3 pb-2">
          <button
            type="button"
            onClick={() => setDark((v) => !v)}
            className={[
              'inline-flex w-full items-center justify-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold',
              'border-[var(--border)] bg-[var(--panel-2)] text-[var(--text)]',
            ].join(' ')}
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {dark ? 'Light Mode' : 'Dark Mode'}
          </button>
        </div>
        <div className="mt-auto border-t border-white/10 p-3">
          <NewsletterCard variant={dark ? 'dark' : 'light'} />
        </div>
      </div>
      <div className="relative min-h-0 min-w-0 flex-1">
        <div className="relative z-10 flex h-full min-h-0 flex-col overflow-hidden px-4 py-4 sm:px-5">
          <WorkflowPulse heartbeat={heartbeat} />
          <main className="min-h-0 flex-1 overflow-hidden">
            {currentTab === 'elite' ? <KineticCommandCenter /> : null}
            {currentTab === 'decision' ? <DecisionLabView /> : null}
            {currentTab === 'matrix' ? <CategoryMatrixView /> : null}
            {currentTab === 'uptime' ? <UptimePulseView /> : null}
            {currentTab === 'blueprint' ? <BotBlueprintView /> : null}
          </main>
        </div>
      </div>
    </div>
  )
}

export function App() {
  return (
    <ArbitrageDataProvider>
      <ThesisShell />
    </ArbitrageDataProvider>
  )
}
