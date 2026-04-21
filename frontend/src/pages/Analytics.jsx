import { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, AreaChart, Area, LineChart, Line
} from 'recharts'
import {
  TrendingUp, TrendingDown, DollarSign, Calendar, Sparkles,
  RefreshCw, ArrowUpRight, ArrowDownRight, Brain, Zap, Target,
  ChevronDown, BarChart3, Activity
} from 'lucide-react'
import { motion, AnimatePresence, useSpring, useMotionValue, animate } from 'framer-motion'
import api from '../services/api'
import toast from 'react-hot-toast'
import { Card, Button, Badge, Skeleton, EmptyState } from '../components/ui'

// ─── Animated Counter ────────────────────────────────────────────────────────
const AnimatedNumber = memo(({ value, prefix = '', suffix = '', decimals = 0 }) => {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ctrl = animate(0, value, {
      duration: 1.4,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: v => {
        el.textContent = prefix + v.toLocaleString('en-IN', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals
        }) + suffix
      }
    })
    return () => ctrl.stop()
  }, [value, prefix, suffix, decimals])
  return <span ref={ref}>{prefix}0{suffix}</span>
})
AnimatedNumber.displayName = 'AnimatedNumber'

// ─── Custom Tooltip ───────────────────────────────────────────────────────────
const SlickTooltip = memo(({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl px-4 py-3 shadow-2xl backdrop-blur-xl">
      {label && <p className="text-xs text-[var(--text-secondary)] mb-1.5 font-medium tracking-wide uppercase">{label}</p>}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-xs text-[var(--text-secondary)] capitalize">{p.name}:</span>
          <span className="text-sm font-bold text-[var(--text-primary)]">₹{Number(p.value).toLocaleString('en-IN')}</span>
        </div>
      ))}
    </div>
  )
})
SlickTooltip.displayName = 'SlickTooltip'

// ─── Pie Custom Label ─────────────────────────────────────────────────────────
const renderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null
  const RADIAN = Math.PI / 180
  const r = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
      fontSize={11} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
const StatCard = memo(({ title, value, icon: Icon, gradient, textColor, prefix = '₹', decimals = 0, trend, trendUp, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 24 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    className="relative overflow-hidden rounded-2xl p-5 group cursor-default bg-[var(--bg-card)] border border-[var(--border-subtle)]"
    whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
  >
    <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl`}
      style={{ background: gradient, opacity: 0.06 }} />
    <div className="flex items-start justify-between mb-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center`} style={{ background: gradient }}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      {trend && (
        <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${trendUp ? 'text-emerald-400 bg-emerald-400/10' : 'text-rose-400 bg-rose-400/10'}`}>
          {trendUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {trend}
        </div>
      )}
    </div>
    <p className="text-xs text-[var(--text-secondary)] font-medium tracking-wide uppercase mb-1">{title}</p>
    <p className={`text-2xl font-bold ${textColor}`}>
      <AnimatedNumber value={value} prefix={prefix} decimals={decimals} />
    </p>
  </motion.div>
))
StatCard.displayName = 'StatCard'

// ─── Insight Card ─────────────────────────────────────────────────────────────
const InsightCard = memo(({ insight, index }) => {
  const isPositive = insight.includes('✅') || insight.includes('Great') || insight.toLowerCase().includes('saving')
  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className={`flex items-start gap-3 p-4 rounded-xl border ${isPositive ? 'bg-emerald-50 border-emerald-200' : 'bg-primary-50 border-primary-200'}`}
    >
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${isPositive ? 'bg-emerald-100' : 'bg-primary-100'}`}>
        {isPositive ? <TrendingUp className="w-4 h-4 text-emerald-600" /> : <Brain className="w-4 h-4 text-primary-600" />}
      </div>
      <p className="text-sm text-neutral-700 leading-relaxed font-medium">{insight.replace('✅ ', '').replace('⚠️ ', '')}</p>
    </motion.div>
  )
})
InsightCard.displayName = 'InsightCard'

