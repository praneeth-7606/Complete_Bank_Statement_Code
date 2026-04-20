import { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  TrendingUp, TrendingDown, Wallet, FileText, ArrowUpRight,
  DollarSign, Activity, Upload as UploadIcon, MessageSquare,
  BarChart3, Loader2, Sparkles, Zap, Calendar, ChevronRight, RefreshCw
} from 'lucide-react'
import { motion, AnimatePresence, animate } from 'framer-motion'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'
import { Card, Button, Badge, Skeleton, EmptyState } from '../components/ui'

// ─── Animated counter ─────────────────────────────────────────────────────────
const AnimatedCount = memo(({ value, prefix = '', decimals = 0 }) => {
  const ref = useRef(null)
  const prevRef = useRef(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const from = prevRef.current
    prevRef.current = value
    const ctrl = animate(from, value, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: v => {
        el.textContent = prefix + v.toLocaleString('en-IN', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals
        })
      }
    })
    return () => ctrl.stop()
  }, [value, prefix, decimals])
  return <span ref={ref}>{prefix}0</span>
})
AnimatedCount.displayName = 'AnimatedCount'

// ─── Mini sparkline tooltip (invisible, just for recharts requirement) ─────
const InvisibleTooltip = () => null

// ─── Stat Card ────────────────────────────────────────────────────────────────
const StatCard = memo(({ title, value, icon: Icon, accent, prefix = '₹', decimals = 2, trend, trendUp, sparkData, delay, onClick }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      onClick={onClick}
      className="relative overflow-hidden rounded-2xl p-5 cursor-pointer group"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      {/* Hover accent glow */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl pointer-events-none"
        style={{ background: `radial-gradient(circle at 30% 30%, ${accent}22 0%, transparent 70%)` }} />

      <div className="flex items-start justify-between mb-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: `${accent}22`, border: `1px solid ${accent}33` }}>
          <Icon className="w-4 h-4" style={{ color: accent }} />
        </div>
        {trend && (
          <div className={`flex items-center gap-0.5 text-xs font-bold px-2 py-1 rounded-full ${trendUp ? 'bg-emerald-400/10 text-emerald-400' : 'bg-rose-400/10 text-rose-400'}`}>
            {trendUp ? <ArrowUpRight className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trend}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500 mb-1 font-medium tracking-wide">{title}</p>
      <p className="text-2xl font-black tracking-tight" style={{ color: accent }}>
        <AnimatedCount value={value} prefix={prefix} decimals={decimals} />
      </p>

      {/* Sparkline */}
      {sparkData?.length > 0 && (
        <div className="mt-3 -mx-1">
          <ResponsiveContainer width="100%" height={40}>
            <AreaChart data={sparkData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
              <defs>
                <linearGradient id={`sg-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={accent} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke={accent} strokeWidth={1.5}
                fill={`url(#sg-${title})`} dot={false} />
              <Tooltip content={<InvisibleTooltip />} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  )
})
StatCard.displayName = 'StatCard'

// ─── Transaction Row ──────────────────────────────────────────────────────────
const TxnRow = memo(({ txn, index }) => {
  const isCredit = txn.type === 'credit'
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
      className="flex items-center justify-between py-3 group"
      style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: isCredit ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }}>
          {isCredit
            ? <TrendingUp className="w-4 h-4 text-emerald-400" />
            : <TrendingDown className="w-4 h-4 text-rose-400" />}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-200 truncate">{txn.description}</p>
          <p className="text-xs text-gray-600 flex items-center gap-1">
            <Calendar className="w-3 h-3" />{txn.date}
          </p>
        </div>
      </div>
      <span className={`text-sm font-bold flex-shrink-0 ml-3 ${isCredit ? 'text-emerald-400' : 'text-rose-400'}`}>
        {isCredit ? '+' : '-'}₹{txn.amount.toLocaleString('en-IN')}
      </span>
    </motion.div>
  )
})
TxnRow.displayName = 'TxnRow'

// ─── Quick Action Button ──────────────────────────────────────────────────────
const QuickAction = memo(({ to, icon: Icon, title, desc, gradient, delay }) => (
  <Link to={to}>
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      whileHover={{ x: 4, transition: { duration: 0.15 } }}
      whileTap={{ scale: 0.98 }}
      className="flex items-center gap-3 p-3.5 rounded-xl transition-colors cursor-pointer"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: gradient }}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-200">{title}</p>
        <p className="text-xs text-gray-600">{desc}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-gray-600" />
    </motion.div>
  </Link>
))
QuickAction.displayName = 'QuickAction'

// ─── MAIN DASHBOARD ──────────────────────────────────────────────────────────
const Dashboard = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    total_transactions: 0, total_income: 0, total_expenses: 0,
    balance: 0, average_transaction: 0
  })
  const [recentTransactions, setRecentTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async (isRefresh = false) => {
    try {
      isRefresh ? setRefreshing(true) : setLoading(true)
      setError(null)

      const [statsRes, txnRes] = await Promise.all([
        api.get('/api/dashboard/stats'),
        api.get('/api/transactions/filtered', { params: { page: 1, limit: 8 } })
      ])

      if (statsRes.data.status === 'success') setStats(statsRes.data.data)
      if (txnRes.data.status === 'success') setRecentTransactions(txnRes.data.data.transactions)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard')
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // Build mini spark data (mock wave if no time-series available)
  const mockSpark = useCallback((base, len = 8) =>
    Array.from({ length: len }, (_, i) => ({ v: base * (0.7 + 0.4 * Math.sin(i * 0.8) + 0.1 * Math.random()) }))
    , [])

  const balanceSpark = useMemo(() => mockSpark(stats.balance), [stats.balance, mockSpark])
  const incomeSpark = useMemo(() => mockSpark(stats.total_income), [stats.total_income, mockSpark])
  const expenseSpark = useMemo(() => mockSpark(stats.total_expenses), [stats.total_expenses, mockSpark])

  const mappedTransactions = useMemo(() =>
    recentTransactions.map(t => ({
      description: t.description || 'N/A',
      date: t.date || 'N/A',
      amount: parseFloat(t.credit || t.debit || 0),
      type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
      category: t.category || 'Uncategorized'
    }))
    , [recentTransactions])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            className="w-14 h-14 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 mx-auto mb-4"
          />
          <p className="text-gray-500 text-sm">Loading dashboard…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <p className="text-rose-400 mb-4">{error}</p>
          <button onClick={() => fetchData()} className="px-5 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* ── HERO BANNER ── */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl p-7"
        style={{ background: 'linear-gradient(135deg,#0d0d2b 0%,#1b0839 55%,#0a1f3d 100%)', border: '1px solid rgba(99,102,241,0.18)' }}
      >
        {/* Glow orbs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-3xl">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)' }} />
          <div className="absolute -bottom-16 -left-16 w-48 h-48 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)' }} />
        </div>

        <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-bold tracking-widest text-indigo-400 uppercase">FinanceAI</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-white via-indigo-200 to-purple-300 bg-clip-text text-transparent mb-1">
              Welcome back
            </h1>
            <p className="text-gray-400 text-sm">Here's your financial overview for today</p>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-emerald-400">Live</span>
            </div>
            <motion.button
              onClick={() => fetchData(true)}
              disabled={refreshing}
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold text-gray-300 transition-all"
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.09)' }}
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Sync
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* ── STAT CARDS ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Net Balance" value={stats.balance} icon={Wallet} accent="#6366f1"
          trend="+12.5%" trendUp delay={0} sparkData={balanceSpark}
          onClick={() => navigate('/transactions')} />
        <StatCard title="Total Income" value={stats.total_income} icon={TrendingUp} accent="#10b981"
          trend="+8.2%" trendUp delay={0.07} sparkData={incomeSpark}
          onClick={() => navigate('/transactions?filter=income')} />
        <StatCard title="Total Expenses" value={stats.total_expenses} icon={TrendingDown} accent="#ef4444"
          trend="-3.1%" trendUp={false} delay={0.14} sparkData={expenseSpark}
          onClick={() => navigate('/transactions?filter=expense')} />
        <StatCard title="Transactions" value={stats.total_transactions} icon={FileText} accent="#f59e0b"
          prefix="" decimals={0} trend="+15" trendUp delay={0.21}
          onClick={() => navigate('/transactions')} />
      </div>

      {/* ── LOWER GRID ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-2xl p-5"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-white">Quick Actions</h3>
          </div>
          <div className="space-y-2">
            <QuickAction to="/upload" icon={UploadIcon} title="Upload Statement"
              desc="Process a bank PDF" gradient="linear-gradient(135deg,#6366f1,#8b5cf6)" delay={0.45} />
            <QuickAction to="/chat" icon={MessageSquare} title="Ask AI Assistant"
              desc="Query your finances" gradient="linear-gradient(135deg,#10b981,#059669)" delay={0.5} />
            <QuickAction to="/analytics" icon={BarChart3} title="View Analytics"
              desc="Insights & trends" gradient="linear-gradient(135deg,#f59e0b,#d97706)" delay={0.55} />
          </div>

          {/* Balance summary */}
          <div className="mt-5 p-4 rounded-xl" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)' }}>
            <p className="text-xs text-gray-500 mb-1">Savings Rate</p>
            <div className="flex items-end gap-2">
              <span className="text-xl font-black text-indigo-300">
                {stats.total_income > 0 ? ((stats.balance / stats.total_income) * 100).toFixed(1) : '0.0'}%
              </span>
              <span className="text-xs text-gray-600 mb-0.5">of income saved</span>
            </div>
            <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, stats.total_income > 0 ? (stats.balance / stats.total_income) * 100 : 0)}%` }}
                transition={{ delay: 0.8, duration: 1, ease: [0.16, 1, 0.3, 1] }}
                className="h-full rounded-full"
                style={{ background: 'linear-gradient(90deg,#6366f1,#8b5cf6)' }}
              />
            </div>
          </div>
        </motion.div>

        {/* Recent Transactions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2 rounded-2xl p-5"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white">Recent Transactions</h3>
            </div>
            <Link to="/transactions">
              <motion.span whileHover={{ x: 2 }} className="flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors">
                View all <ChevronRight className="w-3.5 h-3.5" />
              </motion.span>
            </Link>
          </div>

          {mappedTransactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
                <DollarSign className="w-7 h-7 text-indigo-400" />
              </div>
              <p className="text-gray-500 text-sm mb-4">No transactions yet</p>
              <Link to="/upload">
                <button className="px-5 py-2 rounded-xl text-sm font-semibold text-white"
                  style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)' }}>
                  Upload Statement
                </button>
              </Link>
            </div>
          ) : (
            <div>
              {mappedTransactions.slice(0, 7).map((txn, i) => (
                <TxnRow key={i} txn={txn} index={i} />
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default Dashboard