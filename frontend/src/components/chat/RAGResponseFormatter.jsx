import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp, TrendingDown, AlertCircle, Info, BarChart3,
  MessageSquare, List, Lightbulb, Clock, CheckCircle,
  ArrowRight, ShieldCheck, Zap
} from 'lucide-react'

const ICON_MAP = {
  'TrendingUp': TrendingUp,
  'TrendingDown': TrendingDown,
  'AlertCircle': AlertCircle,
  'Info': Info,
  'BarChart3': BarChart3,
  'MessageSquare': MessageSquare,
  'List': List,
  'Lightbulb': Lightbulb,
  'CheckCircle': CheckCircle,
  'Zap': Zap
}

const RAGResponseFormatter = ({ response, loading, error }) => {
  if (loading) return null

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-2xl flex items-center gap-3 text-red-700 dark:text-red-300"
      >
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <p className="font-semibold text-sm">{error}</p>
      </motion.div>
    )
  }

  if (!response || !response.data) return null

  const { answer, sections = [], metrics = [], insights = [], pagination, processing_time_ms } = response.data

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5 w-full"
    >
      {/* Main answer */}
      <div className="p-4 sm:p-5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center text-primary-600 dark:text-primary-400">
            <MessageSquare className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-[var(--text-primary)] tracking-tight">Summary</h3>
        </div>
        <p className="text-sm sm:text-base text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
          {answer}
        </p>
      </div>

      {/* Metrics & Insights */}
      {(metrics?.length > 0 || insights?.length > 0) && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {metrics?.length > 0 && (
            <div className="p-4 sm:p-5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">Key Statistics</h3>
                </div>
                <ShieldCheck className="w-4 h-4 text-green-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                {metrics.map((metric, idx) => (
                  <div key={idx} className="p-3.5 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl">
                    <p className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-1">{metric.label}</p>
                    <p className="text-lg font-bold text-primary-600 dark:text-primary-400">
                      {metric.formatted || metric.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {insights?.length > 0 && (
            <div className="p-4 sm:p-5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">Insights</h3>
              </div>
              <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
                {insights.map((insight, idx) => {
                  const IconComponent = ICON_MAP[insight.icon] || Info
                  return (
                    <div
                      key={idx}
                      className="p-3 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl flex gap-3 items-center"
                    >
                      <div className="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center text-amber-600 dark:text-amber-400 flex-shrink-0">
                        <IconComponent className="w-4 h-4" />
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-[var(--text-primary)] flex-1">{insight.text}</p>
                      <ArrowRight className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Transactions table */}
      {response.data.transactions?.length > 0 && (
        <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center text-primary-600 dark:text-primary-400">
                <List className="w-4.5 h-4.5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">Matching Transactions</h3>
                <p className="text-xs text-[var(--text-secondary)]">From your bank records</p>
              </div>
            </div>
            {pagination && (
              <span className="px-3 py-1.5 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full text-xs font-bold">
                {pagination.total_count} Matches
              </span>
            )}
          </div>
          <div className="max-h-[420px] overflow-y-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-[var(--bg-card)] text-[var(--text-secondary)] text-xs font-bold uppercase tracking-wider border-b border-[var(--border-subtle)]">
                <tr>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Merchant / Narrative</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {response.data.transactions.map((txn, idx) => (
                  <tr key={idx} className="hover:bg-[var(--bg-card)] transition-colors">
                    <td className="px-5 py-3 text-[var(--text-secondary)] font-mono text-xs">{txn.date}</td>
                    <td className="px-5 py-3">
                      <p className="text-[var(--text-primary)] font-semibold text-sm">
                        {txn.description}
                      </p>
                      <p className="text-[var(--text-secondary)] text-[10px] uppercase tracking-wider">{txn.category || 'Financial'}</p>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span className="px-2.5 py-1 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-[var(--text-primary)] font-bold text-sm">
                        ₹{Number(txn.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[var(--border-subtle)]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider">
            <Zap className="w-3.5 h-3.5 text-primary-500" />
            Agentic RAG
          </div>
          {processing_time_ms && (
            <div className="flex items-center gap-1.5 text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider">
              <Clock className="w-3.5 h-3.5 text-primary-500" />
              {processing_time_ms}ms
            </div>
          )}
        </div>
        <p className="text-[10px] font-bold text-[var(--text-secondary)] uppercase tracking-wider">
          Secure • End-to-End Encrypted
        </p>
      </div>
    </motion.div>
  )
}

export default RAGResponseFormatter
