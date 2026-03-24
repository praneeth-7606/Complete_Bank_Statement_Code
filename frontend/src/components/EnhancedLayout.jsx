import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Upload, 
  List, 
  MessageSquare, 
  BarChart3, 
  Settings,
  Menu,
  X,
  Sparkles,
  Zap
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const EnhancedLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard, gradient: 'from-blue-500 to-cyan-500' },
    { name: 'Upload', href: '/upload', icon: Upload, gradient: 'from-purple-500 to-pink-500' },
    { name: 'Transactions', href: '/transactions', icon: List, gradient: 'from-green-500 to-emerald-500' },
    { name: 'Chat', href: '/chat', icon: MessageSquare, gradient: 'from-orange-500 to-red-500' },
    { name: 'Analytics', href: '/analytics', icon: BarChart3, gradient: 'from-indigo-500 to-purple-500' },
    { name: 'Corrections', href: '/corrections', icon: Settings, gradient: 'from-pink-500 to-rose-500' },
  ]

  const isActive = (path) => location.pathname === path

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900"></div>
      
      {/* Animated Gradient Orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, -100, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-0 left-0 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl"
        ></motion.div>
        <motion.div
          animate={{
            x: [0, -100, 0],
            y: [0, 100, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-0 right-0 w-96 h-96 bg-pink-500/30 rounded-full blur-3xl"
        ></motion.div>
        <motion.div
          animate={{
            x: [0, 50, 0],
            y: [0, -50, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/2 left-1/2 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl"
        ></motion.div>
      </div>

      {/* Mobile sidebar backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside 
        initial={false}
        animate={{ x: sidebarOpen ? 0 : -320 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 left-0 z-50 h-full w-80 lg:translate-x-0"
      >
        <div className="h-full bg-white/5 backdrop-blur-2xl border-r border-white/10">
          <div className="flex flex-col h-full">
            {/* Logo */}
            <motion.div 
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-4 px-6 py-8 border-b border-white/10"
            >
              <motion.div 
                whileHover={{ rotate: 360, scale: 1.1 }}
                transition={{ duration: 0.6 }}
                className="w-14 h-14 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/50"
              >
                <Sparkles className="w-8 h-8 text-white" />
              </motion.div>
              <div>
                <h1 className="text-2xl font-bold gradient-text">FinanceAI</h1>
                <p className="text-xs text-purple-300">Smart Analytics</p>
              </div>
            </motion.div>

            {/* Navigation */}
            <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
              {navigation.map((item, index) => {
                const Icon = item.icon
                const active = isActive(item.href)
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      whileHover={{ scale: 1.05, x: 10 }}
                      whileTap={{ scale: 0.95 }}
                      className={`
                        relative flex items-center gap-4 px-5 py-4 rounded-2xl transition-all duration-300
                        ${active
                          ? 'bg-white/15 shadow-lg shadow-purple-500/20'
                          : 'hover:bg-white/10'
                        }
                      `}
                    >
                      {active && (
                        <motion.div
                          layoutId="activeTab"
                          className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl"
                          transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        />
                      )}
                      <motion.div 
                        className={`relative w-12 h-12 rounded-xl flex items-center justify-center ${
                          active ? `bg-gradient-to-br ${item.gradient}` : 'bg-white/10'
                        }`}
                        whileHover={{ rotate: 360 }}
                        transition={{ duration: 0.6 }}
                      >
                        <Icon className={`w-6 h-6 ${active ? 'text-white' : 'text-purple-300'}`} />
                      </motion.div>
                      <span className={`relative font-semibold ${
                        active ? 'text-white' : 'text-purple-200'
                      }`}>
                        {item.name}
                      </span>
                      {active && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="absolute right-5 w-2 h-2 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full"
                        />
                      )}
                    </motion.div>
                  </Link>
                )
              })}
            </nav>

            {/* Footer */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="px-6 py-6 border-t border-white/10"
            >
              <div className="glass-card p-4">
                <div className="flex items-center gap-3 mb-3">
                  <Zap className="w-5 h-5 text-yellow-400" />
                  <span className="text-sm font-semibold text-white">Pro Tip</span>
                </div>
                <p className="text-xs text-purple-200">
                  Use AI Chat to get instant insights about your spending patterns!
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </motion.aside>

      {/* Main content */}
      <div className="lg:pl-80 relative z-10">
        {/* Top bar */}
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="sticky top-0 z-30 bg-white/5 backdrop-blur-xl border-b border-white/10 px-6 py-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-3 rounded-xl bg-white/10 hover:bg-white/20 transition-colors"
              >
                {sidebarOpen ? (
                  <X className="w-6 h-6 text-white" />
                ) : (
                  <Menu className="w-6 h-6 text-white" />
                )}
              </motion.button>
              
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {navigation.find(item => item.href === location.pathname)?.name || 'Dashboard'}
                </h2>
                <p className="text-sm text-purple-300">AI-Powered Financial Intelligence</p>
              </div>
            </div>

            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="hidden sm:flex items-center gap-3 px-5 py-3 rounded-xl bg-white/10 backdrop-blur-lg border border-white/20"
            >
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm text-white font-medium">System Active</span>
            </motion.div>
          </div>
        </motion.header>

        {/* Page content */}
        <main className="p-6 lg:p-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  )
}

export default EnhancedLayout
