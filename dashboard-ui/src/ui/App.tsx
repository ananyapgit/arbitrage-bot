import { useState } from 'react'
import { ArbitrageDataProvider, useArbitrage } from '../data/ArbitrageDataProvider'
import { HealthView } from '../views/HealthView'
import { OverviewView } from '../views/OverviewView'
import { SourceIntelligenceView } from '../views/SourceIntelligenceView'
import { TelegramView } from '../views/TelegramView'
import { KineticOrbs } from './fintech/KineticOrbs'
import { NewsletterCard } from './fintech/NewsletterCard'
import { SidebarNav, type ThesisTabId } from './fintech/SidebarNav'

function ThesisShell() {
  const [currentTab, setCurrentTab] = useState<ThesisTabId>('overview')
  const { alive } = useArbitrage()

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-[#F2F0EB] font-sans text-[#1A1A1A] antialiased">
      <div className="flex w-[220px] shrink-0 flex-col border-r border-[#2E2E2E] bg-[#1A1A1A]">
        <SidebarNav currentTab={currentTab} onTab={setCurrentTab} />
        <div className="mt-auto border-t border-white/10 p-3">
          <NewsletterCard variant="dark" />
        </div>
      </div>
      <div className="relative min-h-0 min-w-0 flex-1">
        <KineticOrbs botActive={alive} />
        <div className="relative z-10 flex h-full min-h-0 flex-col overflow-hidden px-4 py-4 sm:px-5">
          <header className="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[#E3E3E0] pb-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#6B6B6B]">BCA · Fintech thesis</div>
              <h1 className="text-lg font-semibold tracking-tight sm:text-xl">Arbitrage intelligence desk</h1>
            </div>
            <div
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                alive ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-[#E3E3E0] bg-white text-[#6B6B6B]'
              }`}
            >
              {alive ? 'Bot active' : 'Bot standby'}
            </div>
          </header>
          <main className="min-h-0 flex-1 overflow-hidden">
            {currentTab === 'overview' ? <OverviewView /> : null}
            {currentTab === 'source' ? <SourceIntelligenceView /> : null}
            {currentTab === 'telegram' ? <TelegramView /> : null}
            {currentTab === 'health' ? <HealthView /> : null}
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
