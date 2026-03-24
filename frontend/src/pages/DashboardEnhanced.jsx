import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  FileText,
  ArrowUpRight,
  DollarSign,
  Activity,
  Sparkles,
  Zap,
  BarChart3
} from 'lucide-react'
import { motion } from 'framer-motion'
import CountUp from 'react-countup'
import { useInView } from 'react-intersection-observer'
import { TypeAnimation } from 'react-type-animation'
import Confetti from 'react-confetti'

const DashboardEnhanced = () => {
  const [stats, setStats] = useState({
    totalTransactions: 0,
    totalIncome: 0,
    totalExpenses: 0,
    balance: 0,
  })

  const [recentTransactions, setRecentTransactions] = useState([])
  const [showConfetti, setShowConfetti] = useState(false)
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 })

  useEffect(() => {
    const savedData = localStorage.getItem('dashboardData')
    if (savedData) {
      const data = JSON.parse(savedData)
      setStats(data.stats || stats)
      setRecentTransactions(data.recentTransactions || [])
    }
  }, [])

  const statCards = [
    {
      title: 'Total Balance',
      value: stats.balance,
      icon: Wallet,
      gradient: 'from-blue-500 to-cyan-500',
      trend: '+12.5%',
      trendUp: true,
    },
    {
      title: 'Total Income',
      value: stats.totalIncome,
      icon: TrendingUp,
      gradient: 'from-green-500 to-emerald-500',
      trend: '+8.2%',
      trendUp: true,
    },
    {
      title: 'Total Expenses',
      value: stats.totalExpenses,
      icon: TrendingDown,
      gradient: 'from-red-500 to-pink-500',
      trend: '-3.1%',
      trendUp: false,
    },
    {
      title: 'Transactions',
      value: stats.totalTransactions,
      icon: FileText,
      gradient: 'from-purple-500 to-indigo-500',
      trend: '+15',
      trendUp: true,
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.3
      }
    }
  }

  const itemVariants = {
    hidden: { y: 50, opacity: 0, scale: 0.8 },
    visible: {
      y: 0,
      opacity: 1,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 12
      }
    }
  }

  const floatingAnimation = {
    y: [0, -20, 0],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: "easeInOut"
    }
  }

  return (
    <div className="space-y-8 relative">
      {showConfetti && (
        <Confetti
          width={window.innerWidth}
          height={window.innerHeight}
          recycle={false}
          numberOfPieces={500}
          onConfettiComplete={() => setShowConfetti(false)}
        />
      )}

      {/* Hero Section with Animated Text */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, type: "spring" }}
        className="glass-card relative overflow-hidden"
      >
        {/* Animated Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-purple-600/20 animate-gradient-x"></div>
        
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex-1">
            <motion.h1 
              className="text-5xl font-bold mb-4 gradient-text"
              animate={{ backgroundPosition: ['0%', '100%', '0%'] }}
              transition={{ duration: 5, repeat: Infinity }}
            >
              <TypeAnimation
                sequence={[
                  'Welcome to FinanceAI',
                  2000,
                  'AI-Powered Financial Analysis',
                  2000,
                  'Smart Money Management',
                  2000,
                ]}
                wrapper="span"
                speed={50}
                repeat={Infinity}
              />
            </motion.h1>
            <p className="text-xl text-purple-200 mb-6">
              Transform your financial data into actionable insights
            </p>
            <div className="flex gap-4">
              <Link to="/upload">
                <motion.button
                  whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(168, 85, 247, 0.6)" }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-primary flex items-center gap-2"
                >
                  <Sparkles className="w-5 h-5" />
                  Get Started
                </motion.button>
              </Link>
              <Link to="/analytics">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-secondary flex items-center gap-2"
                >
                  <BarChart3 className="w-5 h-5" />
                  View Analytics
                </motion.button>
              </Link>
            </div>
          </div>
          <motion.div
            animate={floatingAnimation}
            className="hidden lg:block"
          >
            <div className="relative">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="w-64 h-64 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full opacity-20 blur-3xl"
              ></motion.div>
              <Activity className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-32 h-32 text-purple-300" />
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Stats Grid with Counter Animation */}
      <motion.div 
        ref={ref}
        variants={containerVariants}
        initial="hidden"
        animate={inView ? "visible" : "hidden"}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.title}
              variants={itemVariants}
              whileHover={{ 
                scale: 1.05, 
                rotateY: 5,
                boxShadow: "0 20px 60px rgba(168, 85, 247, 0.4)"
              }}
              className="card relative overflow-hidden group cursor-pointer"
            >
              {/* Animated Background */}
              <motion.div
                className={`absolute inset-0 bg-gradient-to-br ${stat.gradient} opacity-0 group-hover:opacity-20 transition-opacity duration-500`}
              ></motion.div>
              
              <div className="relative z-10">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <p className="text-sm text-purple-200 mb-2">{stat.title}</p>
                    <h3 className="text-3xl font-bold text-white">
                      {stat.title.includes('Balance') || stat.title.includes('Income') || stat.title.includes('Expenses') ? (
                        <>
                          ₹<CountUp end={stat.value} duration={2.5} separator="," decimals={2} />
                        </>
                      ) : (
                        <CountUp end={stat.value} duration={2} />
                      )}
                    </h3>
                    <motion.div 
                      className={`flex items-center gap-1 text-sm mt-2 ${
                        stat.trendUp ? 'text-green-400' : 'text-red-400'
                      }`}
                      initial={{ x: -20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                    >
                      <motion.div
                        animate={{ y: stat.trendUp ? [-2, 2, -2] : [2, -2, 2] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <ArrowUpRight className={`w-4 h-4 ${!stat.trendUp && 'rotate-90'}`} />
                      </motion.div>
                      <span className="font-semibold">{stat.trend}</span>
                    </motion.div>
                  </div>
                  <motion.div 
                    className={`bg-gradient-to-br ${stat.gradient} p-4 rounded-2xl shadow-lg`}
                    whileHover={{ rotate: 360, scale: 1.1 }}
                    transition={{ duration: 0.6 }}
                  >
                    <Icon className="w-8 h-8 text-white" />
                  </motion.div>
                </div>
              </div>

              {/* Shine Effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.6 }}
              ></motion.div>
            </motion.div>
          )
        })}
      </motion.div>

      {/* Quick Actions & Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6, type: "spring" }}
          className="card"
        >
          <h3 className="text-2xl font-bold mb-6 gradient-text">Quick Actions</h3>
          <div className="space-y-4">
            {[
              { to: '/upload', icon: FileText, title: 'Upload Statement', desc: 'Process new PDF', gradient: 'from-blue-500 to-cyan-500' },
              { to: '/chat', icon: Zap, title: 'Ask AI', desc: 'Query your data', gradient: 'from-green-500 to-emerald-500' },
              { to: '/analytics', icon: TrendingUp, title: 'View Analytics', desc: 'Insights & trends', gradient: 'from-purple-500 to-pink-500' }
            ].map((action, index) => (
              <Link key={index} to={action.to}>
                <motion.div
                  whileHover={{ scale: 1.03, x: 10 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-all duration-300 border border-white/10 hover:border-white/30 group"
                >
                  <motion.div 
                    className={`w-14 h-14 bg-gradient-to-br ${action.gradient} rounded-xl flex items-center justify-center shadow-lg`}
                    whileHover={{ rotate: 360 }}
                    transition={{ duration: 0.6 }}
                  >
                    <action.icon className="w-7 h-7 text-white" />
                  </motion.div>
                  <div>
                    <p className="font-semibold text-white group-hover:text-purple-300 transition-colors">{action.title}</p>
                    <p className="text-sm text-purple-200">{action.desc}</p>
                  </div>
                </motion.div>
              </Link>
            ))}
          </div>
        </motion.div>

        {/* Recent Transactions */}
        <motion.div 
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.7, type: "spring" }}
          className="lg:col-span-2 card"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold gradient-text">Recent Transactions</h3>
            <Link to="/transactions">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="text-sm text-purple-300 hover:text-purple-100 font-semibold"
              >
                View all →
              </motion.button>
            </Link>
          </div>
          
          {recentTransactions.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-16"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              >
                <DollarSign className="w-16 h-16 text-purple-300 mx-auto mb-4" />
              </motion.div>
              <p className="text-purple-200 mb-4">No transactions yet</p>
              <Link to="/upload">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="btn-primary"
                >
                  Upload your first statement
                </motion.button>
              </Link>
            </motion.div>
          ) : (
            <div className="space-y-3">
              {recentTransactions.slice(0, 5).map((transaction, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                  whileHover={{ scale: 1.02, x: 5 }}
                  className="flex items-center justify-between p-4 rounded-xl bg-white/5 hover:bg-white/10 transition-all duration-300 border border-white/10"
                >
                  <div className="flex items-center gap-4">
                    <motion.div 
                      className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        transaction.type === 'credit' ? 'bg-gradient-to-br from-green-500 to-emerald-500' : 'bg-gradient-to-br from-red-500 to-pink-500'
                      }`}
                      whileHover={{ rotate: 360 }}
                      transition={{ duration: 0.6 }}
                    >
                      {transaction.type === 'credit' ? (
                        <TrendingUp className="w-6 h-6 text-white" />
                      ) : (
                        <TrendingDown className="w-6 h-6 text-white" />
                      )}
                    </motion.div>
                    <div>
                      <p className="font-semibold text-white">{transaction.description}</p>
                      <p className="text-sm text-purple-200">{transaction.date}</p>
                    </div>
                  </div>
                  <div className={`font-bold text-lg ${
                    transaction.type === 'credit' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {transaction.type === 'credit' ? '+' : '-'}₹{transaction.amount.toLocaleString('en-IN')}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}

export default DashboardEnhanced
