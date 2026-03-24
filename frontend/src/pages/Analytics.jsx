import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, AreaChart, Area } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Calendar, Sparkles, Target, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '../components/common'
import api from '../services/api'
import toast from 'react-hot-toast'

const Analytics = () => {
  const [analyticsData, setAnalyticsData] = useState({
    categoryData: [],
    monthlyData: [],
    insights: [],
    summary: {}
  })
  const [period, setPeriod] = useState('daily')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAnalyticsData()
  }, [])

  useEffect(() => {
    fetchDateAnalytics()
  }, [period])

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch category analytics
      const categoryResponse = await api.get('/api/analytics/by-category')
      
      // Fetch dashboard stats for summary
      const statsResponse = await api.get('/api/dashboard/stats')
      
      if (categoryResponse.data.status === 'success' && statsResponse.data.status === 'success') {
        // Generate insights
        const topCategory = categoryResponse.data.data.categories[0]
        const balance = statsResponse.data.data.balance
        const totalIncome = statsResponse.data.data.total_income
        const savingsPercentage = totalIncome > 0 ? ((balance / totalIncome) * 100).toFixed(1) : 0
        
        const insights = [
          topCategory ? `Your highest spending category is ${topCategory.name} with ₹${topCategory.total.toLocaleString('en-IN')}` : 'No spending data available',
          `Total savings this period: ₹${balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${savingsPercentage}% of income)`,
          `You have ${statsResponse.data.data.total_transactions} transactions`,
          totalIncome > statsResponse.data.data.total_expenses ? '✅ Great! Your income exceeds expenses' : '⚠️ Your expenses exceed income - consider budgeting'
        ]
        
        setAnalyticsData(prev => ({
          ...prev,
          categoryData: categoryResponse.data.data.categories,
          insights,
          summary: {
            balance: statsResponse.data.data.balance,
            totalIncome: statsResponse.data.data.total_income,
            totalExpenses: statsData.data.total_expenses,
            totalTransactions: statsData.data.total_transactions
          }
        }))
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
      setError(error.message || 'Failed to load analytics data')
      toast.error('Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }

  const fetchDateAnalytics = async () => {
    try {
      const dateResponse = await api.get('/api/analytics/by-date', {
        params: { period }
      })
      
      if (dateResponse.data.status === 'success') {
        setAnalyticsData(prev => ({
          ...prev,
          monthlyData: dateResponse.data.data.periods
        }))
      }
    } catch (error) {
      console.error('Error fetching date analytics:', error)
    }
  }

  const COLORS = ['#0ea5e9', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#6366f1']

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-900">{payload[0].name}</p>
          <p className="text-sm text-gray-600">
            ₹{payload[0].value.toLocaleString('en-IN')}
          </p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Loading analytics data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Analytics</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <Button
            variant="primary"
            onClick={fetchAnalyticsData}
          >
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-xl sm:rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-4 sm:p-6 lg:p-8 shadow-lg sm:shadow-2xl"
      >
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-40 h-40 sm:w-64 sm:h-64 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse"></div>
        </div>
        <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-1 sm:mb-2 flex items-center gap-2 sm:gap-3 flex-wrap">
              <Sparkles className="w-6 h-6 sm:w-8 sm:h-8 lg:w-10 lg:h-10" />
              Financial Analytics
            </h1>
            <p className="text-xs sm:text-sm lg:text-lg text-white/90">AI-powered insights into your spending patterns</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={fetchAnalyticsData}
            className="hidden sm:flex items-center gap-2 px-4 sm:px-6 py-2 sm:py-3 bg-white/20 backdrop-blur-lg text-white rounded-lg sm:rounded-xl font-semibold border border-white/30 hover:bg-white/30 transition-all text-sm flex-shrink-0"
          >
            <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5" />
            Refresh Data
          </motion.button>
        </div>
      </motion.div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Balance</p>
              <h3 className="text-2xl font-bold text-gray-900">
                ₹{analyticsData.summary.balance?.toLocaleString('en-IN') || '0'}
              </h3>
            </div>
            <DollarSign className="w-10 h-10 text-blue-500" />
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Income</p>
              <h3 className="text-2xl font-bold text-green-600">
                ₹{analyticsData.summary.totalIncome?.toLocaleString('en-IN') || '0'}
              </h3>
            </div>
            <TrendingUp className="w-10 h-10 text-green-500" />
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Expenses</p>
              <h3 className="text-2xl font-bold text-red-600">
                ₹{analyticsData.summary.totalExpenses?.toLocaleString('en-IN') || '0'}
              </h3>
            </div>
            <TrendingDown className="w-10 h-10 text-red-500" />
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Transactions</p>
              <h3 className="text-2xl font-bold text-purple-600">
                {analyticsData.summary.totalTransactions || 0}
              </h3>
            </div>
            <Calendar className="w-10 h-10 text-purple-500" />
          </div>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Category Breakdown */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <h3 className="text-lg font-semibold mb-4">Expense by Category</h3>
          {analyticsData.categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={analyticsData.categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {analyticsData.categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No category data available
            </div>
          )}
        </motion.div>

        {/* Monthly Trend */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Income vs Expenses</h3>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-3 py-2 bg-gray-50 border-2 border-gray-200 rounded-lg text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analyticsData.monthlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="income" fill="#10b981" name="Income" />
              <Bar dataKey="expenses" fill="#ef4444" name="Expenses" />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* Spending Trend Line Chart */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card"
      >
        <h3 className="text-lg font-semibold mb-4">Spending Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={analyticsData.monthlyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={2} name="Expenses" />
            <Line type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} name="Income" />
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* AI Insights */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="card"
      >
        <h3 className="text-lg font-semibold mb-4">AI-Powered Insights</h3>
        <div className="space-y-3">
          {analyticsData.insights.map((insight, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-4 h-4 text-white" />
              </div>
              <p className="text-gray-700">{insight}</p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Category Details Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="card"
      >
        <h3 className="text-lg font-semibold mb-4">Category Breakdown</h3>
        {analyticsData.categoryData.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Category</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Amount</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Percentage</th>
                </tr>
              </thead>
              <tbody>
                {analyticsData.categoryData.map((category, index) => {
                  const total = analyticsData.categoryData.reduce((sum, c) => sum + c.value, 0)
                  const percentage = ((category.value / total) * 100).toFixed(1)
                  
                  return (
                    <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <span className="font-medium text-gray-900">{category.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-semibold text-gray-900">
                        ₹{category.value.toLocaleString('en-IN')}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-600">
                        {percentage}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No category data available
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default Analytics
