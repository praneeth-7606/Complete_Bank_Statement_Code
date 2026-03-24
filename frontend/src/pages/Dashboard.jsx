import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  FileText,
  DollarSign,
  Activity,
  Upload as UploadIcon,
  MessageSquare,
  BarChart3,
  Loader2
} from 'lucide-react'
import { motion } from 'framer-motion'
import { Button, EmptyState } from '../components/common'
import StatisticsGrid from '../components/dashboard/StatisticsGrid'
import SpendingChart from '../components/dashboard/SpendingChart'
import CategoryBreakdown from '../components/dashboard/CategoryBreakdown'
import RecentTransactions from '../components/dashboard/RecentTransactions'
import api from '../services/api'
import toast from 'react-hot-toast'

const Dashboard = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    total_transactions: 0,
    total_income: 0,
    total_expenses: 0,
    balance: 0,
    average_transaction: 0,
    largest_expense: 0,
    largest_income: 0
  })

  const [recentTransactions, setRecentTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch dashboard stats from backend
  const fetchDashboardStats = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await api.get('/api/dashboard/stats')
      
      if (response.data.status === 'success') {
        setStats(response.data.data)
        
        // Fetch recent transactions for the dashboard
        const txnResponse = await api.get('/api/transactions/filtered', {
          params: { page: 1, limit: 10 }
        })
        
        if (txnResponse.data.status === 'success') {
          setRecentTransactions(txnResponse.data.data.transactions)
        }
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (error) {
      console.error('Error fetching dashboard stats:', error)
      setError(error.message || 'Failed to load dashboard data')
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboardStats()
  }, [])

  const statCards = [
    {
      title: 'Total Balance',
      value: `₹${stats.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
      icon: Wallet,
      color: 'bg-blue-500',
      trend: '+12.5%',
      trendUp: true,
    },
    {
      title: 'Total Income',
      value: `₹${stats.total_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
      icon: TrendingUp,
      color: 'bg-green-500',
      trend: '+8.2%',
      trendUp: true,
    },
    {
      title: 'Total Expenses',
      value: `₹${stats.total_expenses.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
      icon: TrendingDown,
      color: 'bg-red-500',
      trend: '-3.1%',
      trendUp: false,
    },
    {
      title: 'Transactions',
      value: stats.total_transactions.toString(),
      icon: FileText,
      color: 'bg-purple-500',
      trend: '+15',
      trendUp: true,
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Dashboard</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <Button
            variant="primary"
            onClick={fetchDashboardStats}
          >
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Welcome Section */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card bg-gradient-to-r from-primary-500 to-primary-700 text-white"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold mb-1 sm:mb-2">Welcome to FinanceAI</h1>
            <p className="text-sm sm:text-base text-primary-100">
              AI-powered financial statement analysis at your fingertips
            </p>
          </div>
          <Activity className="w-12 h-12 sm:w-16 sm:h-16 opacity-20 flex-shrink-0" />
        </div>
      </motion.div>

      {/* Stats Grid - NEW DESIGN */}
      <StatisticsGrid 
        stats={stats}
        onCardClick={(type) => {
          if (type === 'transactions') navigate('/transactions')
          else navigate(`/transactions?filter=${type}`)
        }}
      />

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <SpendingChart />
        <CategoryBreakdown />
      </div>

      {/* Quick Actions & Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Quick Actions */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <h3 className="text-lg font-semibold mb-4 text-gray-900">Quick Actions</h3>
          <div className="space-y-3">
            <Button
              variant="secondary"
              icon={UploadIcon}
              iconPosition="left"
              onClick={() => navigate('/upload')}
              className="w-full justify-start"
            >
              <div className="flex-1 text-left">
                <p className="font-medium text-gray-900">Upload Statement</p>
                <p className="text-xs text-gray-600">Process new PDF</p>
              </div>
            </Button>
            
            <Button
              variant="secondary"
              icon={MessageSquare}
              iconPosition="left"
              onClick={() => navigate('/chat')}
              className="w-full justify-start"
            >
              <div className="flex-1 text-left">
                <p className="font-medium text-gray-900">Ask AI</p>
                <p className="text-xs text-gray-600">Query your data</p>
              </div>
            </Button>

            <Button
              variant="secondary"
              icon={BarChart3}
              iconPosition="left"
              onClick={() => navigate('/analytics')}
              className="w-full justify-start"
            >
              <div className="flex-1 text-left">
                <p className="font-medium text-gray-900">View Analytics</p>
                <p className="text-xs text-gray-600">Insights & trends</p>
              </div>
            </Button>
          </div>
        </motion.div>

        {/* Recent Transactions */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2"
        >
          <RecentTransactions transactions={recentTransactions} />
        </motion.div>
      </div>
    </div>
  )
}

export default Dashboard
