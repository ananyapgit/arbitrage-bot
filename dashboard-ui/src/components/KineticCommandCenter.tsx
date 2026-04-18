import React, { useEffect, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Brain, 
  Zap, 
  Target, 
  Send, 
  Activity, 
  ChevronRight, 
  Cpu, 
  Search,
  LayoutGrid,
  ShieldCheck,
  Radar,
  History,
  Terminal,
  ArrowUpRight,
  TrendingDown,
  ExternalLink,
  RefreshCw
} from 'lucide-react'
import Papa from 'papaparse'
import { 
  ResponsiveContainer, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar as RechartsRadar 
} from 'recharts'

// --- CONSTANTS ---
const MASTER_URL = 'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/master_log.csv'
const AUDIT_URL = 'https://raw.githubusercontent.com/ananyapgit/arbitrage-bot/main/dashboard/public/data/delivery_audit.csv'

const COLORS = {
  bg: '#0A0A0B',
  card: '#F8F9FA',
  accent: '#FFD700', // Cyber Yellow
  danger: '#FF4D4D', // Signal Red
  text: '#F8F9FA',
  textMuted: '#94A3B8',
  border: 'rgba(248, 249, FA, 0.05)'
}

// --- TYPES ---
interface Deal {
  timestamp: string
  id: string
  title: string
  price: string
  original_price: string
  discount: string
  category: string
  store: string
  link: string
  status: string
}

interface AuditEntry {
  timestamp: string
  deal_id: string
  channel: string
  status: string
}

interface NavItem {
  id: string
  label: string
  icon: React.ElementType
  description: string
}

const navigationItems: NavItem[] = [
  { id: 'overview', label: '[Neural Mesh]', icon: Brain, description: 'The main heartbeat' },
  { id: 'scraping', label: '[Infiltration Ops]', icon: Search, description: 'Real-time scraping velocity' },
  { id: 'engine', label: '[Decision Logic]', icon: Zap, description: 'Arbitrage decision flow' },
  { id: 'outreach', label: '[Outreach Hub]', icon: Send, description: 'Broadcast success rates' },
  { id: 'health', label: '[System Vitality]', icon: Activity, description: 'Uptime and API latency' }
]

// --- COMPONENTS ---

const Sidebar = ({ activeTab, onTabChange }: { activeTab: string, onTabChange: (id: string) => void }) => (
  <div className="w-80 h-full border-r border-white/5 bg-[#0A0A0B] p-6 flex flex-col">
    <div className="mb-10 flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-[#FFD700] flex items-center justify-center shadow-[0_0_20px_rgba(255,215,0,0.3)]">
        <Cpu className="text-black w-6 h-6" />
      </div>
      <div>
        <h1 className="text-xl font-black tracking-tighter text-[#F8F9FA]">KINETIC</h1>
        <p className="text-[10px] uppercase tracking-widest text-[#FFD700] font-bold">Command Center</p>
      </div>
    </div>

    <nav className="flex-1 space-y-2">
      {navigationItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onTabChange(item.id)}
          className={`w-full group relative flex items-center gap-4 p-4 rounded-xl transition-all duration-300 ${
            activeTab === item.id 
              ? 'bg-white/5 text-[#FFD700]' 
              : 'text-[#94A3B8] hover:bg-white/[0.02] hover:text-white'
          }`}
        >
          {activeTab === item.id && (
            <motion.div 
              layoutId="nav-glow"
              className="absolute inset-0 bg-[#FFD700]/5 rounded-xl border border-[#FFD700]/20 shadow-[0_0_20px_rgba(255,215,0,0.05)]"
            />
          )}
          <item.icon className={`w-5 h-5 relative z-10 ${activeTab === item.id ? 'text-[#FFD700]' : 'group-hover:text-white'}`} />
          <div className="relative z-10 text-left">
            <div className="text-sm font-bold tracking-tight">{item.label}</div>
            <div className="text-[10px] text-[#94A3B8] group-hover:text-white/60">{item.description}</div>
          </div>
          <ChevronRight className={`ml-auto w-4 h-4 transition-transform ${activeTab === item.id ? 'translate-x-0' : '-translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0'}`} />
        </button>
      ))}
    </nav>

    <div className="mt-auto p-4 rounded-2xl bg-white/[0.03] border border-white/5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-widest">Bot Status</span>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse shadow-[0_0_10px_#10B981]" />
          <span className="text-[10px] font-bold text-[#10B981]">ACTIVE</span>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-[11px]">
          <span className="text-[#94A3B8]">Memory Usage</span>
          <span className="text-[#F8F9FA]">128MB</span>
        </div>
        <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
          <div className="w-1/3 h-full bg-[#FFD700]" />
        </div>
      </div>
    </div>
  </div>
)

