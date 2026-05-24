"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts"
import { TrendingUp, BarChart3, Layers } from "lucide-react"
import { cn } from "@/lib/utils"
import { getApiUrl } from "@/lib/api-config"

interface CategoryMatrixProps {
  className?: string
}

export function CategoryMatrix({ className }: CategoryMatrixProps) {
  const [radarData, setRadarData] = useState<any[]>([
    { category: "Electronics", volume: 50, profit: 60, success: 95 },
    { category: "Fashion", volume: 40, profit: 55, success: 92 },
    { category: "Home", volume: 35, profit: 50, success: 90 },
    { category: "Toys", volume: 30, profit: 45, success: 88 },
  ])
  const [pieData, setPieData] = useState<any[]>([
    { name: "Electronics", value: 3500, color: "var(--chart-1)" },
    { name: "Fashion", value: 2800, color: "var(--chart-2)" },
    { name: "Home", value: 2100, color: "var(--chart-3)" },
    { name: "Toys", value: 1500, color: "var(--chart-4)" },
  ])
  const [topCategories, setTopCategories] = useState<any[]>([
    { name: "Electronics", deals: 3500, profit: "₹525,000", growth: "95%" },
    { name: "Fashion", deals: 2800, profit: "₹420,000", growth: "92%" },
    { name: "Home", deals: 2100, profit: "₹315,000", growth: "90%" },
    { name: "Toys", deals: 1500, profit: "₹225,000", growth: "88%" },
  ])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(getApiUrl('/api/dashboard/categories'))
        const data = await res.json()
        
        if (Array.isArray(data)) {
          // Transform for charts
          setPieData(data.map((item: any, i: number) => ({
            ...item,
            color: `var(--chart-${(i % 5) + 1})`
          })))

          setRadarData(data.map((item: any) => ({
            category: item.name || "Unknown",
            volume: Math.min((item.volume || 0) * 5, 100), // Scale volume for radar
            profit: Math.min(((item.profit || 0) / 1000) * 100, 100), // Scale profit (assuming 1000 is max for radar)
            success: parseFloat(item.successRate) || 0
          })))

          // Transform for top categories list
          setTopCategories(data
            .sort((a: any, b: any) => (b.value || 0) - (a.value || 0))
            .slice(0, 4)
            .map((item: any) => ({
              name: item.name || "Unknown",
              deals: item.value || 0,
              profit: `₹${(item.profit || 0).toLocaleString()}`,
              growth: item.successRate || "0%"
            })))
        }
      } catch (error) {
        console.error("Failed to fetch categories:", error)
      }
    }
    fetchData()
  }, [])

  const totalDeals = pieData.reduce((sum, item) => sum + (item.value || 0), 0)

  return (
    <div className={cn("h-full grid grid-cols-3 gap-4", className)}>
      {/* Radar Chart */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="col-span-2 bg-card rounded-xl border border-border shadow-lg p-6 flex flex-col"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-card-foreground">Performance Matrix</h3>
            <p className="text-sm text-muted-foreground">Volume, Profit & Success Rate by Category</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-1" />
              <span className="text-muted-foreground">Volume</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-2" />
              <span className="text-muted-foreground">Profit</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-chart-3" />
              <span className="text-muted-foreground">Success</span>
            </div>
          </div>
        </div>
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
              <PolarGrid strokeDasharray="3 3" stroke="var(--border)" />
              <PolarAngleAxis
                dataKey="category"
                tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 100]}
                tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
              />
              <Radar
                name="Volume"
                dataKey="volume"
                stroke="var(--chart-1)"
                fill="var(--chart-1)"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Radar
                name="Profit"
                dataKey="profit"
                stroke="var(--chart-2)"
                fill="var(--chart-2)"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Radar
                name="Success"
                dataKey="success"
                stroke="var(--chart-3)"
                fill="var(--chart-3)"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
                labelStyle={{ color: "var(--card-foreground)", fontWeight: 600 }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Right Column */}
      <div className="flex flex-col gap-4">
        {/* Pie Chart */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="flex-1 bg-card rounded-xl border border-border shadow-lg p-4 flex flex-col"
        >
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <Layers className="w-4 h-4 text-primary" />
            </div>
            <h4 className="font-semibold text-card-foreground text-sm">Deal Distribution</h4>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius="55%"
                  outerRadius="80%"
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-card-foreground">{totalDeals}</p>
            <p className="text-xs text-muted-foreground">Total Deals</p>
          </div>
        </motion.div>

        {/* Top Categories List */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="flex-1 bg-card rounded-xl border border-border shadow-lg p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="p-1.5 rounded-lg bg-success/10">
              <BarChart3 className="w-4 h-4 text-success" />
            </div>
            <h4 className="font-semibold text-card-foreground text-sm">Top Categories</h4>
          </div>
          <div className="space-y-3">
            {topCategories.map((category, index) => (
              <motion.div
                key={category.name}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.05 }}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-card-foreground">{category.name}</p>
                    <p className="text-xs text-muted-foreground">{category.deals} deals</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-success">{category.profit}</p>
                  <div className="flex items-center gap-1 text-xs text-success">
                    <TrendingUp className="w-3 h-3" />
                    {category.growth}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
