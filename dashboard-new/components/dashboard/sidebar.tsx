"use client"

import { motion } from "framer-motion"
import {
  FlaskConical,
  LayoutGrid,
  Activity,
  Workflow,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  Store,
} from "lucide-react"
import { useTheme } from "@/contexts/theme-context"
import { cn } from "@/lib/utils"

interface SidebarProps {
  isCollapsed: boolean
  onToggle: () => void
  activeTab: string
  onTabChange: (tab: string) => void
}

const menuItems = [
  { id: "decision-lab", label: "Command Stream", icon: FlaskConical },
  { id: "category-matrix", label: "Category Matrix", icon: LayoutGrid },
  { id: "bot-blueprint", label: "Bot Blueprint", icon: Workflow },
  { id: "uptime-pulse", label: "Uptime Pulse", icon: Activity },
  { id: "subscriber-hub", label: "Subscriber Hub", icon: Users },
]

export function Sidebar({ isCollapsed, onToggle, activeTab, onTabChange }: SidebarProps) {
  const { theme, toggleTheme } = useTheme()

  return (
    <motion.aside
      initial={false}
      animate={{ width: isCollapsed ? 72 : 240 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative h-full bg-sidebar border-r border-sidebar-border flex flex-col z-20"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10">
          <Store className="w-5 h-5 text-primary" strokeWidth={1.5} />
        </div>
        <motion.div
          initial={false}
          animate={{ opacity: isCollapsed ? 0 : 1, width: isCollapsed ? 0 : "auto" }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <span className="text-lg font-bold text-foreground whitespace-nowrap">Namma Malige</span>
          <span className="block text-xs text-muted-foreground whitespace-nowrap">Command Center</span>
        </motion.div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2">
        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            return (
              <motion.button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                  "hover:bg-sidebar-accent group relative",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground/70 hover:text-sidebar-foreground"
                )}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-full"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <Icon className={cn("w-5 h-5 shrink-0", isActive && "text-primary")} />
                <motion.span
                  initial={false}
                  animate={{ opacity: isCollapsed ? 0 : 1, width: isCollapsed ? 0 : "auto" }}
                  transition={{ duration: 0.2 }}
                  className="text-sm font-medium overflow-hidden whitespace-nowrap"
                >
                  {item.label}
                </motion.span>
              </motion.button>
            )
          })}
        </div>
      </nav>

      {/* Bottom Actions */}
      <div className="p-2 border-t border-sidebar-border space-y-1">
        {/* Theme Toggle */}
        <motion.button
          onClick={toggleTheme}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-all"
        >
          {theme === "dark" ? (
            <Sun className="w-5 h-5 shrink-0" />
          ) : (
            <Moon className="w-5 h-5 shrink-0" />
          )}
          <motion.span
            initial={false}
            animate={{ opacity: isCollapsed ? 0 : 1, width: isCollapsed ? 0 : "auto" }}
            transition={{ duration: 0.2 }}
            className="text-sm font-medium overflow-hidden whitespace-nowrap"
          >
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </motion.span>
        </motion.button>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center shadow-lg hover:bg-accent transition-colors z-30"
      >
        {isCollapsed ? (
          <ChevronRight className="w-3 h-3 text-foreground" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-foreground" />
        )}
      </button>
    </motion.aside>
  )
}
