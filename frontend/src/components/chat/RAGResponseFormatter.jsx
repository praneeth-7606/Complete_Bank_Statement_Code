import { motion, AnimatePresence } from 'framer-motion'
import { 
  TrendingUp, TrendingDown, AlertCircle, Info, BarChart3, 
  MessageSquare, List, Lightbulb, Clock, CheckCircle
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
  'CheckCircle': CheckCircle
}

const RAGResponseFormatter = ({ response, loading, error }) => {
  if (loading) {
    return (
      <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
        <div className="w-2 h-2 bg-indigo-600 rounded-full animate-pulse"></div>
        <span className="text-sm text-gray-600">AI is thinking...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    )
  }

  if (!response || !response.data) {
    return null
  }

  const { answer, sections = [], metrics = [], insights = [], pagination, processing_time_ms } = response.data

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Main Answer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="p-4 bg-white rounded-lg border border-gray-200 shadow-sm"
      >
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{answer}</p>
      </motion.div>

      {/* Metrics Section */}
      {metrics && metrics.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border border-purple-200"
        >
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-5 h-5 text-purple-600" />
            <h3 className="font-semibold text-gray-900">Key Metrics</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {metrics.map((metric, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + idx * 0.05 }}
                className="p-3 bg-white rounded-lg border border-purple-100"
              >
                <p className="text-xs text-gray-600 mb-1">{metric.label}</p>
                <p className="text-lg font-bold text-purple-600">{metric.formatted || metric.value}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Insights Section */}
      {insights && insights.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-2"
        >
          <div className="flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-600" />
            <h3 className="font-semibold text-gray-900">Insights</h3>
          </div>
          {insights.map((insight, idx) => {
            const bgColor = insight.type === 'positive' 
              ? 'bg-green-50 border-green-200' 
              : insight.type === 'warning' 
              ? 'bg-orange-50 border-orange-200' 
              : 'bg-blue-50 border-blue-200'
            
            const textColor = insight.type === 'positive' 
              ? 'text-green-700' 
              : insight.type === 'warning' 
              ? 'text-orange-700' 
              : 'text-blue-700'
            
            const IconComponent = ICON_MAP[insight.icon] || Info
            
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + idx * 0.05 }}
                className={`p-3 rounded-lg border flex gap-3 ${bgColor}`}
              >
                <IconComponent className={`w-5 h-5 flex-shrink-0 ${textColor}`} />
                <p className={`text-sm ${textColor}`}>{insight.text}</p>
              </motion.div>
            )
          })}
        </motion.div>
      )}

      {/* Transactions Section */}
      {response.data.transactions && response.data.transactions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200"
        >
          <div className="flex items-center gap-2 mb-3">
            <List className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-gray-900">Transactions</h3>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {response.data.transactions.map((txn, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 + idx * 0.05 }}
                className="p-2 bg-white rounded border border-green-100 text-xs"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-900">{txn.description}</p>
                    <p className="text-gray-500">{txn.date}</p>
                  </div>
                  <p className="font-semibold text-green-600">₹{txn.amount.toLocaleString()}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Pagination Info */}
      {pagination && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700"
        >
          <p>
            Showing {pagination.returned_count} of {pagination.total_count} results
            {pagination.has_more && ` (Page ${pagination.current_page})`}
          </p>
        </motion.div>
      )}

      {/* Processing Time */}
      {processing_time_ms && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center gap-2 text-xs text-gray-500"
        >
          <Clock className="w-4 h-4" />
          <span>Response time: {processing_time_ms}ms</span>
        </motion.div>
      )}
    </motion.div>
  )
}

export default RAGResponseFormatter
