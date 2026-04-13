import { useState } from 'react'
import { ArbitrageDataProvider } from '../data/ArbitrageDataProvider'
import { KineticCommandCenter } from '../components/KineticCommandCenter'
import { NewsletterCard } from './fintech/NewsletterCard'
import { SidebarNav, type ThesisTabId } from './fintech/SidebarNav'

function ThesisShell() {
  const [currentTab, setCurrentTab] = useState<ThesisTabId>('elite')

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-[#F2F0EB] font-sans text-[#E6EDF3] antialiased">
      <div className="flex w-[220px] shrink-0 flex-col border-r border-[#2E2E2E] bg-[#1A1A1A]">
        <SidebarNav currentTab={currentTab} onTab={setCurrentTab} />
        <div className="mt-auto border-t border-white/10 p-3">
          <NewsletterCard variant="dark" />
        </div>
      </div>
      <div className="relative min-h-0 min-w-0 flex-1">
        <div className="relative z-10 flex h-full min-h-0 flex-col overflow-hidden px-4 py-4 sm:px-5">
          <main className="min-h-0 flex-1 overflow-hidden">
            {currentTab === 'elite' ? <KineticCommandCenter /> : null}
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