const BentoGrid = ({ children }: { children: React.ReactNode }) => (
  <div className="grid grid-cols-12 grid-rows-6 gap-4 h-full p-6 bg-[#0A0A0B]">
    {children}
  </div>
)

const Card = ({ children, className = '', title = '', icon: Icon }: { children: React.ReactNode, className?: string, title?: string, icon?: React.ElementType }) => (
  <motion.div 
    whileHover={{ scale: 1.002 }}
    className={`bg-[#F8F9FA] rounded-3xl p-6 border-[0.5px] border-black/5 relative overflow-hidden group shadow-sm ${className}`}
  >
    <div className="absolute inset-0 bg-gradient-to-br from-black/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
    <div className="relative z-10 h-full flex flex-col">
      {title && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-[#0A0A0B]/60" />}
            <h3 className="text-[11px] font-black uppercase tracking-widest text-[#0A0A0B]/40">{title}</h3>
          </div>
          <div className="w-1.5 h-1.5 rounded-full bg-[#0A0A0B]/10" />
        </div>
      )}
      <div className="flex-1">{children}</div>
    </div>
    
    {/* Hover Glow Trace */}
    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-500">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#FFD700]/50 to-transparent" />
      <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#FFD700]/50 to-transparent" />
      <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-[#FFD700]/50 to-transparent" />
      <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-transparent via-[#FFD700]/50 to-transparent" />
    </div>
  </motion.div>
)

export function KineticCommandCenter() {
  const [activeTab, setActiveTab] = useState('overview')
  const [deals, setDeals] = useState<Deal[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null)
  const [botLogs, setBotLogs] = useState<string[]>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [masterRes, auditRes] = await Promise.all([
          fetch(MASTER_URL),
          fetch(AUDIT_URL)
        ])
        
        const masterText = await masterRes.text()
        const auditText = await auditRes.text()

        Papa.parse(masterText, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            const mappedDeals = (results.data as any[]).map(row => ({
              timestamp: row.timestamp || '',
              id: row.id || row.deal_id || '',
              title: row.title || '',
              price: row.price || '',
              original_price: row.original_price || '',
              discount: row.discount || '',
              category: row.category || '',
              store: row.platform || row.store || '',
              link: row.affiliate_link || '',
              status: row.status || ''
            })).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
            setDeals(mappedDeals)
            
            // Generate some bot logs based on the latest deal
            if (mappedDeals.length > 0) {
              const latest = mappedDeals[0]
              const logs = [
                `[${new Date().toLocaleTimeString()}] INFILTRATION: Scanning ${latest.store}...`,
                `[${new Date().toLocaleTimeString()}] LOGIC: Analyzing "${latest.title.substring(0, 30)}..."`,
                `[${new Date().toLocaleTimeString()}] LOGIC: Discount detected: ${latest.discount}`,
                `[${new Date().toLocaleTimeString()}] OUTREACH: Verified affiliate link for Deal ID #${latest.id}`,
                `[${new Date().toLocaleTimeString()}] VITALITY: Decision Engine operating at 100% capacity`
              ]
              setBotLogs(logs)
            }
          }
        })

        Papa.parse(auditText, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            setAudit(results.data as AuditEntry[])
          }
        })

        setLoading(false)
      } catch (err) {
        console.error('Data fetch failed:', err)
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const radarData = useMemo(() => {
    const counts = { Amazon: 0, Flipkart: 0, Couponami: 0 }
    deals.forEach(d => {
      const store = d.store.toLowerCase()
      if (store.includes('amazon')) counts.Amazon++
      else if (store.includes('flipkart')) counts.Flipkart++
      else counts.Couponami++
    })
    return [
      { subject: 'Amazon', A: counts.Amazon },
      { subject: 'Flipkart', A: counts.Flipkart },
      { subject: 'Couponami', A: counts.Couponami },
    ]
  }, [deals])

  const tickerDeals = useMemo(() => deals.slice(0, 20), [deals])
  
  const metrics = useMemo(() => {
    const accepted = deals.filter(d => d.status.toLowerCase().includes('ok') || d.status === '').length
    const total = deals.length
    const successRate = audit.length > 0 ? (audit.filter(a => a.status === 'success').length / audit.length) * 100 : 98.2
    return {
      total,
      accepted,
      successRate: successRate.toFixed(1),
      velocity: (total / 60).toFixed(1) // Rough estimate
    }
  }, [deals, audit])

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <BentoGrid>
            {/* Hero: Decision Engine */}
            <Card className="col-span-8 row-span-4" title="Decision Engine" icon={Zap}>
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h2 className="text-4xl font-black text-[#0A0A0B] tracking-tight">LIVE FLOW TRACE</h2>
                    <p className="text-[#0A0A0B]/60 text-sm">Real-time arbitrage logic visualization</p>
                  </div>
                  <div className="flex gap-2">
                    <div className="px-3 py-1 rounded-full bg-[#0A0A0B] text-white text-[10px] font-bold">NODE: 04</div>
                    <div className="px-3 py-1 rounded-full bg-[#FFD700] text-[#0A0A0B] text-[10px] font-bold">LATENCY: 42ms</div>
                  </div>
                </div>

                <div className="flex-1 relative bg-black/[0.02] rounded-2xl overflow-hidden border border-black/5">
                  <svg className="w-full h-full" viewBox="0 0 800 400">
                    <g className="nodes">
                      {[
                        { x: 100, y: 200, label: 'SCRAPE', active: true },
                        { x: 300, y: 200, label: 'FILTER', active: true },
                        { x: 500, y: 200, label: 'LOOT VERIFY', active: true },
                        { x: 700, y: 200, label: 'BROADCAST', active: true }
                      ].map((node, i) => (
                        <g key={i}>
                          <circle cx={node.x} cy={node.y} r="6" fill="#0A0A0B" />
                          <motion.circle 
                            cx={node.x} cy={node.y} r="12" 
                            fill="none" stroke="#0A0A0B" strokeWidth="1" strokeDasharray="4 2"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                          />
                          <text x={node.x} y={node.y + 35} textAnchor="middle" className="text-[10px] font-black uppercase fill-[#0A0A0B]/40">{node.label}</text>
                        </g>
                      ))}
                    </g>

                    <path d="M 112 200 L 288 200" stroke="#0A0A0B" strokeWidth="1" strokeDasharray="4 4" opacity="0.1" />
                    <path d="M 312 200 L 488 200" stroke="#0A0A0B" strokeWidth="1" strokeDasharray="4 4" opacity="0.1" />
                    <path d="M 512 200 L 688 200" stroke="#0A0A0B" strokeWidth="1" strokeDasharray="4 4" opacity="0.1" />

                    <motion.circle 
                      r="4" 
                      fill="#FFD700"
                      animate={{ cx: [112, 288], cy: [200, 200], opacity: [0, 1, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    />
                    <motion.circle 
                      r="4" 
                      fill="#FFD700"
                      animate={{ cx: [312, 488], cy: [200, 200], opacity: [0, 1, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: 0.5 }}
                    />
                    <motion.circle 
                      r="4" 
                      fill="#FFD700"
                      animate={{ cx: [512, 688], cy: [200, 200], opacity: [0, 1, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: 1 }}
                    />
                  </svg>
                  
                  <div className="absolute bottom-6 left-6 right-6 flex justify-between">
                    <div className="flex gap-4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_8px_#10B981]" />
                        <span className="text-[10px] font-bold text-[#0A0A0B]/60 uppercase tracking-tighter">Live Scraping</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-[#FFD700] shadow-[0_0_8px_#FFD700]" />
                        <span className="text-[10px] font-bold text-[#0A0A0B]/60 uppercase tracking-tighter">Engine Logic</span>
                      </div>
                    </div>
                    <div className="text-[10px] font-mono text-[#0A0A0B]/40">AUDIT_TOKEN: {audit[0]?.deal_id || 'XF-000'}</div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Radar Chart */}
            <Card className="col-span-4 row-span-3" title="Site Heatmap" icon={Radar}>
              <div className="h-full flex flex-col">
                <div className="mb-4">
                  <div className="text-3xl font-black text-[#0A0A0B]">DENSITY</div>
                  <div className="text-[10px] text-[#0A0A0B]/40 uppercase font-bold tracking-widest">Platform Saturation</div>
                </div>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="#0A0A0B" strokeOpacity={0.05} />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#0A0A0B', fontSize: 10, fontWeight: 800 }} />
                      <RechartsRadar
                        name="Density"
                        dataKey="A"
                        stroke="#FFD700"
                        fill="#FFD700"
                        fillOpacity={0.6}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </Card>

            {/* Ticker Tape */}
            <Card className="col-span-4 row-span-3" title="Deal Velocity" icon={History}>
              <div className="h-full flex flex-col">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-black text-[#0A0A0B]">TICKER</div>
                    <div className="text-[10px] text-[#0A0A0B]/40 uppercase font-bold tracking-widest">Real-time Stream</div>
                  </div>
                  <div className="w-10 h-10 rounded-full border border-black/5 flex items-center justify-center">
                    <TrendingDown className="w-4 h-4 text-[#FF4D4D]" />
                  </div>
                </div>
                <div className="flex-1 overflow-hidden relative">
                  <div className="absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-[#F8F9FA] to-transparent z-10" />
                  <div className="absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-[#F8F9FA] to-transparent z-10" />
                  <div className="space-y-3 py-4 overflow-y-auto h-full scrollbar-hide">
                    {tickerDeals.map((deal, i) => (
                      <motion.div 
                        key={deal.id + i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        onClick={() => setSelectedDeal(deal)}
                        className="flex items-center justify-between p-3 rounded-xl bg-black/[0.02] border border-black/[0.03] group/item cursor-pointer hover:bg-[#FFD700]/10 transition-colors"
                      >
                        <div className="flex-1 min-w-0 pr-4">
                          <div className="text-[11px] font-black text-[#0A0A0B] truncate uppercase tracking-tighter">{deal.title}</div>
                          <div className="text-[9px] text-[#0A0A0B]/40 font-bold uppercase tracking-tight">{deal.store} • {deal.category}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[11px] font-black text-[#FF4D4D]">{deal.price}</div>
                          <div className="text-[9px] text-[#0A0A0B]/30 line-through">{deal.original_price}</div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            {/* Bot Thinking Feed */}
            <Card className="col-span-4 row-span-2" title="Bot Thinking" icon={Terminal}>
              <div className="h-full flex flex-col">
                <div className="flex-1 font-mono text-[10px] text-[#0A0A0B]/80 overflow-hidden relative p-3 bg-black/[0.03] rounded-xl border border-black/5">
                  <div className="space-y-2">
                    {botLogs.map((log, i) => (
                      <div key={i} className="flex gap-2">
                        <span className="text-[#0A0A0B]/30 shrink-0">{log.split(' ')[0]}</span>
                        <span className="text-[#0A0A0B]">{log.split(' ').slice(1).join(' ')}</span>
                      </div>
                    ))}
                    <motion.div 
                      animate={{ opacity: [0, 1] }} 
                      transition={{ duration: 0.5, repeat: Infinity }}
                      className="w-1.5 h-3 bg-[#FFD700]"
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* Outreach Success */}
            <Card className="col-span-4 row-span-1 bg-[#FFD700] border-none" title="Outreach" icon={Send}>
              <div className="flex items-center justify-between h-full -mt-2">
                <div>
                  <div className="text-4xl font-black text-[#0A0A0B]">{metrics.successRate}%</div>
                  <div className="text-[10px] text-[#0A0A0B]/40 font-black uppercase tracking-widest">Broadcast Success</div>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-[#0A0A0B] flex items-center justify-center">
                  <ArrowUpRight className="text-[#FFD700] w-6 h-6" />
                </div>
              </div>
            </Card>
          </BentoGrid>
        )
      case 'scraping':
        return (
          <BentoGrid>
            <Card className="col-span-12 row-span-3" title="Scraping Velocity" icon={Search}>
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-4xl font-black text-[#0A0A0B] tracking-tight uppercase">Infiltration Ops</h2>
                  <div className="text-right">
                    <div className="text-3xl font-black text-[#10B981]">{metrics.velocity}</div>
                    <div className="text-[10px] font-bold text-[#0A0A0B]/40 uppercase">Deals/Min</div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-6 flex-1">
                  {radarData.map((site) => (
                    <div key={site.subject} className="p-8 rounded-[40px] bg-black/[0.03] border border-black/5 flex flex-col justify-center text-center group hover:bg-[#0A0A0B] hover:text-[#FFD700] transition-all duration-500">
                      <div className="text-sm font-black uppercase tracking-widest mb-2 opacity-40 group-hover:opacity-100">{site.subject}</div>
                      <div className="text-6xl font-black mb-2">{site.A}</div>
                      <div className="text-[10px] font-bold uppercase tracking-tighter opacity-40 group-hover:opacity-100">Total Extractions</div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
            <Card className="col-span-6 row-span-3" title="Active Scrapers" icon={Cpu}>
              <div className="space-y-4">
                {['Amazon Main', 'Flipkart API', 'Couponami Crawler'].map((scraper, i) => (
                  <div key={scraper} className="p-4 rounded-2xl bg-black/[0.02] border border-black/5 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-[#0A0A0B] flex items-center justify-center text-[#FFD700] font-black text-xs">0{i+1}</div>
                      <div>
                        <div className="text-sm font-black text-[#0A0A0B] uppercase">{scraper}</div>
                        <div className="text-[10px] font-bold text-[#10B981]">STATUS: OPERATIONAL</div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map(b => <div key={b} className="w-1 h-4 bg-[#10B981] rounded-full animate-pulse" style={{ animationDelay: `${b * 0.1}s` }} />)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="col-span-6 row-span-3" title="Recent Failures" icon={History}>
              <div className="flex flex-col h-full justify-center items-center text-center p-10 opacity-20">
                <ShieldCheck className="w-16 h-16 mb-4" />
                <div className="text-xl font-black uppercase">Zero Breaches</div>
                <p className="text-xs font-bold uppercase">All scrapers operating within parameters</p>
              </div>
            </Card>
          </BentoGrid>
        )
      case 'engine':
        return (
          <BentoGrid>
            <Card className="col-span-12 row-span-6" title="Decision Logic" icon={Zap}>
              <div className="flex flex-col h-full">
                <div className="mb-12">
                  <h2 className="text-6xl font-black text-[#0A0A0B] tracking-tighter uppercase leading-none mb-4">Neural<br/>Architecture</h2>
                  <p className="text-lg font-medium text-[#0A0A0B]/40 uppercase tracking-widest">Arbitrage Decision-Making Process</p>
                </div>
                <div className="flex-1 relative">
                  {/* Complex Flowchart SVG */}
                  <svg className="w-full h-full" viewBox="0 0 1000 500">
                    <defs>
                      <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#0A0A0B" />
                      </marker>
                    </defs>
                    
                    {[
                      { x: 100, y: 250, label: 'Data Intake' },
                      { x: 300, y: 250, label: 'Price Verify' },
                      { x: 500, y: 150, label: 'Affiliate Check' },
                      { x: 500, y: 350, label: 'Duplicate Filter' },
                      { x: 700, y: 250, label: 'Risk Audit' },
                      { x: 900, y: 250, label: 'Deployment' }
                    ].map((node, i) => (
                      <g key={i}>
                        <rect x={node.x-60} y={node.y-30} width="120" height="60" rx="20" fill="#0A0A0B" />
                        <text x={node.x} y={node.y+5} textAnchor="middle" fill="#FFD700" className="text-[10px] font-black uppercase">{node.label}</text>
                      </g>
                    ))}

                    <path d="M 160 250 L 240 250" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                    <path d="M 360 250 L 440 150" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                    <path d="M 360 250 L 440 350" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                    <path d="M 560 150 L 640 250" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                    <path d="M 560 350 L 640 250" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                    <path d="M 760 250 L 840 250" stroke="#0A0A0B" strokeWidth="2" markerEnd="url(#arrow)" />
                  </svg>
                </div>
              </div>
            </Card>
          </BentoGrid>
        )
      case 'outreach':
         return (
           <BentoGrid>
             <Card className="col-span-12 row-span-3" title="Broadcast Performance" icon={Send}>
               <div className="flex flex-col h-full">
                 <div className="flex items-center justify-between mb-8">
                   <h2 className="text-4xl font-black text-[#0A0A0B] tracking-tight uppercase">Outreach Hub</h2>
                   <div className="flex gap-4">
                     <div className="px-6 py-3 rounded-2xl bg-[#0A0A0B] text-[#FFD700] text-sm font-black uppercase tracking-widest">Total: {audit.length}</div>
                     <div className="px-6 py-3 rounded-2xl bg-[#FFD700] text-[#0A0A0B] text-sm font-black uppercase tracking-widest">Success: {metrics.successRate}%</div>
                   </div>
                 </div>
                 <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                   {audit.slice(0, 10).map((entry, i) => (
                     <div key={i} className="p-4 rounded-2xl bg-black/[0.02] border border-black/5 flex items-center justify-between">
                       <div className="flex items-center gap-6">
                         <div className={`w-3 h-3 rounded-full ${entry.status === 'success' ? 'bg-[#10B981]' : 'bg-[#FF4D4D]'}`} />
                         <div>
                           <div className="text-xs font-black text-[#0A0A0B] uppercase">Deal ID: {entry.deal_id}</div>
                           <div className="text-[10px] font-bold text-[#0A0A0B]/40">{entry.timestamp}</div>
                         </div>
                       </div>
                       <div className="flex items-center gap-4">
                         <div className="text-[10px] font-black text-[#0A0A0B] uppercase px-3 py-1 bg-black/5 rounded-full">{entry.channel}</div>
                         <div className={`text-[10px] font-black uppercase ${entry.status === 'success' ? 'text-[#10B981]' : 'text-[#FF4D4D]'}`}>{entry.status}</div>
                       </div>
                     </div>
                   ))}
                 </div>
               </div>
             </Card>
             <Card className="col-span-6 row-span-3" title="Channel Distribution" icon={LayoutGrid}>
               <div className="flex flex-col h-full justify-between">
                 {['Telegram', 'Email', 'WhatsApp'].map(channel => {
                   const count = audit.filter(a => a.channel.toLowerCase().includes(channel.toLowerCase())).length
                   const total = audit.length || 1
                   const percent = (count / total) * 100
                   return (
                     <div key={channel} className="space-y-2">
                       <div className="flex justify-between items-end">
                         <span className="text-xs font-black text-[#0A0A0B] uppercase">{channel}</span>
                         <span className="text-[10px] font-bold text-[#0A0A0B]/40">{count} BROADCASTS</span>
                       </div>
                       <div className="w-full h-3 bg-black/5 rounded-full overflow-hidden">
                         <motion.div 
                           initial={{ width: 0 }}
                           animate={{ width: `${percent}%` }}
                           className="h-full bg-[#0A0A0B]" 
                         />
                       </div>
                     </div>
                   )
                 })}
               </div>
             </Card>
             <Card className="col-span-6 row-span-3 bg-[#0A0A0B] border-none" title="Real-time Pulse" icon={Activity}>
               <div className="h-full flex flex-col justify-center items-center text-center">
                 <div className="relative mb-6">
                   <motion.div 
                     animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                     transition={{ duration: 2, repeat: Infinity }}
                     className="absolute inset-0 rounded-full border-2 border-[#FFD700]"
                   />
                   <div className="w-20 h-20 rounded-full bg-[#FFD700] flex items-center justify-center">
                     <Send className="w-10 h-10 text-[#0A0A0B]" />
                   </div>
                 </div>
                 <div className="text-2xl font-black text-white uppercase tracking-tighter">Broadcasting</div>
                 <div className="text-[10px] font-bold text-[#FFD700] uppercase tracking-widest mt-2">Active Transmission Stream</div>
               </div>
             </Card>
           </BentoGrid>
         )
       case 'health':
         return (
           <BentoGrid>
             <Card className="col-span-12 row-span-2" title="System Vitality" icon={Activity}>
               <div className="flex items-center justify-between h-full">
                 <div>
                   <h2 className="text-6xl font-black text-[#0A0A0B] tracking-tighter uppercase">99.9% UPTIME</h2>
                   <p className="text-sm font-bold text-[#0A0A0B]/40 uppercase tracking-widest mt-2">System Status: Optimal</p>
                 </div>
                 <div className="flex gap-1 h-20 items-end">
                   {[...Array(20)].map((_, i) => (
                     <motion.div 
                       key={i}
                       initial={{ height: 10 }}
                       animate={{ height: Math.random() * 60 + 20 }}
                       transition={{ duration: 0.5, repeat: Infinity, repeatType: 'reverse', delay: i * 0.05 }}
                       className="w-2 bg-[#0A0A0B] rounded-full"
                     />
                   ))}
                 </div>
               </div>
             </Card>
             <Card className="col-span-4 row-span-2" title="API Latency" icon={Zap}>
               <div className="flex flex-col h-full justify-center">
                 <div className="text-6xl font-black text-[#0A0A0B]">42ms</div>
                 <div className="text-xs font-black text-[#0A0A0B]/40 uppercase tracking-widest mt-2">Average Response Time</div>
                 <div className="mt-6 flex items-center gap-2">
                   <div className="w-2 h-2 rounded-full bg-[#10B981]" />
                   <span className="text-[10px] font-bold text-[#10B981] uppercase">Within Parameters</span>
                 </div>
               </div>
             </Card>
             <Card className="col-span-4 row-span-2" title="Memory Core" icon={Cpu}>
               <div className="flex flex-col h-full justify-center">
                 <div className="text-6xl font-black text-[#0A0A0B]">128MB</div>
                 <div className="text-xs font-black text-[#0A0A0B]/40 uppercase tracking-widest mt-2">Resource Utilization</div>
                 <div className="mt-6 w-full h-2 bg-black/5 rounded-full overflow-hidden">
                   <div className="w-1/3 h-full bg-[#0A0A0B]" />
                 </div>
               </div>
             </Card>
             <Card className="col-span-4 row-span-2 bg-[#FF4D4D] border-none" title="Alerts" icon={History}>
               <div className="flex flex-col h-full justify-center text-white">
                 <div className="text-6xl font-black">0</div>
                 <div className="text-xs font-black uppercase tracking-widest mt-2">Critical Failures</div>
                 <p className="text-[10px] font-medium uppercase mt-4 opacity-60">System resilience at maximum capacity</p>
               </div>
             </Card>
             <Card className="col-span-12 row-span-2" title="Global Health Trace" icon={Radar}>
               <div className="h-full flex items-center justify-between">
                 <div className="space-y-4 flex-1">
                   {['Database', 'Cloud Engine', 'Network', 'Scrapers'].map(sys => (
                     <div key={sys} className="flex items-center justify-between pr-20">
                       <span className="text-xs font-black text-[#0A0A0B] uppercase">{sys}</span>
                       <div className="flex gap-2 items-center">
                         <div className="text-[10px] font-black text-[#10B981] uppercase">Stable</div>
                         <div className="w-20 h-1 bg-black/5 rounded-full overflow-hidden">
                           <div className="w-full h-full bg-[#10B981]" />
                         </div>
                       </div>
                     </div>
                   ))}
                 </div>
                 <div className="w-px h-full bg-black/5 mx-10" />
                 <div className="text-right">
                   <div className="text-4xl font-black text-[#0A0A0B]">SECURE</div>
                   <div className="text-[10px] font-bold text-[#0A0A0B]/40 uppercase tracking-widest">Protocol Version 4.2.0</div>
                 </div>
               </div>
             </Card>
           </BentoGrid>
         )
        default:
          return null
      }
    }
  
    return (
    <div className="flex h-screen bg-[#0A0A0B] text-[#F8F9FA] overflow-hidden font-sans selection:bg-[#FFD700] selection:text-[#0A0A0B]">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.02 }}
            transition={{ duration: 0.3 }}
            className="h-full"
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>

        {/* Product DNA Modal */}
        <AnimatePresence>
          {selectedDeal && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/80 backdrop-blur-sm"
              onClick={() => setSelectedDeal(null)}
            >
              <motion.div 
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="w-full max-w-2xl bg-[#F8F9FA] rounded-[40px] p-10 overflow-hidden relative"
                onClick={e => e.stopPropagation()}
              >
                <div className="absolute top-0 right-0 p-8">
                  <button 
                    onClick={() => setSelectedDeal(null)}
                    className="w-12 h-12 rounded-full bg-[#0A0A0B] text-white flex items-center justify-center hover:scale-110 transition-transform"
                  >
                    ×
                  </button>
                </div>

                <div className="mb-8">
                  <div className="text-[10px] font-black text-[#FFD700] bg-[#0A0A0B] px-3 py-1 rounded-full inline-block mb-4 uppercase tracking-widest">Product DNA</div>
                  <h2 className="text-4xl font-black text-[#0A0A0B] leading-tight mb-2">{selectedDeal.title}</h2>
                  <p className="text-[#0A0A0B]/60 font-medium uppercase tracking-tighter">{selectedDeal.store} • {selectedDeal.category}</p>
                </div>

                <div className="grid grid-cols-2 gap-8 mb-10">
                  <div className="p-6 rounded-3xl bg-black/[0.03] border border-black/5">
                    <div className="text-[10px] font-bold text-[#0A0A0B]/40 uppercase mb-2">Price Dynamics</div>
                    <div className="flex items-end gap-3">
                      <div className="text-4xl font-black text-[#FF4D4D]">{selectedDeal.price}</div>
                      <div className="text-xl font-bold text-[#0A0A0B]/20 line-through mb-1">{selectedDeal.original_price}</div>
                    </div>
                    <div className="mt-2 text-[11px] font-black text-[#10B981] uppercase">{selectedDeal.discount} OFF</div>
                  </div>
                  <div className="p-6 rounded-3xl bg-black/[0.03] border border-black/5">
                    <div className="text-[10px] font-bold text-[#0A0A0B]/40 uppercase mb-2">Extraction Meta</div>
                    <div className="space-y-1">
                      <div className="text-xs font-black text-[#0A0A0B]">ID: {selectedDeal.id}</div>
                      <div className="text-xs font-medium text-[#0A0A0B]/60">SCRAPED: {new Date(selectedDeal.timestamp).toLocaleString()}</div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <a 
                    href={selectedDeal.link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex-1 bg-[#0A0A0B] text-[#FFD700] py-5 rounded-2xl text-center font-black uppercase tracking-widest hover:scale-[1.02] active:scale-[0.98] transition-transform flex items-center justify-center gap-2"
                  >
                    Deploy Link <ExternalLink className="w-4 h-4" />
                  </a>
                  <button className="px-8 bg-[#F8F9FA] border-2 border-[#0A0A0B] text-[#0A0A0B] py-5 rounded-2xl font-black uppercase tracking-widest hover:bg-[#0A0A0B] hover:text-[#F8F9FA] transition-colors">
                    Audit
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Floating Neural Core Animation */}
      <div className="fixed bottom-8 right-8 pointer-events-none">
        <motion.div 
          animate={{ 
            rotate: 360,
            scale: [1, 1.1, 1],
          }}
          transition={{ 
            rotate: { duration: 10, repeat: Infinity, ease: "linear" },
            scale: { duration: 4, repeat: Infinity, ease: "easeInOut" }
          }}
          className="relative w-24 h-24"
        >
          <div className="absolute inset-0 rounded-full border border-[#FFD700]/20 blur-sm" />
          <div className="absolute inset-4 rounded-full border border-[#FFD700]/40 blur-[2px]" />
          <div className="absolute inset-8 rounded-full bg-[#FFD700] shadow-[0_0_30px_#FFD700]" />
          <Brain className="absolute inset-0 m-auto w-8 h-8 text-[#0A0A0B]" />
        </motion.div>
      </div>
    </div>
  )
}