// ─── Period Toggle ────────────────────────────────────────────────────────────
const PeriodToggle = memo(({ value, onChange }) => {
  const periods = ['daily', 'weekly', 'monthly']
  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-neutral-100 border border-neutral-200">
      {periods.map(p => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all duration-200 ${value === p ? 'text-white shadow-lg bg-gradient-to-r from-primary-600 to-primary-700' : 'text-neutral-600 hover:text-neutral-900 hover:bg-white'}`}
        >
          {p}
        </button>
      ))}
    </div>
  )
})
PeriodToggle.displayName = 'PeriodToggle'

// ─── Category Table Row ───────────────────────────────────────────────────────
const CategoryRow = memo(({ category, index, total, color }) => {
  const pct = total > 0 ? ((category.value / total) * 100).toFixed(1) : 0
  return (
    <motion.tr
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="group border-b border-neutral-200 hover:bg-neutral-50 transition-colors"
    >
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
          <span className="text-sm font-medium text-neutral-900">{category.name}</span>
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1.5 rounded-full bg-neutral-200 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ delay: index * 0.04 + 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full"
              style={{ background: color }}
            />
          </div>
          <span className="text-xs text-neutral-600 w-10 text-right font-medium">{pct}%</span>
        </div>
      </td>
      <td className="py-3 px-4 text-right">
        <span className="text-sm font-bold text-neutral-900">₹{(category.value || 0).toLocaleString('en-IN')}</span>
      </td>
    </motion.tr>
  )
})
CategoryRow.displayName = 'CategoryRow'

// ─── CHART COLORS ─────────────────────────────────────────────────────────────
const PALETTE = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#f97316', '#84cc16']

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────
const Analytics = () => {
  const [analyticsData, setAnalyticsData] = useState({ categoryData: [], monthlyData: [], insights: [], summary: {} })
  const [period, setPeriod] = useState('monthly')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const fetchAnalyticsData = useCallback(async (isRefresh = false) => {
    try {
      isRefresh ? setRefreshing(true) : setLoading(true)
      setError(null)

      const [categoryResponse, statsResponse] = await Promise.all([
        api.get('/api/analytics/by-category'),
        api.get('/api/dashboard/stats')
      ])

      if (categoryResponse.data.status === 'success' && statsResponse.data.status === 'success') {
        const topCategory = categoryResponse.data.data.categories[0]
        const balance = statsResponse.data.data.balance
        const totalIncome = statsResponse.data.data.total_income
        const savingsPercentage = totalIncome > 0 ? ((balance / totalIncome) * 100).toFixed(1) : 0
        const aiInsights = statsResponse.data.data.ai_insights
        const insights = (aiInsights?.length > 0) ? aiInsights : [
          topCategory ? `Highest spend: ${topCategory.name} at ₹${topCategory.total.toLocaleString('en-IN')}` : 'No spending data available',
          `Net savings: ₹${balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${savingsPercentage}% of income)`,
          `${statsResponse.data.data.total_transactions} transactions recorded`,
          totalIncome > statsResponse.data.data.total_expenses ? '✅ Income exceeds expenses — great financial health!' : '⚠️ Expenses exceed income — consider reviewing your budget'
        ]
        setAnalyticsData(prev => ({
          ...prev,
          categoryData: categoryResponse.data.data.categories.map(c => ({ ...c, value: c.total })),
          insights,
          summary: {
            balance: statsResponse.data.data.balance,
            totalIncome: statsResponse.data.data.total_income,
            totalExpenses: statsResponse.data.data.total_expenses,
            totalTransactions: statsResponse.data.data.total_transactions
          }
        }))
      }
    } catch (err) {
      setError(err.message || 'Failed to load analytics')
      toast.error('Failed to load analytics data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  const fetchDateAnalytics = useCallback(async () => {
    try {
      const res = await api.get('/api/analytics/by-date', { params: { period } })
      if (res.data.status === 'success') {
        setAnalyticsData(prev => ({ ...prev, monthlyData: res.data.data.periods }))
      }
    } catch { }
  }, [period])

  useEffect(() => { fetchAnalyticsData() }, [fetchAnalyticsData])
  useEffect(() => { fetchDateAnalytics() }, [fetchDateAnalytics])

  const totalCategorySpend = useMemo(
    () => analyticsData.categoryData.reduce((s, c) => s + c.value, 0),
    [analyticsData.categoryData]
  )

  const savingsRate = useMemo(() => {
    if (!analyticsData.summary.totalIncome) return 0
    return ((analyticsData.summary.balance / analyticsData.summary.totalIncome) * 100).toFixed(1)
  }, [analyticsData.summary])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            className="w-16 h-16 rounded-full border-2 border-primary-200 border-t-primary-600 mx-auto mb-6"
          />
          <p className="text-neutral-600 text-sm font-medium tracking-wide">Loading analytics…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 rounded-2xl bg-rose-100 border border-rose-200 flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="w-8 h-8 text-rose-600" />
          </div>
          <h3 className="text-lg font-bold text-neutral-900 mb-2">Couldn't load data</h3>
          <p className="text-neutral-600 text-sm mb-6 font-medium">{error}</p>
          <button onClick={() => fetchAnalyticsData()} className="px-6 py-2.5 rounded-xl font-semibold text-white text-sm bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 transition-all shadow-lg">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── HERO HEADER ── */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl p-8 bg-gradient-to-r from-primary-700 via-primary-800 to-primary-900 border border-primary-600/30 shadow-xl"
      >
        {/* Orbs */}
        <div className="absolute top-0 right-0 w-80 h-80 rounded-full pointer-events-none opacity-20" style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%)', transform: 'translate(30%, -30%)' }} />
        <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full pointer-events-none opacity-20" style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%)', transform: 'translate(-30%, 30%)' }} />

        <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white/20">
                <BarChart3 className="w-4 h-4 text-white" />
              </div>
              <span className="text-xs font-semibold tracking-widest text-white/80 uppercase">Intelligence Suite</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black mb-2 text-white">
              Financial Analytics
            </h1>
            <p className="text-white/80 text-sm">Real-time insights powered by AI analysis</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success-500/20 border border-success-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-success-400 animate-pulse" />
              <span className="text-xs font-semibold text-success-400">Live</span>
            </div>
            <motion.button
              onClick={() => fetchAnalyticsData(true)}
              disabled={refreshing}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all bg-white/10 border border-white/20 hover:bg-white/20"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </motion.button>
          </div>
        </div>

        {/* Quick savings badge */}
        <div className="relative mt-6 flex flex-wrap gap-3">
          {[
            { label: 'Savings Rate', value: `${savingsRate}%`, color: '#10b981' },
            { label: 'Categories', value: analyticsData.categoryData.length, color: '#ffffff' },
            { label: 'Transactions', value: analyticsData.summary.totalTransactions || 0, color: '#ffffff' }
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10">
              <span className="text-xs text-white/70">{item.label}</span>
              <span className="text-sm font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── STAT CARDS ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Net Balance" value={analyticsData.summary.balance || 0} icon={Zap}
          gradient="linear-gradient(135deg,#6366f1,#8b5cf6)" textColor="text-indigo-300" decimals={2} delay={0} trend="+12%" trendUp />
        <StatCard title="Total Income" value={analyticsData.summary.totalIncome || 0} icon={TrendingUp}
          gradient="linear-gradient(135deg,#10b981,#059669)" textColor="text-emerald-300" decimals={2} delay={0.07} trend="+8%" trendUp />
        <StatCard title="Total Expenses" value={analyticsData.summary.totalExpenses || 0} icon={TrendingDown}
          gradient="linear-gradient(135deg,#ef4444,#dc2626)" textColor="text-rose-300" decimals={2} delay={0.14} trend="-3%" trendUp={false} />
        <StatCard title="Transactions" value={analyticsData.summary.totalTransactions || 0} icon={Activity}
          gradient="linear-gradient(135deg,#f59e0b,#d97706)" textColor="text-amber-300" prefix="" delay={0.21} trend="+15" trendUp />
      </div>

      {/* ── CHARTS GRID ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Donut chart – category */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 rounded-2xl p-6 bg-white/80 backdrop-blur-sm border border-neutral-200 shadow-lg"
        >
          <h3 className="text-base font-bold text-neutral-900 mb-1">Spending by Category</h3>
          <p className="text-xs text-neutral-600 mb-4 font-medium">Distribution across all categories</p>
          {analyticsData.categoryData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={analyticsData.categoryData} cx="50%" cy="50%"
                    innerRadius={60} outerRadius={90} paddingAngle={3}
                    dataKey="value" labelLine={false} label={renderPieLabel}>
                    {analyticsData.categoryData.map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip content={<SlickTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-3 space-y-2">
                {analyticsData.categoryData.slice(0, 4).map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                      <span className="text-neutral-700 truncate max-w-[120px] font-medium">{c.name}</span>
                    </div>
                    <span className="text-neutral-900 font-semibold">₹{(c.value || 0).toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-neutral-600 text-sm font-medium">No category data</div>
          )}
        </motion.div>

        {/* Area / Bar chart – income vs expenses */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-3 rounded-2xl p-6 bg-white/80 backdrop-blur-sm border border-neutral-200 shadow-lg"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-neutral-900 mb-0.5">Income vs Expenses</h3>
              <p className="text-xs text-neutral-600 font-medium">Compare cash flow over time</p>
            </div>
            <PeriodToggle value={period} onChange={setPeriod} />
          </div>
          {analyticsData.monthlyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={analyticsData.monthlyData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gIncome" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gExpenses" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<SlickTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: '#6b7280' }} />
                <Area type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} fill="url(#gIncome)" name="Income" dot={false} />
                <Area type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={2} fill="url(#gExpenses)" name="Expenses" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[240px] flex items-center justify-center text-neutral-600 text-sm font-medium">No timeline data yet</div>
          )}
        </motion.div>
      </div>

      {/* ── SPENDING TREND ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="rounded-2xl p-6 bg-white/80 backdrop-blur-sm border border-neutral-200 shadow-lg"
      >
        <div className="flex items-center gap-3 mb-4">
          <Activity className="w-5 h-5 text-primary-600" />
          <div>
            <h3 className="text-base font-bold text-neutral-900">Spending Trend</h3>
            <p className="text-xs text-neutral-600 font-medium">Cumulative expense pattern over time</p>
          </div>
        </div>
        {analyticsData.monthlyData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={analyticsData.monthlyData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
              <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<SlickTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#6b7280' }} />
              <Line type="monotone" dataKey="expenses" stroke="#f59e0b" strokeWidth={2.5} dot={false} name="Expenses" />
              <Line type="monotone" dataKey="income" stroke="#6366f1" strokeWidth={2.5} dot={false} name="Income" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[200px] flex items-center justify-center text-neutral-600 text-sm font-medium">No data available</div>
        )}
      </motion.div>

      {/* ── BOTTOM SPLIT: AI Insights + Category Table ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* AI Insights */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="rounded-2xl p-6 bg-white/80 backdrop-blur-sm border border-neutral-200 shadow-lg"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-gradient-to-br from-primary-600 to-primary-700">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-base font-bold text-neutral-900">AI Insights</h3>
              <p className="text-xs text-neutral-600 font-medium">Powered by your financial data</p>
            </div>
          </div>
          <div className="space-y-3">
            {analyticsData.insights.length > 0
              ? analyticsData.insights.map((insight, i) => <InsightCard key={i} insight={insight} index={i} />)
              : <p className="text-neutral-600 text-sm text-center py-8 font-medium">No insights yet — upload statements to get started</p>
            }
          </div>
        </motion.div>

        {/* Category breakdown table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="rounded-2xl overflow-hidden bg-white/80 backdrop-blur-sm border border-neutral-200 shadow-lg"
        >
          <div className="p-6 pb-4">
            <h3 className="text-base font-bold text-neutral-900 mb-0.5">Category Breakdown</h3>
            <p className="text-xs text-neutral-600 font-medium">Detailed spending by category</p>
          </div>
          {analyticsData.categoryData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-2 px-4 text-xs font-semibold text-neutral-600 uppercase tracking-wide">Category</th>
                    <th className="text-left py-2 px-4 text-xs font-semibold text-neutral-600 uppercase tracking-wide">Share</th>
                    <th className="text-right py-2 px-4 text-xs font-semibold text-neutral-600 uppercase tracking-wide">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {analyticsData.categoryData.map((cat, i) => (
                    <CategoryRow key={i} category={cat} index={i} total={totalCategorySpend} color={PALETTE[i % PALETTE.length]} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-neutral-600 text-sm px-6 font-medium">
              No category data available. Upload a statement to see your breakdown.
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default Analytics