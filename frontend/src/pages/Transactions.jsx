import { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react'
import { Download, Loader2, X, Search, SlidersHorizontal, TrendingUp, TrendingDown, ChevronLeft, ChevronRight, Filter, ArrowUpDown, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import api, { transactionsAPI } from '../services/api'
import toast from 'react-hot-toast'
import { Button, Badge, Skeleton, EmptyState, Card } from '../components/ui'

// ─── Category badge color map ─────────────────────────────────────────────────
const CATEGORY_COLORS = {
  'Food & Dining': '#f59e0b',
  'Shopping': '#8b5cf6',
  'Transportation': '#06b6d4',
  'Entertainment': '#ec4899',
  'Healthcare': '#10b981',
  'Utilities': '#6366f1',
  'Education': '#3b82f6',
  'Travel': '#f97316',
  'Groceries': '#84cc16',
  'Other': '#6b7280'
}
const getCategoryColor = cat => CATEGORY_COLORS[cat] || '#6b7280'

// ─── Category Pill ────────────────────────────────────────────────────────────
const CategoryPill = memo(({ category }) => {
  const variantMap = {
    'Food & Dining': 'warning',
    'Shopping': 'ai',
    'Transportation': 'primary',
    'Entertainment': 'danger',
    'Healthcare': 'success',
    'Utilities': 'primary',
    'Education': 'primary',
    'Travel': 'warning',
    'Groceries': 'success',
    'Other': 'default'
  }
  return <Badge variant={variantMap[category] || 'default'} size="sm">{category}</Badge>
})
CategoryPill.displayName = 'CategoryPill'

// ─── Transaction Row ──────────────────────────────────────────────────────────
const TransactionRow = memo(({ txn, index, onUpdateCategory }) => {
  const isCredit = txn.credit > 0
  const amount = isCredit ? parseFloat(txn.credit) : parseFloat(txn.debit)
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleUpdate = async (newCat) => {
    if (newCat === txn.category) {
      setIsEditing(false)
      return
    }
    setLoading(true)
    try {
      await onUpdateCategory(txn.id, newCat)
      setIsEditing(false)
    } catch (err) {
      // Error handled in parent
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.tr
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.025, duration: 0.3 }}
      className="group border-b hover:bg-white/30 transition-colors"
      style={{ borderColor: 'rgba(0,0,0,0.05)' }}
    >
      {/* Type icon */}
      <td className="py-3.5 pl-4 pr-2 w-10">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center"
          style={{ background: isCredit ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }}>
          {isCredit
            ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            : <TrendingDown className="w-3.5 h-3.5 text-rose-400" />}
        </div>
      </td>

      {/* Date */}
      <td className="py-3.5 px-3 whitespace-nowrap">
        <span className="text-sm text-neutral-900 font-semibold">{txn.date || '—'}</span>
      </td>

      {/* Description */}
      <td className="py-3.5 px-3 max-w-[180px] sm:max-w-xs">
        <p className="text-sm font-semibold text-neutral-900 truncate">{txn.description}</p>
        {txn.reference && <p className="text-xs text-neutral-500 truncate">{txn.reference}</p>}
      </td>

      {/* Category */}
      <td className="py-3.5 px-3 hidden sm:table-cell">
        {isEditing ? (
          <div className="flex items-center gap-2">
            <select
              autoFocus
              disabled={loading}
              value={txn.category || 'Other'}
              onChange={(e) => handleUpdate(e.target.value)}
              onBlur={() => !loading && setIsEditing(false)}
              className="bg-[var(--bg-surface)] text-xs border border-[var(--border-subtle)] rounded-lg px-2 py-1 outline-none text-[var(--text-primary)]"
            >
              {CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            {loading && <Loader2 className="w-3 h-3 animate-spin text-gray-400" />}
          </div>
        ) : (
          <div className="cursor-pointer hover:opacity-80 transition-opacity" onClick={() => setIsEditing(true)}>
            <CategoryPill category={txn.category || 'Other'} />
          </div>
        )}
      </td>

      {/* Amount */}
      <td className="py-3.5 pl-3 pr-4 text-right whitespace-nowrap">
        <span className={`text-sm font-bold ${isCredit ? 'text-emerald-400' : 'text-rose-400'}`}>
          {isCredit ? '+' : '-'}₹{amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </span>
      </td>
    </motion.tr>
  )
})
TransactionRow.displayName = 'TransactionRow'

// ─── Active Filter Chip ───────────────────────────────────────────────────────
const FilterChip = memo(({ label, onRemove, color = '#6366f1' }) => (
  <motion.div
    initial={{ scale: 0.85, opacity: 0 }}
    animate={{ scale: 1, opacity: 1 }}
    exit={{ scale: 0.85, opacity: 0 }}
    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
    style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
  >
    {label}
    <button onClick={onRemove} className="hover:opacity-70 transition-opacity ml-0.5">
      <X className="w-3 h-3" />
    </button>
  </motion.div>
))
FilterChip.displayName = 'FilterChip'

// ─── MAIN COMPONENT ──────────────────────────────────────────────────────────
const CATEGORIES = ['Food & Dining', 'Transportation', 'Shopping', 'Entertainment', 'Bills & Utilities', 'Healthcare', 'Education', 'Travel', 'Investment', 'Dividend', 'Salary', 'Transfer', 'Personal Transfer', 'Other Transfers', 'Other']

const Transactions = () => {
  const [filters, setFilters] = useState({ categories: [], type: 'all', search: '' })
  const [pagination, setPagination] = useState({ page: 1, limit: 20, total: 0, totalPages: 0 })
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showFilterPanel, setShowFilterPanel] = useState(false)
  const searchRef = useRef(null)
  const searchDebounce = useRef(null)

  // ── Fetch ──
  const fetchTransactions = useCallback(async (pageNum = 1, currentFilters = filters) => {
    try {
      setLoading(true)
      setError(null)
      const params = { page: pageNum, limit: pagination.limit }
      if (currentFilters.categories.length > 0) params.categories = currentFilters.categories.join(',')
      if (currentFilters.type !== 'all') params.type = currentFilters.type
      if (currentFilters.search.trim()) params.search = currentFilters.search.trim()

      const response = await api.get('/api/transactions/filtered', { params })
      if (response.data.status === 'success') {
        setTransactions(response.data.data.transactions)
        setPagination(prev => ({
          ...prev,
          page: response.data.data.page,
          total: response.data.data.total,
          totalPages: response.data.data.total_pages
        }))
      }
    } catch (err) {
      setError(err.message || 'Failed to load transactions')
      toast.error('Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.limit])

  useEffect(() => { fetchTransactions(1) }, [])

  // Debounced search
  const handleSearchChange = useCallback((val) => {
    clearTimeout(searchDebounce.current)
    setFilters(prev => ({ ...prev, search: val }))
    searchDebounce.current = setTimeout(() => {
      setFilters(prev => {
        const next = { ...prev, search: val }
        fetchTransactions(1, next)
        return next
      })
    }, 400)
  }, [fetchTransactions])

  const handleTypeChange = useCallback((type) => {
    setFilters(prev => {
      const next = { ...prev, type }
      fetchTransactions(1, next)
      return next
    })
  }, [fetchTransactions])

  const toggleCategory = useCallback((cat) => {
    setFilters(prev => {
      const cats = prev.categories.includes(cat)
        ? prev.categories.filter(c => c !== cat)
        : [...prev.categories, cat]
      const next = { ...prev, categories: cats }
      fetchTransactions(1, next)
      return next
    })
  }, [fetchTransactions])

  const clearAll = useCallback(() => {
    const next = { categories: [], type: 'all', search: '' }
    setFilters(next)
    if (searchRef.current) searchRef.current.value = ''
    fetchTransactions(1, next)
  }, [fetchTransactions])

  const handlePage = useCallback((p) => {
    fetchTransactions(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [fetchTransactions])

  const handleCategoryUpdate = useCallback(async (txnId, newCategory) => {
    try {
      await transactionsAPI.updateCategory(txnId, newCategory)
      setTransactions(prev => prev.map(t =>
        t.id === txnId ? { ...t, category: newCategory } : t
      ))
      toast.success('Category updated successfully')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update category')
      throw err
    }
  }, [])

  const handleExport = useCallback(() => {
    if (!transactions.length) return
    const csv = [
      ['Date', 'Description', 'Category', 'Type', 'Amount'],
      ...transactions.map(t => [
        t.date, t.description, t.category || 'N/A',
        t.credit > 0 ? 'income' : 'expense',
        t.credit > 0 ? t.credit : t.debit
      ])
    ].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV exported!')
  }, [transactions])

  const hasFilters = useMemo(
    () => filters.categories.length > 0 || filters.type !== 'all' || filters.search,
    [filters]
  )

  const totalIncome = useMemo(() => transactions.reduce((s, t) => s + (parseFloat(t.credit) || 0), 0), [transactions])
  const totalExpenses = useMemo(() => transactions.reduce((s, t) => s + (parseFloat(t.debit) || 0), 0), [transactions])

  return (
    <div className="space-y-5 relative">
      {/* Subtle gradient background */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-br from-neutral-50 via-blue-50/30 to-neutral-50"></div>
        <div className="absolute top-20 right-20 w-96 h-96 bg-primary-200/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-200/15 rounded-full blur-3xl"></div>
      </div>

      {/* ── HEADER ── */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/60 backdrop-blur-md rounded-2xl p-6 border border-white/40 shadow-lg"
      >
        <div>
          <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-neutral-900 to-neutral-600 bg-clip-text text-transparent">
            Transactions
          </h1>
          <p className="text-xs text-neutral-600 mt-0.5">
            {loading ? 'Loading…' : `${pagination.total} transactions total`}
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={!transactions.length}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-lg"
          style={{ background: 'linear-gradient(135deg,#0ea5e9,#0284c7)' }}
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </motion.div>

      {/* ── SUMMARY PILLS ── */}
      {!loading && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
          className="flex flex-wrap gap-3">
          {[
            { label: 'Showing', value: `${transactions.length} of ${pagination.total}`, color: '#6b7280' },
            { label: 'Income', value: `₹${totalIncome.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, color: '#10b981' },
            { label: 'Expenses', value: `₹${totalExpenses.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, color: '#ef4444' }
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/50 backdrop-blur-sm border border-white/40 shadow-sm">
              <span className="text-xs text-neutral-600 font-medium">{item.label}</span>
              <span className="text-sm font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* ── SEARCH + FILTER BAR ── */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="flex flex-col sm:flex-row gap-3">

        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500 pointer-events-none" />
          <input
            ref={searchRef}
            type="text"
            defaultValue={filters.search}
            onChange={e => handleSearchChange(e.target.value)}
            placeholder="Search transactions…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm text-neutral-900 placeholder-neutral-500 outline-none transition-all focus:ring-2 focus:ring-primary-400 bg-white/60 backdrop-blur-sm border border-white/40"
          />
        </div>

        {/* Type toggle */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-white/50 backdrop-blur-sm border border-white/40">
          {['all', 'income', 'expense'].map(t => (
            <button key={t} onClick={() => handleTypeChange(t)}
              className="px-3 py-2 rounded-lg text-xs font-semibold capitalize transition-all"
              style={filters.type === t
                ? { background: 'linear-gradient(135deg,#0ea5e9,#0284c7)', color: '#fff' }
                : { color: '#6b7280' }}>
              {t}
            </button>
          ))}
        </div>

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilterPanel(v => !v)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all"
          style={{
            background: showFilterPanel ? 'rgba(14,165,233,0.15)' : 'rgba(255,255,255,0.5)',
            border: showFilterPanel ? '1px solid rgba(14,165,233,0.4)' : '1px solid rgba(255,255,255,0.4)',
            color: showFilterPanel ? '#0ea5e9' : '#6b7280'
          }}
        >
          <SlidersHorizontal className="w-4 h-4" />
          Filters
          {filters.categories.length > 0 && (
            <span className="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center bg-primary-600 text-white">
              {filters.categories.length}
            </span>
          )}
        </button>
      </motion.div>

      {/* ── FILTER PANEL ── */}
      <AnimatePresence>
        {showFilterPanel && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="rounded-2xl p-5 bg-white/50 backdrop-blur-sm border border-white/40">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-bold text-neutral-700 uppercase tracking-wide">Filter by Category</p>
                {filters.categories.length > 0 && (
                  <button
                    className="text-xs text-primary-600 hover:text-primary-700 transition-colors font-semibold"
                    onClick={() => {
                      const next = { ...filters, categories: [] }
                      setFilters(next)
                      fetchTransactions(1, next)
                    }}>
                    Clear
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map(cat => {
                  const active = filters.categories.includes(cat)
                  const color = getCategoryColor(cat)
                  return (
                    <button key={cat} onClick={() => toggleCategory(cat)}
                      className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all hover:scale-105"
                      style={active
                        ? { background: `${color}25`, color, border: `1px solid ${color}50` }
                        : { background: 'rgba(255,255,255,0.6)', color: '#6b7280', border: '1px solid rgba(255,255,255,0.4)' }}>
                      {cat}
                    </button>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── ACTIVE FILTER CHIPS ── */}
      <AnimatePresence>
        {hasFilters && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex flex-wrap items-center gap-2"
          >
            <span className="text-xs text-gray-600 font-medium">Active:</span>
            {filters.search && (
              <FilterChip label={`"${filters.search}"`} color="#6366f1"
                onRemove={() => { handleSearchChange(''); if (searchRef.current) searchRef.current.value = '' }} />
            )}
            {filters.type !== 'all' && (
              <FilterChip label={filters.type} color="#8b5cf6"
                onRemove={() => handleTypeChange('all')} />
            )}
            {filters.categories.map(cat => (
              <FilterChip key={cat} label={cat} color={getCategoryColor(cat)}
                onRemove={() => toggleCategory(cat)} />
            ))}
            <button onClick={clearAll} className="text-xs text-gray-500 hover:text-rose-400 transition-colors font-medium ml-1">
              Clear all
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── TABLE ── */}
      {loading ? (
        <div className="flex items-center justify-center py-20 bg-white/40 backdrop-blur-sm rounded-2xl border border-white/40">
          <div className="text-center">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              className="w-10 h-10 rounded-full border-2 border-primary-500/20 border-t-primary-500 mx-auto mb-3" />
            <p className="text-neutral-600 text-sm">Loading transactions…</p>
          </div>
        </div>
      ) : error ? (
        <div className="rounded-2xl p-8 text-center bg-danger-50/50 backdrop-blur-sm border border-danger-200">
          <p className="text-danger-600 mb-4 font-semibold">{error}</p>
          <button onClick={() => fetchTransactions(1)} className="px-5 py-2 rounded-xl bg-danger-500/20 text-danger-600 text-sm font-semibold border border-danger-500/30 hover:bg-danger-500/30 transition-all">
            Retry
          </button>
        </div>
      ) : transactions.length === 0 ? (
        <div className="rounded-2xl p-12 text-center bg-white/40 backdrop-blur-sm border border-white/40">
          <Filter className="w-10 h-10 text-neutral-400 mx-auto mb-3" />
          <p className="text-neutral-600 text-sm">No transactions match your filters</p>
          {hasFilters && (
            <button onClick={clearAll} className="mt-3 text-primary-600 text-xs hover:text-primary-700 transition-colors font-semibold">Clear filters</button>
          )}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl overflow-hidden bg-white/60 backdrop-blur-md border border-white/40 shadow-lg"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                  <th className="w-10 py-3 pl-4" />
                  <th className="py-3 px-3 text-left">
                    <span className="text-xs font-bold text-neutral-600 uppercase tracking-wide">Date</span>
                  </th>
                  <th className="py-3 px-3 text-left">
                    <span className="text-xs font-bold text-neutral-600 uppercase tracking-wide">Description</span>
                  </th>
                  <th className="py-3 px-3 text-left hidden sm:table-cell">
                    <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Category</span>
                  </th>
                  <th className="py-3 pl-3 pr-4 text-right">
                    <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Amount</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence mode="sync">
                  {transactions.map((txn, i) => (
                    <TransactionRow
                      key={txn.id || i}
                      txn={txn}
                      index={i}
                      onUpdateCategory={handleCategoryUpdate}
                    />
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* ── PAGINATION ── */}
      {!loading && transactions.length > 0 && pagination.totalPages > 1 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-3 px-1"
        >
          <p className="text-xs text-gray-600">
            Page <span className="text-gray-400 font-semibold">{pagination.page}</span> of <span className="text-gray-400 font-semibold">{pagination.totalPages}</span>
            <span className="ml-2 text-gray-600">({pagination.total} total)</span>
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePage(pagination.page - 1)}
              disabled={pagination.page === 1}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)', color: '#9ca3af' }}
            >
              <ChevronLeft className="w-4 h-4" />
              Prev
            </button>

            {/* Page numbers (show ±2 around current) */}
            <div className="hidden sm:flex items-center gap-1">
              {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                const start = Math.max(1, Math.min(pagination.page - 2, pagination.totalPages - 4))
                const pg = start + i
                if (pg > pagination.totalPages) return null
                return (
                  <button key={pg} onClick={() => handlePage(pg)}
                    className="w-9 h-9 rounded-xl text-sm font-semibold transition-all"
                    style={pg === pagination.page
                      ? { background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff' }
                      : { background: 'rgba(255,255,255,0.04)', color: '#6b7280', border: '1px solid rgba(255,255,255,0.07)' }}>
                    {pg}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => handlePage(pagination.page + 1)}
              disabled={pagination.page === pagination.totalPages}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)', color: '#9ca3af' }}
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default Transactions