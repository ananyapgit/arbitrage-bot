"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Mail,
  MessageSquare,
  Users,
  TrendingUp,
  CheckCircle2,
  AlertCircle,
  Send,
  QrCode,
  Sparkles,
  UserPlus,
  Activity,
  Check,
  Clock,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getApiUrl } from "@/lib/api-config"

interface SubscriberHubProps {
  className?: string
}

export function SubscriberHub({ className }: SubscriberHubProps) {
  const [email, setEmail] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [errorMessage, setErrorMessage] = useState("")
  const [liveStats, setLiveStats] = useState({
    total: 0,
    email: 0,
    telegram: 0,
    growth: "+0%"
  })
  const [recentActivity, setRecentActivity] = useState<any[]>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, activityRes] = await Promise.all([
          fetch(getApiUrl('/api/dashboard/stats')),
          fetch(getApiUrl('/api/dashboard/subscribers/recent'))
        ])
        
        const statsData = await statsRes.json()
        if (statsData?.subscribers) {
          setLiveStats({
            total: statsData.subscribers.total || 0,
            email: statsData.subscribers.email || 0,
            telegram: statsData.subscribers.telegram || 0,
            growth: statsData.subscribers.growth || "+0%"
          })
        }

        const activityData = await activityRes.json()
        setRecentActivity(Array.isArray(activityData) ? activityData : [])
      } catch (error) {
        console.error("Failed to fetch subscriber stats:", error)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  const validateEmail = (email: string) => {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return regex.test(email)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateEmail(email)) {
      setStatus("error")
      setErrorMessage("Please enter a valid email address")
      return
    }

    setStatus("loading")

    try {
      // In production, we would use a real serverless function or DB.
      // For this deployment, we'll try to use the local API if available.
      const res = await fetch(getApiUrl('/api/dashboard/subscribers/add'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })
      
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.error || "Failed to subscribe")
      }
      
      setStatus("success")
      setEmail("")
      
      // Reset after 3 seconds
      setTimeout(() => setStatus("idle"), 3000)
    } catch (error: any) {
      setStatus("error")
      setErrorMessage(error.message || "Failed to subscribe. Please try again.")
    }
  }

  const stats = [
    { label: "Total Subscribers", value: liveStats.total.toLocaleString(), icon: Users, trend: liveStats.growth },
    { label: "Email List", value: liveStats.email.toLocaleString(), icon: Mail, trend: `${((liveStats.email / (liveStats.total || 1)) * 100).toFixed(0)}% of total` },
    { label: "Telegram Members", value: liveStats.telegram.toLocaleString(), icon: MessageSquare, trend: `${((liveStats.telegram / (liveStats.total || 1)) * 100).toFixed(0)}% of total` },
    { label: "Growth Rate", value: liveStats.growth, icon: TrendingUp, trend: "vs last month" },
  ]

  return (
    <div className={cn("h-full flex flex-col gap-4", className)}>
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((stat, index) => {
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
                  <p className="text-xs text-success mt-1">{stat.trend}</p>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-2 gap-4">
        {/* Newsletter Signup */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-card rounded-xl border border-border shadow-lg p-6 flex flex-col"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-primary/10">
              <Mail className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-card-foreground">Join Our Newsletter</h3>
              <p className="text-sm text-muted-foreground">Get daily arbitrage alerts delivered to your inbox</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (status === "error") setStatus("idle")
                }}
                placeholder="Enter your email address"
                className={cn(
                  "w-full px-4 py-3 rounded-lg border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary transition-all",
                  status === "error" ? "border-destructive" : "border-input"
                )}
              />
              {status === "error" && (
                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-sm text-destructive mt-2 flex items-center gap-1"
                >
                  <AlertCircle className="w-4 h-4" />
                  {errorMessage}
                </motion.p>
              )}
            </div>

            <motion.button
              type="submit"
              disabled={status === "loading" || status === "success"}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "w-full py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all",
                status === "success"
                  ? "bg-success text-success-foreground"
                  : "bg-primary text-primary-foreground hover:opacity-90"
              )}
            >
              <AnimatePresence mode="wait">
                {status === "loading" ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin"
                  />
                ) : status === "success" ? (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-5 h-5" />
                    Successfully Subscribed!
                  </motion.div>
                ) : (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    Subscribe Now
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          </form>

          {/* Features */}
          <div className="mt-6 pt-6 border-t border-border">
            <h4 className="text-sm font-medium text-card-foreground mb-3">What you&apos;ll get:</h4>
            <div className="space-y-2">
              {[
                "Daily curated arbitrage opportunities",
                "Exclusive member-only deals",
                "Market trend analysis & insights",
                "Early access to new features",
              ].map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + index * 0.05 }}
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                >
                  <Sparkles className="w-4 h-4 text-primary" />
                  {feature}
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Telegram Widget */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-card rounded-xl border border-border shadow-lg p-6 flex flex-col"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-info/10">
              <MessageSquare className="w-5 h-5 text-info" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-card-foreground">Join Telegram</h3>
              <p className="text-sm text-muted-foreground">Get instant alerts on your phone</p>
            </div>
          </div>

          {/* QR Code */}
          <div className="flex-1 flex flex-col items-center justify-center">
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="w-48 h-48 bg-white rounded-xl border-2 border-border flex items-center justify-center mb-4 overflow-hidden"
            >
              <img 
                src="/tg-qr.jpeg" 
                alt="Telegram QR Code" 
                className="w-full h-full object-cover p-1"
              />
            </motion.div>

            <p className="text-sm text-muted-foreground text-center mb-4">
              Scan the QR code or click the button below
            </p>

            <motion.a
              href="https://t.me/namma_malige"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 bg-info text-info-foreground hover:opacity-90 transition-all"
            >
              <MessageSquare className="w-4 h-4" />
              Join @namma_malige
            </motion.a>
          </div>

          {/* Telegram Stats */}
          <div className="mt-6 pt-6 border-t border-border">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xl font-bold text-card-foreground">{liveStats.telegram.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground">Members</p>
              </div>
              <div>
                <p className="text-xl font-bold text-card-foreground">24/7</p>
                <p className="text-xs text-muted-foreground">Alerts</p>
              </div>
              <div>
                <p className="text-xl font-bold text-card-foreground">{"<1s"}</p>
                <p className="text-xs text-muted-foreground">Delivery</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Subscribers */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-card rounded-xl border border-border shadow-lg p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-primary" />
            <h4 className="font-medium text-card-foreground">Recent Activity</h4>
          </div>
          <span className="text-xs text-muted-foreground">Last 24 hours</span>
        </div>
        <div className="flex items-center gap-4 overflow-x-auto pb-2 no-scrollbar">
          {recentActivity.map((sub, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + index * 0.05 }}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/30 shrink-0"
            >
              {sub.type === "email" ? (
                <Mail className="w-4 h-4 text-warning" />
              ) : (
                <MessageSquare className="w-4 h-4 text-info" />
              )}
              <div>
                <p className="text-sm font-medium text-card-foreground">{sub.email || sub.user || sub.name}</p>
                <p className="text-xs text-muted-foreground">{sub.time}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
