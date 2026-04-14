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
  if (loading) return null; // Handled by parent Chat component

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="p-6 bg-red-50/50 backdrop-blur-sm border-2 border-red-100 rounded-[2rem] flex items-center gap-4 text-red-700"
      >
        <AlertCircle className="w-6 h-6 flex-shrink-0" />
        <p className="font-semibold">{error}</p>
      </motion.div>
    )
  }

  if (!response || !response.data) return null

  const { answer, sections = [], metrics = [], insights = [], pagination, processing_time_ms } = response.data

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8 w-full"
    >
      {/* 1. Main Insight Card (Answer) */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="relative group"
      >
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-[2.5rem] blur opacity-15 group-hover:opacity-25 transition duration-1000 group-hover:duration-200"></div>
        <div className="relative p-6 sm:p-8 lg:p-10 bg-white/90 backdrop-blur-xl border border-white/60 rounded-[2.5rem] shadow-2xl">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
              <MessageSquare className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-700 to-purple-800 tracking-tight">AI Financial Summary</h3>
          </div>
          <p className="text-base sm:text-lg text-gray-800 leading-[1.8] font-medium whitespace-pre-wrap selection:bg-indigo-100 italic">
            {answer}
          </p>
        </div>
      </motion.div>

      {/* 2. Metrics & Insights Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Metrics */}
        {metrics && metrics.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-6 sm:p-8 bg-gradient-to-br from-indigo-600/5 to-purple-600/5 border border-indigo-100/50 rounded-[2.5rem] shadow-xl"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-6 h-6 text-indigo-600" />
                <h3 className="text-xl font-bold text-gray-900">Key Statistics</h3>
              </div>
              <ShieldCheck className="w-5 h-5 text-green-500" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {metrics.map((metric, idx) => (
                <motion.div
                  key={idx}
                  whileHover={{ y: -5, scale: 1.02 }}
                  className="p-5 bg-white border border-gray-100 rounded-3xl shadow-sm hover:shadow-xl transition-all"
                >
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">{metric.label}</p>
                  <p className="text-xl sm:text-2xl font-black text-indigo-600 tracking-tight">
                    {metric.formatted || metric.value}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Insights */}
        {insights && insights.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-6 sm:p-8 bg-gradient-to-br from-amber-600/5 to-orange-600/5 border border-amber-100/50 rounded-[2.5rem] shadow-xl"
          >
            <div className="flex items-center gap-3 mb-6">
              <Lightbulb className="w-6 h-6 text-amber-600" />
              <h3 className="text-xl font-bold text-gray-900">Strategic Insights</h3>
            </div>
            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {insights.map((insight, idx) => {
                const IconComponent = ICON_MAP[insight.icon] || Info
                return (
                  <motion.div
                    key={idx}
                    whileHover={{ x: 10 }}
                    transition={{ type: "spring", stiffness: 300 }}
                    className="p-4 bg-white/60 backdrop-blur-sm border border-white/80 rounded-2xl flex gap-4 items-center group cursor-pointer"
                  >
                    <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 group-hover:scale-110 transition-transform">
                      <IconComponent className="w-5 h-5" />
                    </div>
                    <p className="text-sm font-semibold text-gray-700 flex-1">{insight.text}</p>
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}
      </div>

      {/* 3. Deep-Dive Transactions (Data Table style) */}
      {response.data.transactions && response.data.transactions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden bg-gray-900 rounded-[2.5rem] shadow-2xl border border-gray-800"
        >
          <div className="p-6 sm:p-8 lg:p-10 border-b border-gray-800 bg-gray-900/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 border border-indigo-500/30">
                <List className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">Retrieved Data points</h3>
                <p className="text-gray-400 text-sm">Synchronized with bank ledger records</p>
              </div>
            </div>
            {pagination && (
              <span className="px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-full text-xs font-bold border border-indigo-500/30">
                {pagination.total_count} Matches
              </span>
            )}
          </div>
          <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-gray-900/90 backdrop-blur-md text-gray-400 text-xs font-bold uppercase tracking-[0.2em] border-b border-gray-800">
                <tr>
                  <th className="px-8 py-5">Date</th>
                  <th className="px-8 py-5">Merchant / Narrative</th>
                  <th className="px-8 py-5 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {response.data.transactions.map((txn, idx) => (
                  <motion.tr
                    key={idx}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.02 }}
                    className="hover:bg-indigo-500/5 transition-colors group"
                  >
                    <td className="px-8 py-5 text-gray-500 font-mono text-sm">{txn.date}</td>
                    <td className="px-8 py-5">
                      <p className="text-gray-200 font-bold tracking-tight group-hover:text-indigo-400 transition-colors uppercase text-sm">
                        {txn.description}
                      </p>
                      <p className="text-gray-600 text-[10px] font-bold uppercase tracking-widest">{txn.category || 'Financial'}</p>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <span className="px-3 py-1 bg-white/5 rounded-lg text-indigo-400 font-black text-base italic">
                        ₹{txn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* 4. Footer & Performance */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-400 tracking-widest uppercase">
            <Zap className="w-4 h-4 text-indigo-500" />
            Neural Logic Engine v4
          </div>
          {processing_time_ms && (
            <div className="flex items-center gap-2 text-xs font-bold text-gray-400 tracking-widest uppercase bg-gray-50 px-3 py-1 rounded-full border border-gray-100">
              <Clock className="w-4 h-4 text-indigo-500" />
              Lat: {processing_time_ms}ms
            </div>
          )}
        </div>
        <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">
          Secure Processing • End-to-End Encryption • AI Trust Validated
        </p>
      </div>
    </motion.div>
  )
}

export default RAGResponseFormatter
