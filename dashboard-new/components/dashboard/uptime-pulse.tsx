"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Activity, MessageSquare, Mail, Check, AlertCircle, Clock, BarChart3 } from "lucide-react"
import { cn } from "@/lib/utils"
import { getApiUrl } from "@/lib/api-config"

// heatmap and recent deliveries will be fetched from API
interface UptimePulseProps {
  className?: string
}

export function UptimePulse({ className }: UptimePulseProps) {
  const [liveStats, setLiveStats] = useState({
    totalSends: "0",
    telegram: "0",
    email: "0",
    successRate: "0%",
  })
  const [heatmapData, setHeatmapData] = useState<any[]>([])
  const [recentDeliveries, setRecentDeliveries] = useState<any[]>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, heatmapRes] = await Promise.all([
          fetch(getApiUrl('/api/dashboard/stats')),
          fetch(getApiUrl('/api/dashboard/heatmap'))
        ])
        
        const statsData = await statsRes.json()
        setLiveStats({
          totalSends: ((statsData?.telegramSends || 0) + (statsData?.emailSends || 0)).toLocaleString(),
          telegram: (statsData?.telegramSends || 0).toLocaleString(),
          email: (statsData?.emailSends || 0).toLocaleString(),
          successRate: statsData?.successRate || "0%",
        })

        const heatmapJson = await heatmapRes.json()
        if (heatmapJson?.heatmap) {
          setHeatmapData(heatmapJson.heatmap)
        }
        if (heatmapJson?.recent) {
          setRecentDeliveries(heatmapJson.recent)
        }
      } catch (error) {
        console.error("Failed to fetch uptime stats:", error)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  const statsDisplay = [
    { label: "Total Sends", value: liveStats.totalSends, icon: BarChart3, change: "All Time History" },
    { label: "Telegram", value: liveStats.telegram, icon: MessageSquare, change: "Direct Broadcast" },
    { label: "Email", value: liveStats.email, icon: Mail, change: "SMTP Alerts" },
    { label: "Success Rate", value: liveStats.successRate, icon: Check, change: "Live Network Audit" },
  ]

  const getIntensityColor = (value: number) => {
    if (value === 0) return "bg-muted/30"
    if (value < 15) return "bg-success/20"
    if (value < 30) return "bg-success/40"
    if (value < 50) return "bg-success/60"
    return "bg-success/80"
  }

  return (
    <div className={cn("h-full flex flex-col gap-4", className)}>
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        {statsDisplay.map((stat, index) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ y: -2 }}
              className="bg-card rounded-xl border border-border shadow-lg p-4"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-card-foreground">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-xs text-success mt-1">{stat.change}</p>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-3 gap-4">
        {/* Activity Heatmap */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="col-span-2 bg-card rounded-xl border border-border shadow-lg p-6 flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-card-foreground">Activity Heatmap</h3>
              <p className="text-sm text-muted-foreground">Delivery volume over the past week</p>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Less</span>
              <div className="flex gap-1">
                <div className="w-3 h-3 rounded-sm bg-muted/30" />
                <div className="w-3 h-3 rounded-sm bg-success/20" />
                <div className="w-3 h-3 rounded-sm bg-success/40" />
                <div className="w-3 h-3 rounded-sm bg-success/60" />
                <div className="w-3 h-3 rounded-sm bg-success/80" />
              </div>
              <span>More</span>
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            {/* Hour labels */}
            <div className="flex mb-2 pl-12">
              {[0, 3, 6, 9, 12, 15, 18, 21].map((hour) => (
                <div key={hour} className="flex-1 text-xs text-muted-foreground text-center">
                  {hour}:00
                </div>
              ))}
            </div>

            {/* Heatmap grid */}
            <div className="flex-1 space-y-1">
              {heatmapData.map((dayData, dayIndex) => (
                <motion.div
                  key={dayData.day}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: dayIndex * 0.05 }}
                  className="flex items-center gap-2"
                >
                  <span className="w-10 text-xs text-muted-foreground text-right">{dayData.day}</span>
                  <div className="flex-1 flex gap-0.5">
                    {dayData.hours.map((hourData, hourIndex) => (
                      <motion.div
                        key={hourIndex}
                        whileHover={{ scale: 1.5, zIndex: 10 }}
                        className={cn(
                          "flex-1 h-5 rounded-sm cursor-pointer transition-colors",
                          getIntensityColor(hourData.total)
                        )}
                        title={`${dayData.day} ${hourData.hour}:00 - ${hourData.total} sends (${hourData.telegram} TG, ${hourData.email} Email)`}
                      />
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Recent Deliveries */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card rounded-xl border border-border shadow-lg p-4 flex flex-col"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Activity className="w-4 h-4 text-primary" />
            </div>
            <h4 className="font-semibold text-card-foreground">Recent Deliveries</h4>
          </div>

          <div className="flex-1 space-y-2 overflow-auto custom-scrollbar">
            {recentDeliveries.map((delivery, index) => (
              <motion.div
                key={delivery.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.05 }}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div className={cn(
                  "p-1.5 rounded-lg",
                  delivery.type === "telegram" ? "bg-info/10" : "bg-warning/10"
                )}>
                  {delivery.type === "telegram" ? (
                    <MessageSquare className="w-4 h-4 text-info" />
                  ) : (
                    <Mail className="w-4 h-4 text-warning" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-card-foreground truncate">{delivery.recipient}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {delivery.time}
                  </div>
                </div>
                {delivery.status === "success" ? (
                  <Check className="w-4 h-4 text-success" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-destructive" />
                )}
              </motion.div>
            ))}
          </div>

          {/* Live indicator */}
          <div className="mt-3 pt-3 border-t border-border flex items-center justify-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
            </span>
            <span className="text-xs text-muted-foreground">Live updates enabled</span>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
