import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, LogIn, DollarSign, TrendingUp, Shield, Zap, Sun, Moon } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import toast from 'react-hot-toast'
import { Button, Input } from '../components/ui'

const Login = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [wakingHint, setWakingHint] = useState(false)
  const [focusedField, setFocusedField] = useState(null)
  const { login } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setWakingHint(false)
    // Free-tier backend sleeps when idle: if login takes >8s, tell the user
    // the server is waking up instead of leaving them staring at a spinner.
    const hintTimer = setTimeout(() => setWakingHint(true), 8000)

    const result = await login(email, password)
    clearTimeout(hintTimer)

    if (result.success) {
      toast.success('Welcome back! 🎉')
      navigate('/')
    } else {
      toast.error(result.error)
    }

    setLoading(false)
    setWakingHint(false)
  }

  const features = [
    { icon: TrendingUp, text: 'Smart Analytics', color: 'from-blue-500 to-cyan-500' },
    { icon: Shield, text: 'Secure & Private', color: 'from-indigo-500 to-purple-500' },
    { icon: Zap, text: 'Lightning Fast', color: 'from-purple-500 to-pink-500' }
  ]

  return (
    <div className="auth-page min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <button
        type="button"
        onClick={toggleTheme}
        className="theme-toggle absolute right-4 top-4 z-20 rounded-xl p-3 shadow-lg transition-colors hover:opacity-80"
        aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
        title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      >
        {isDark ? <Sun size={20} /> : <Moon size={20} />}
      </button>
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 90, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            rotate: [90, 0, 90],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "linear"
          }}
          className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-full blur-3xl"
        />
      </div>

      <div className="w-full max-w-6xl grid lg:grid-cols-2 gap-8 relative z-10">
        {/* Left Side - Features */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="hidden lg:flex flex-col justify-center space-y-8"
        >
          <div>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="inline-flex items-center gap-3 mb-6"
            >
              <div className="w-16 h-16 bg-gradient-to-br from-white/20 to-white/5 backdrop-blur-xl rounded-2xl flex items-center justify-center border border-white/20">
                <DollarSign className="w-10 h-10 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold">FinanceAI</h1>
                <p className="auth-muted">Smart Financial Management</p>
              </div>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-5xl font-bold mb-4 leading-tight"
            >
              Manage Your Finances
              <span className="block bg-gradient-to-r from-cyan-400 to-pink-400 bg-clip-text text-transparent">
                Like Never Before
              </span>
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="auth-muted text-lg mb-8"
            >
              AI-powered insights, automated categorization, and intelligent analytics for your financial data.
            </motion.p>
          </div>

          <div className="space-y-4">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
                className="auth-feature flex items-center gap-4 p-4 backdrop-blur-xl rounded-2xl"
              >
                <div className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-lg font-semibold">{feature.text}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Right Side - Login Form */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center justify-center"
        >
          <div className="auth-card w-full max-w-md backdrop-blur-xl rounded-3xl p-10">
            {/* Mobile Logo */}
            <div className="lg:hidden text-center mb-8">
              <motion.div
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: "spring", duration: 0.8 }}
                className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-lg mb-3"
              >
                <DollarSign className="w-10 h-10 text-white" />
              </motion.div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                FinanceAI
              </h1>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <h2 className="auth-title text-3xl font-bold mb-2">Welcome Back</h2>
              <p className="auth-muted mb-8">Login to access your financial dashboard</p>
            </motion.div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Input
                  type="email"
                  autoComplete="email"
                  label="Email Address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  icon={Mail}
                  iconPosition="left"
                  placeholder="you@example.com"
                  fullWidth
                  required
                />
              </motion.div>

              {/* Password */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Input
                  type="password"
                  autoComplete="current-password"
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  icon={Lock}
                  iconPosition="left"
                  placeholder="••••••••"
                  fullWidth
                  required
                />
              </motion.div>

              {/* Submit Button */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="mt-6"
              >
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={loading}
                  icon={LogIn}
                  iconPosition="left"
                  fullWidth
                >
                  {loading ? 'Logging in...' : 'Login to Dashboard'}
                </Button>
                {loading && wakingHint && (
                  <p className="text-center text-xs text-indigo-300 mt-3">
                    ⏳ Waking up the server (it sleeps when idle) — this can take up to a minute on first visit.
                  </p>
                )}
              </motion.div>
            </form>

            {/* Signup Link */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="auth-muted text-center text-sm mt-8"
            >
              Don't have an account?{' '}
              <Link to="/signup" className="whitespace-nowrap text-indigo-400 hover:text-indigo-300 font-bold transition-colors">
                Sign up for free →
              </Link>
            </motion.p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Login
