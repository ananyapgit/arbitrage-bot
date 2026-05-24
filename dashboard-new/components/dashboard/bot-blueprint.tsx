"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import {
  Globe,
  FileSearch,
  ShieldCheck,
  Send,
  ArrowRight,
  CheckCircle2,
  Clock,
  Sparkles,
  Database,
  Bot,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getApiUrl } from "@/lib/api-config"

const modules = [
  {
    id: "scrapers",
    name: "Web Scrapers",
    icon: Globe,
    status: "active",
    description: "Multi-source price monitoring across 50+ retail platforms",
    details: [
      "Amazon, eBay, Walmart, Target",
      "Nike, StockX, GOAT",
      "TCGPlayer, eBay Collectibles",
      "Real-time price tracking",
    ],
    stats: { processed: "12.4K", rate: "240/min" },
  },
  {
    id: "extraction",
    name: "Data Extraction",
    icon: FileSearch,
    status: "active",
    description: "AI-powered product matching and price normalization",
    details: [
      "SKU/UPC matching algorithm",
      "Fuzzy product title matching",
      "Price history aggregation",
      "Condition assessment",
    ],
    stats: { accuracy: "99.2%", latency: "45ms" },
  },
  {
    id: "verification",
    name: "Verification Engine",
    icon: ShieldCheck,
    status: "active",
    description: "Multi-layer validation and risk assessment",
    details: [
      "Seller reputation check",
      "Historical price validation",
      "Stock availability verify",
      "Margin calculation",
    ],
    stats: { validated: "8.2K", rejected: "1.4K" },
  },
  {
    id: "dispatch",
    name: "Sync Dispatch",
    icon: Send,
    status: "active",
    description: "Real-time notification delivery via multiple channels",
    details: [
      "Telegram bot integration",
      "Email SMTP delivery",
      "Priority queue system",
      "Retry & fallback logic",
    ],
    stats: { delivered: "24.6K", success: "99.8%" },
  },
]

interface BotBlueprintProps {
  className?: string
}

