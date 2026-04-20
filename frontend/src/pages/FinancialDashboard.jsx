import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  FileText,
  ArrowUpRight,
  DollarSign,
  PieChart,
  Upload as UploadIcon,
  MessageSquare,
  Calendar,
  CheckCircle
} from 'lucide-react'
import { motion } from 'framer-motion'
import CountUp from 'react-countup'
import { useInView } from 'react-intersection-observer'
import { statementsAPI } from '../services/api'

const FinancialDashboard = () => {
  const [stats, setStats] = useState({
    totalTransactions: 0,
    totalIncome: 0,
    totalExpenses: 0,
    balance: 0,
  })

  const [recentTransactions, setRecentTransactions] = useState([])
  const [loading, setLoading] = useState(false)
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 })

  useEffect(() => {
    // Fetch data from backend
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)

      // Fetch all statements from backend
      const statements = await statementsAPI.getAllStatements()

      if (statements && statements.length > 0) {
        let allTransactions = []
        let totalIncome = 0
        let totalExpenses = 0

        // Fetch transactions from each statement
        for (const statement of statements) {
          try {
            const details = await statementsAPI.getStatementDetails(statement.upload_id)
            if (details.transactions && Array.isArray(details.transactions)) {
              allTransactions = [...allTransactions, ...details.transactions]
            }
          } catch (error) {
            console.warn(`Failed to fetch details for statement ${statement.upload_id}:`, error)
          }
        }

        // Calculate stats from backend data
        totalIncome = allTransactions.reduce((sum, t) => sum + (parseFloat(t.credit) || 0), 0)
        totalExpenses = allTransactions.reduce((sum, t) => sum + (parseFloat(t.debit) || 0), 0)
        const balance = totalIncome - totalExpenses

        // Update state with backend data
        setStats({
          totalTransactions: allTransactions.length,
          totalIncome: totalIncome,
          totalExpenses: totalExpenses,
          balance: balance,
        })

        // Set recent transactions (last 10)
        setRecentTransactions(allTransactions.slice(0, 10).map(t => ({
          description: t.description || 'N/A',
          date: t.date || 'N/A',
          amount: parseFloat(t.credit || t.debit || 0),
          type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
          category: t.category || 'Uncategorized'
        })))

        // Save to localStorage as cache
        const dashboardData = {
          stats: {
            totalTransactions: allTransactions.length,
            totalIncome: totalIncome,
            totalExpenses: totalExpenses,
            balance: balance,
          },
          allTransactions: allTransactions,
          recentTransactions: allTransactions.slice(0, 10).map(t => ({
            description: t.description || 'N/A',
            date: t.date || 'N/A',
            amount: parseFloat(t.credit || t.debit || 0),
            type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
            category: t.category || 'Uncategorized'
          }))
        }
        localStorage.setItem('dashboardData', JSON.stringify(dashboardData))
      } else {
        // No statements from backend - use localStorage fallback
        const savedData = localStorage.getItem('dashboardData')
        if (savedData) {
          try {
            const data = JSON.parse(savedData)
            if (data.stats) {
              setStats(data.stats)
            }
            if (data.recentTransactions) {
              setRecentTransactions(data.recentTransactions)
            }
          } catch (error) {
            console.error('Error loading cached dashboard data:', error)
          }
        }
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)

      // Fallback to localStorage
      const savedData = localStorage.getItem('dashboardData')
      if (savedData) {
        try {
          const data = JSON.parse(savedData)
          if (data.stats) {
            setStats(data.stats)
          }
          if (data.recentTransactions) {
            setRecentTransactions(data.recentTransactions)
          }
        } catch (e) {
          console.error('Error loading cached data:', e)
        }
      }
    } finally {
      setLoading(false)
    }
  }



  const statCards = [
    {
      title: 'Total Balance',
      value: stats.balance,
      icon: Wallet,
      color: 'blue',
      bgColor: 'bg-blue-50',
      iconColor: 'text-blue-600',
      trend: '+12.5%',
      trendUp: true,
    },
    {
      title: 'Total Income',
      value: stats.totalIncome,
      icon: TrendingUp,
      color: 'green',
      bgColor: 'bg-green-50',
      iconColor: 'text-green-600',
      trend: '+8.2%',
      trendUp: true,
    },
    {
      title: 'Total Expenses',
      value: stats.totalExpenses,
      icon: TrendingDown,
      color: 'red',
      bgColor: 'bg-red-50',
      iconColor: 'text-red-600',
      trend: '-3.1%',
      trendUp: false,
    },
    {
      title: 'Transactions',
      value: stats.totalTransactions,
      icon: FileText,
      color: 'purple',
      bgColor: 'bg-purple-50',
      iconColor: 'text-purple-600',
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
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card bg-gradient-to-r from-blue-600 to-green-600 text-white"
      >
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex-1">
            <h1 className="text-3xl md:text-4xl font-bold mb-3">
              Welcome to FinanceAI
            </h1>
            <p className="text-blue-100 text-lg mb-6">
              Your intelligent financial management platform. Upload statements, track expenses, and get AI-powered insights.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/upload">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all flex items-center gap-2"
                >
                  <UploadIcon className="w-5 h-5" />
                  Upload Statement
                </motion.button>
              </Link>
              <Link to="/analytics">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-800 transition-all flex items-center gap-2"
                >
                  <PieChart className="w-5 h-5" />
                  View Analytics
                </motion.button>
              </Link>
            </div>
          </div>
          <div className="hidden lg:block">
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              className="w-48 h-48 bg-white/10 rounded-full flex items-center justify-center backdrop-blur-sm"
            >
              <DollarSign className="w-24 h-24 text-white" />
            </motion.div>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        ref={ref}
        variants={containerVariants}
        initial="hidden"
        animate={inView ? "visible" : "hidden"}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.title}
              variants={itemVariants}
              whileHover={{ y: -5, shadow: "lg" }}
              className="card"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-2">{stat.title}</p>
                  <h3 className="text-3xl font-bold text-gray-900">
                    {stat.title.includes('Balance') || stat.title.includes('Income') || stat.title.includes('Expenses') ? (
                      <>
                        ₹<CountUp end={stat.value} duration={2} separator="," decimals={2} />
                      </>
                    ) : (
                      <CountUp end={stat.value} duration={2} />
                    )}
                  </h3>
                  <div className={`flex items-center gap-1 text-sm mt-2 ${stat.trendUp ? 'text-green-600' : 'text-red-600'
                    }`}>
                    <ArrowUpRight className={`w-4 h-4 ${!stat.trendUp && 'rotate-90'}`} />
                    <span className="font-semibold">{stat.trend}</span>
                    <span className="text-gray-500">vs last month</span>
                  </div>
                </div>
                <div className={`${stat.bgColor} p-3 rounded-xl`}>
                  <Icon className={`w-7 h-7 ${stat.iconColor}`} />
                </div>
              </div>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Quick Actions & Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <h3 className="text-xl font-bold text-[var(--text-primary)] mb-4">Quick Actions</h3>
          <div className="space-y-3">
            {[
              { to: '/upload', icon: UploadIcon, title: 'Upload Statement', desc: 'Process bank PDFs', color: 'blue' },
              { to: '/chat', icon: MessageSquare, title: 'AI Assistant', desc: 'Ask about finances', color: 'green' },
              { to: '/analytics', icon: PieChart, title: 'View Reports', desc: 'Detailed insights', color: 'purple' }
            ].map((action) => (
              <Link key={action.to} to={action.to}>
                <motion.div
                  whileHover={{ x: 5 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-3 p-4 rounded-lg bg-[var(--bg-card)] hover:bg-[var(--bg-surface)] transition-all border border-[var(--border-subtle)]"
                >
                  <div className={`w-12 h-12 bg-${action.color}-100 rounded-lg flex items-center justify-center`}>
                    <action.icon className={`w-6 h-6 text-${action.color}-600`} />
                  </div>
                  <div>
                    <p className="font-semibold text-[var(--text-primary)]">{action.title}</p>
                    <p className="text-sm text-[var(--text-secondary)]">{action.desc}</p>
                  </div>
                </motion.div>
              </Link>
            ))}
          </div>
        </motion.div>

        {/* Recent Transactions */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-2 card"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-[var(--text-primary)]">Recent Transactions</h3>
            <Link to="/transactions" className="text-sm text-blue-600 hover:text-blue-700 font-semibold">
              View all →
            </Link>
          </div>

          {recentTransactions.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-gray-600 mb-4">No transactions yet</p>
              <Link to="/upload">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-primary"
                >
                  Upload Your First Statement
                </motion.button>
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentTransactions.slice(0, 5).map((transaction, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex items-center justify-between p-4 rounded-lg bg-gray-50 hover:bg-gray-100 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${transaction.type === 'credit' ? 'bg-green-100' : 'bg-red-100'
                      }`}>
                      {transaction.type === 'credit' ? (
                        <TrendingUp className="w-5 h-5 text-green-600" />
                      ) : (
                        <TrendingDown className="w-5 h-5 text-red-600" />
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{transaction.description}</p>
                      <p className="text-sm text-gray-500 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {transaction.date}
                      </p>
                    </div>
                  </div>
                  <div className={`font-bold text-lg ${transaction.type === 'credit' ? 'text-green-600' : 'text-red-600'
                    }`}>
                    {transaction.type === 'credit' ? '+' : '-'}₹{transaction.amount.toLocaleString('en-IN')}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Features Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card bg-gradient-to-r from-blue-50 to-green-50"
      >
        <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">Why Choose FinanceAI?</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: CheckCircle, title: 'AI-Powered', desc: 'Smart categorization and insights' },
            { icon: TrendingUp, title: 'Real-time Analytics', desc: 'Track spending patterns instantly' },
            { icon: MessageSquare, title: 'Chat Assistant', desc: 'Ask questions about your finances' }
          ].map((feature, index) => (
            <div key={index} className="text-center">
              <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-md">
                <feature.icon className="w-8 h-8 text-blue-600" />
              </div>
              <h4 className="font-bold text-gray-900 mb-2">{feature.title}</h4>
              <p className="text-sm text-gray-600">{feature.desc}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}

export default FinancialDashboard
