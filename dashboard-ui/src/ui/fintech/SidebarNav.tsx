import { clsx } from 'clsx'
import { Activity, BookOpen, LayoutDashboard, PieChart, Zap } from 'lucide-react'

export type ThesisTabId = 'elite' | 'decision' | 'matrix' | 'uptime' | 'blueprint'

const NAV: Array<{ id: ThesisTabId; label: string; icon: typeof Activity }> = [
  { id: 'elite', label: 'Kinetic Command', icon: LayoutDashboard },
  { id: 'decision', label: 'Decision Lab', icon: Zap },
  { id: 'matrix', label: 'Category Matrix', icon: PieChart },
  { id: 'uptime', label: 'Uptime Pulse', icon: Activity },
  { id: 'blueprint', label: 'Bot Blueprint', icon: BookOpen },
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
        <div className="text-[10px] font-medium uppercase tracking-[0.2em] text-white/45">Engine</div>
        <div className="mt-1 text-lg font-semibold tracking-tight">Superbot</div>
        <div className="text-xs text-white/50">Control Center</div>
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
