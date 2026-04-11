import { clsx } from 'clsx'
import { Activity, HeartPulse, Radar, Send } from 'lucide-react'

export type ThesisTabId = 'overview' | 'source' | 'telegram' | 'health'

const NAV: Array<{ id: ThesisTabId; label: string; icon: typeof Activity }> = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'source', label: 'Source Intelligence', icon: Radar },
  { id: 'telegram', label: 'Telegram Analytics', icon: Send },
  { id: 'health', label: 'System Health', icon: HeartPulse },
]

export function SidebarNav({
  currentTab,
  onTab,
}: {
  currentTab: ThesisTabId
  onTab: (t: ThesisTabId) => void
}) {
  return (
    <aside className="flex min-h-0 w-full flex-1 flex-col px-3 py-6 text-white">
      <div className="px-2 pb-6">
        <div className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/45">Thesis</div>
        <div className="mt-1 text-lg font-semibold tracking-tight">Arbitrage</div>
        <div className="text-xs text-white/50">Intelligence Desk</div>
      </div>
      <nav className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto overscroll-contain">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = id === currentTab
          return (
            <button
              key={id}
              type="button"
              onClick={() => onTab(id)}
              className={clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors',
                active ? 'bg-white/10 text-white' : 'text-white/65 hover:bg-white/[0.06] hover:text-white',
              )}
            >
              <Icon className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
              {label}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}
