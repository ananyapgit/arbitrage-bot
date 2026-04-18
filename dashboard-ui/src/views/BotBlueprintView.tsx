import { Bot, Cpu, Layers, ShieldCheck, Workflow } from 'lucide-react'

const features = [
  { icon: Workflow, title: 'Atomic Sync Engine', body: 'Telegram and Email dispatch fire in parallel via asyncio.gather().' },
  { icon: Cpu, title: 'Deep JS Parsing', body: 'Amazon price extraction uses JSON-LD and twister JS metadata fallback.' },
  { icon: ShieldCheck, title: 'Validation Gates', body: 'Numeric price, affiliate link integrity, dedupe, and audit logging.' },
  { icon: Layers, title: 'Parallel Multi-Source', body: 'Amazon, Flipkart, Couponami, and EarnKaro scrape streams unify per batch.' },
]

export function BotBlueprintView() {
  return (
    <div className="grid h-full min-h-0 grid-cols-12 gap-3">
      <div className="col-span-12 rounded-2xl border border-white/10 bg-[#121821] p-4 text-[#E6EDF3]">
        <div className="inline-flex items-center gap-2 text-sm font-semibold">
          <Bot className="h-4 w-4 text-indigo-300" />
          Bot Blueprint
        </div>
        <div className="mt-1 text-xs text-white/60">Production architecture and capabilities</div>
      </div>
      {features.map((f) => {
        const Icon = f.icon
        return (
          <div
            key={f.title}
            className="col-span-12 rounded-2xl border border-white/10 bg-[#121821] p-4 text-[#E6EDF3] transition-transform hover:-translate-y-0.5 md:col-span-6"
          >
            <div className="inline-flex items-center gap-2 text-sm font-semibold">
              <Icon className="h-4 w-4 text-indigo-300" />
              {f.title}
            </div>
            <div className="mt-2 text-xs text-white/65">{f.body}</div>
          </div>
        )
      })}
    </div>
  )
}