export function BotBlueprint({ className }: BotBlueprintProps) {
  const [hoveredModule, setHoveredModule] = useState<string | null>(null)
  const [selectedModule, setSelectedModule] = useState<typeof modules[0] | null>(null)
  const [liveStats, setLiveStats] = useState<any>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(getApiUrl('/api/dashboard/stats'))
        const data = await res.json()
        setLiveStats(data)
      } catch (error) {
        console.error("Failed to fetch blueprint stats:", error)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  const dynamicModules = modules.map(m => {
    if (m.id === "scrapers") {
      return { ...m, stats: { processed: liveStats?.totalOpportunities?.toLocaleString() || "0", rate: "Live Monitoring" } }
    }
    if (m.id === "verification") {
      return { ...m, stats: { validated: liveStats?.accepted?.toLocaleString() || "0", rejected: liveStats?.rejected?.toLocaleString() || "0" } }
    }
    if (m.id === "dispatch") {
      const totalSends = (liveStats?.telegramSends || 0) + (liveStats?.emailSends || 0)
      return { ...m, stats: { delivered: totalSends.toLocaleString(), success: liveStats?.successRate || "0%" } }
    }
    return m
  })

  return (
    <div className={cn("h-full flex flex-col gap-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Live Infrastructure Map</h2>
          <p className="text-sm text-muted-foreground">Real-time data flow visualization</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/20">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
          </span>
          <span className="text-sm font-medium text-success">All Systems Operational</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-3 gap-4">
        {/* Flow Diagram */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="col-span-2 bg-card rounded-xl border border-border shadow-lg p-6 flex items-center justify-center"
        >
          <div className="w-full flex items-center justify-between gap-4">
            {dynamicModules.map((module, index) => {
              const Icon = module.icon
              const isHovered = hoveredModule === module.id
              const isSelected = selectedModule?.id === module.id

              return (
                <div key={module.id} className="flex items-center flex-1">
                  <motion.div
                    onMouseEnter={() => setHoveredModule(module.id)}
                    onMouseLeave={() => setHoveredModule(null)}
                    onClick={() => setSelectedModule(module as any)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.98 }}
                    className={cn(
                      "relative flex flex-col items-center gap-3 p-4 rounded-xl cursor-pointer transition-all duration-200",
                      isHovered || isSelected ? "bg-primary/10" : "bg-muted/30",
                      isSelected && "ring-2 ring-primary"
                    )}
                  >
                    {/* Status indicator */}
                    <div className="absolute top-2 right-2">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
                      </span>
                    </div>

                    {/* Icon */}
                    <motion.div
                      animate={{ y: isHovered ? -5 : 0 }}
                      className={cn(
                        "w-14 h-14 rounded-xl flex items-center justify-center",
                        isHovered || isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                      )}
                    >
                      <Icon className="w-7 h-7" />
                    </motion.div>

                    {/* Label */}
                    <div className="text-center">
                      <p className="text-sm font-medium text-card-foreground">{module.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {module.id === "scrapers" && module.stats.rate}
                        {module.id === "extraction" && (module as any).stats.latency}
                        {module.id === "verification" && `${module.stats.validated} validated`}
                        {module.id === "dispatch" && module.stats.success}
                      </p>
                    </div>

                    {/* Pulse animation */}
                    {(isHovered || isSelected) && (
                      <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1.2, opacity: 0 }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                        className="absolute inset-0 rounded-xl bg-primary/20"
                      />
                    )}
                  </motion.div>

                  {/* Connection Arrow */}
                  {index < dynamicModules.length - 1 && (
                    <div className="flex-1 flex items-center justify-center px-2">
                      <motion.div
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ delay: index * 0.2, duration: 0.5 }}
                        className="flex items-center gap-1"
                      >
                        <div className="h-0.5 flex-1 bg-gradient-to-r from-primary/60 to-primary" />
                        <motion.div
                          animate={{ x: [0, 5, 0] }}
                          transition={{ repeat: Infinity, duration: 1.5 }}
                        >
                          <ArrowRight className="w-4 h-4 text-primary" />
                        </motion.div>
                      </motion.div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Module Details Panel */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-card rounded-xl border border-border shadow-lg p-4 flex flex-col"
        >
          {selectedModule ? (
            <>
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-primary/10">
                  <selectedModule.icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-card-foreground">{selectedModule.name}</h3>
                  <div className="flex items-center gap-1 text-xs text-success">
                    <CheckCircle2 className="w-3 h-3" />
                    Active
                  </div>
                </div>
              </div>

              <p className="text-sm text-muted-foreground mb-4">{selectedModule.description}</p>

              <div className="space-y-2 mb-4">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Capabilities</h4>
                {selectedModule.details.map((detail, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center gap-2 text-sm text-card-foreground"
                  >
                    <Sparkles className="w-3 h-3 text-primary" />
                    {detail}
                  </motion.div>
                ))}
              </div>

              <div className="mt-auto pt-4 border-t border-border">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Performance</h4>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(selectedModule.stats).map(([key, value]) => (
                    <div key={key} className="p-2 rounded-lg bg-muted/30">
                      <p className="text-lg font-bold text-card-foreground">{value}</p>
                      <p className="text-xs text-muted-foreground capitalize">{key}</p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <div className="p-4 rounded-full bg-muted/30 mb-4">
                <Bot className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="font-medium text-card-foreground mb-1">Select a Module</h3>
              <p className="text-sm text-muted-foreground">Click on any module in the flow diagram to view its details</p>
            </div>
          )}
        </motion.div>
      </div>

      {/* Bottom Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Data Processed", value: "2.4TB", icon: Database, color: "text-chart-1" },
          { label: "Avg Latency", value: "142ms", icon: Clock, color: "text-chart-2" },
          { label: "Uptime", value: "99.99%", icon: CheckCircle2, color: "text-success" },
          { label: "Active Bots", value: "12", icon: Bot, color: "text-chart-4" },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.05 }}
            className="bg-card rounded-xl border border-border shadow-md p-3 flex items-center gap-3"
          >
            <stat.icon className={cn("w-5 h-5", stat.color)} />
            <div>
              <p className="text-lg font-bold text-card-foreground">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
