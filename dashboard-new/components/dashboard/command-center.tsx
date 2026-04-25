"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Bell, Search, User, Zap } from "lucide-react"
import { Sidebar } from "./sidebar"
import { DecisionLab } from "./decision-lab"
import { CategoryMatrix } from "./category-matrix"
import { UptimePulse } from "./uptime-pulse"
import { BotBlueprint } from "./bot-blueprint"
import { SubscriberHub } from "./subscriber-hub"
import { NeuralGrid } from "../neural-grid"
import { cn } from "@/lib/utils"

const tabs = {
  "decision-lab": DecisionLab,
  "category-matrix": CategoryMatrix,
  "bot-blueprint": BotBlueprint,
  "uptime-pulse": UptimePulse,
  "subscriber-hub": SubscriberHub,
}

const tabTitles = {
  "decision-lab": "Command Stream",
  "category-matrix": "Category Matrix",
  "bot-blueprint": "Bot Blueprint",
  "uptime-pulse": "Uptime Pulse",
  "subscriber-hub": "Subscriber Hub",
}

export function CommandCenter() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<keyof typeof tabs>("decision-lab")
  const [botStatus, setBotStatus] = useState("Sleeping")

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://localhost:5001/api/dashboard/stats')
        const data = await res.json()
        setBotStatus(data.workflowStatus)
      } catch (error) {
        console.error("Failed to fetch bot status:", error)
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 15000)
    return () => clearInterval(interval)
  }, [])

  const ActiveComponent = tabs[activeTab]

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-background relative">
      {/* Neural Grid Background */}
      <NeuralGrid />

      {/* Sidebar */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab as keyof typeof tabs)}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden z-10">
        {/* Header */}
        <header className="h-16 border-b border-border bg-card/80 backdrop-blur-sm flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-foreground">{tabTitles[activeTab]}</h1>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                Live
              </span>
              <div className={cn(
                "flex items-center gap-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
                botStatus === "Sleeping" ? "bg-muted/10 text-muted-foreground border-border" :
                botStatus === "Scraping" ? "bg-warning/10 text-warning border-warning/20" :
                botStatus === "Broadcasting" ? "bg-success/10 text-success border-success/20" :
                "bg-primary/10 text-primary border-primary/20"
              )}>
                <Zap className={cn("w-3 h-3", botStatus !== "Sleeping" && "animate-pulse fill-current")} />
                {botStatus}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Header elements removed per request: Search, Notifications, User */}
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 p-6 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <ActiveComponent className="h-full" />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}
