"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  CheckCircle2,
  XCircle,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package,
  Clock,
  X,
  Zap,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface DecisionLabProps {
  className?: string
}

export function DecisionLab({ className }: DecisionLabProps) {
  const [selectedDeal, setSelectedDeal] = useState<any | null>(null)
  const [deals, setDeals] = useState<any[]>([])
  const [stats, setStats] = useState({
    totalOpportunities: 0,
    pending: 0,
    accepted: 0,
    totalProfit: 0,
    workflowStatus: "Active"
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, dealsRes] = await Promise.all([
          fetch('http://localhost:5001/api/dashboard/stats'),
          fetch('http://localhost:5001/api/dashboard/deals')
        ])
        const statsData = await statsRes.json()
        const dealsData = await dealsRes.json()
        
        if (statsData && typeof statsData === 'object' && !statsData.error) {
          setStats(statsData)
        }
        
        if (Array.isArray(dealsData)) {
          setDeals(dealsData)
        } else {
          console.error("API returned non-array deals data:", dealsData)
          setDeals([])
        }
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error)
        setDeals([])
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 15000) // Refresh every 15s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={cn("h-full flex flex-col gap-4", className)}>
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Total Opportunities"
          value={stats.totalOpportunities}
          icon={Package}
          trend="+5%"
          trendUp
        />
        <StatCard
          label="Workflow Status"
          value={stats.workflowStatus}
          icon={Zap}
          variant={
            stats.workflowStatus === "Sleeping" ? "default" :
            stats.workflowStatus === "Scraping" ? "warning" :
            stats.workflowStatus === "Broadcasting" ? "success" : "primary"
          }
        />
        <StatCard
          label="Live Broadcasts"
          value={stats.accepted}
          icon={CheckCircle2}
          variant="success"
        />
        <StatCard
          label="Estimated Revenue"
          value={typeof stats.totalProfit === 'number' ? `₹${stats.totalProfit.toLocaleString()}` : stats.totalProfit}
          icon={DollarSign}
          variant="primary"
        />
      </div>

      {/* Data Table */}
      <div className="flex-1 bg-card rounded-xl border border-border shadow-lg overflow-hidden flex flex-col">
        <div className="px-6 py-4 border-b border-border bg-card">
          <h3 className="text-lg font-semibold text-card-foreground">Command Stream</h3>
          <p className="text-sm text-muted-foreground">Real-time bot execution logs and deal flow</p>
        </div>

        <div className="flex-1 overflow-auto custom-scrollbar">
          <table className="w-full">
            <thead className="sticky top-0 bg-muted/50 backdrop-blur-sm">
              <tr className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <th className="px-6 py-3">Product / Event</th>
                <th className="px-6 py-3 text-center">Route</th>
                <th className="px-6 py-3 text-center">Price</th>
                <th className="px-6 py-3 text-center">MRP</th>
                <th className="px-6 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {Array.isArray(deals) && deals.map((deal, index) => (
                <motion.tr
                  key={deal.id || `deal-${index}-${deal.timestamp}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.05, 0.5) }}
                  onClick={() => setSelectedDeal(deal)}
                  className="group hover:bg-muted/30 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
                        deal.status === 'accepted' ? "bg-success/10 text-success" : 
                        deal.status === 'rejected' ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary"
                      )}>
                        <Package className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-card-foreground text-sm truncate max-w-[400px]">{deal.product}</p>
                        <p className="text-xs text-muted-foreground font-mono uppercase">{deal.category}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center gap-2 text-xs font-mono">
                      <span className="text-muted-foreground truncate max-w-[80px]">{deal.source}</span>
                      <ChevronRight className="w-3 h-3 text-muted-foreground shrink-0" />
                      <span className={cn(
                        "font-medium",
                        deal.target === 'System Alert' ? "text-warning" : "text-card-foreground"
                      )}>{deal.target || 'TG/Email'}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className="text-success font-semibold font-mono">{deal.buyPrice}</span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className="text-muted-foreground line-through text-xs font-mono">{deal.sellPrice}</span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <StatusBadge status={deal.status} />
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Side Panel */}
      <AnimatePresence>
        {selectedDeal && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-96 bg-card border-l border-border shadow-2xl z-50 flex flex-col"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h3 className="font-semibold text-card-foreground">Event Analysis</h3>
              <button
                onClick={() => setSelectedDeal(null)}
                className="p-1 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>
            <div className="flex-1 p-6 overflow-auto custom-scrollbar space-y-6">
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Product</span>
                <p className="mt-1 text-card-foreground font-medium">{selectedDeal.product}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Buy Price</span>
                  <p className="mt-1 text-xl font-bold text-card-foreground font-mono">{selectedDeal.buyPrice}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Original Price</span>
                  <p className="mt-1 text-xl font-bold text-muted-foreground/50 line-through font-mono">{selectedDeal.sellPrice}</p>
                </div>
              </div>
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</span>
                <div className="mt-2">
                  <StatusBadge status={selectedDeal.status} />
                </div>
              </div>
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Engine Reasoning</span>
                <div className="mt-2 p-4 rounded-lg bg-muted/50 border border-border">
                  <p className="text-sm text-card-foreground leading-relaxed italic">"{selectedDeal.reason}"</p>
                </div>
              </div>
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Timestamp</span>
                <p className="mt-1 text-sm text-muted-foreground font-mono">{selectedDeal.timestamp}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  trendUp,
  variant = "default",
}: {
  label: string
  value: string | number
  icon: React.ElementType
  trend?: string
  trendUp?: boolean
  variant?: "default" | "primary" | "success" | "warning"
}) {
  const variants = {
    default: "bg-card",
    primary: "bg-primary/10",
    success: "bg-success/10",
    warning: "bg-warning/10",
  }

  const iconVariants = {
    default: "text-muted-foreground",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
  }

  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.01 }}
      className={cn(
        "p-4 rounded-xl border border-border shadow-md transition-all duration-300",
        variants[variant]
      )}
    >
      <div className="flex items-center justify-between">
        <div className={cn("p-2 rounded-lg bg-muted/50", variant !== "default" && "bg-card/50 shadow-sm")}>
          <Icon className={cn("w-5 h-5", iconVariants[variant])} />
        </div>
        {trend && (
          <div className={cn(
            "flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full tracking-tighter",
            trendUp ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
          )}>
            {trendUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trend}
          </div>
        )}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold text-card-foreground tracking-tight">{value}</p>
        <p className="text-sm text-muted-foreground mt-1">{label}</p>
      </div>
    </motion.div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const variants = {
    pending: "bg-warning/10 text-warning border-warning/20",
    accepted: "bg-success/10 text-success border-success/20",
    rejected: "bg-destructive/10 text-destructive border-destructive/20",
    alert: "bg-primary/10 text-primary border-primary/20",
    shadow: "bg-muted/50 text-muted-foreground border-muted",
  }

  const label = status === 'accepted' ? 'BROADCAST' : status === 'rejected' ? 'FILTERED' : status.toUpperCase()

  return (
    <span className={cn(
      "inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold tracking-widest border font-mono",
      variants[status as keyof typeof variants] || variants.pending
    )}>
      {label}
    </span>
  )
}
