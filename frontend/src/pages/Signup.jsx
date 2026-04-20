import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, User, UserPlus, DollarSign, TrendingUp, Shield, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { GoogleLogin } from '@react-oauth/google'
import { Button, Input } from '../components/ui'

const Signup = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState(null)
  const { signup, googleLogin } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    setLoading(true)

    const result = await signup(email, password, fullName)

    if (result.success) {
      toast.success('Account created successfully!')
      navigate('/')
    } else {
      toast.error(result.error)
    }

    setLoading(false)
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true)

    const result = await googleLogin(credentialResponse.credential)

    if (result.success) {
      toast.success('Welcome to FinanceAI!')
      navigate('/')
    } else {
      toast.error(result.error)
    }

    setLoading(false)
  }

  const handleGoogleError = () => {
    toast.error('Google signup failed. Please try again.')
  }

  const features = [
    { icon: TrendingUp, text: 'Smart Analytics', color: 'from-blue-500 to-cyan-500' },
    { icon: Shield, text: 'Secure & Private', color: 'from-indigo-500 to-purple-500' },
    { icon: Zap, text: 'Lightning Fast', color: 'from-purple-500 to-pink-500' }
  ]

  return (
    <div className="min-h-screen bg-[#080810] flex items-center justify-center p-4 relative overflow-hidden">
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
          className="hidden lg:flex flex-col justify-center space-y-8 text-white"
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
                <p className="text-indigo-200">Smart Financial Management</p>
              </div>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-5xl font-bold mb-4 leading-tight"
            >
              Start Your Journey
              <span className="block bg-gradient-to-r from-cyan-400 to-pink-400 bg-clip-text text-transparent">
                To Financial Freedom
              </span>
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-lg text-indigo-200 mb-8"
            >
              Join thousands of users managing their finances smarter with AI-powered insights.
            </motion.p>
          </div>

          <div className="space-y-4">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
                className="flex items-center gap-4 p-4 bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20"
              >
                <div className={`w-12 h-12 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center`}>
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-lg font-semibold">{feature.text}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Right Side - Signup Form */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center justify-center"
        >
          <div className="w-full max-w-md bg-white/[0.03] backdrop-blur-xl rounded-3xl shadow-2xl p-10 border border-white/5">
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
              <h2 className="text-3xl font-bold text-white mb-2">Create Account</h2>
              <p className="text-gray-400 mb-8">Start managing your finances smarter</p>
            </motion.div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Full Name
                </label>
                <div className="relative group">
                  <User className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${focusedField === 'name' ? 'text-indigo-600' : 'text-gray-400'
                    }`} />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    onFocus={() => setFocusedField('name')}
                    onBlur={() => setFocusedField(null)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white/[0.02] border border-white/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all text-white placeholder-gray-500 hover:border-white/20"
                    placeholder="John Doe"
                    required
                    minLength={2}
                  />
                </div>
              </motion.div>

              {/* Email */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
              >
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Email Address
                </label>
                <div className="relative group">
                  <Mail className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${focusedField === 'email' ? 'text-indigo-600' : 'text-gray-400'
                    }`} />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onFocus={() => setFocusedField('email')}
                    onBlur={() => setFocusedField(null)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white/[0.02] border border-white/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all text-white placeholder-gray-500 hover:border-white/20"
                    placeholder="you@example.com"
                    required
                  />
                </div>
              </motion.div>

              {/* Password */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
              >
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Password
                </label>
                <div className="relative group">
                  <Lock className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${focusedField === 'password' ? 'text-indigo-600' : 'text-gray-400'
                    }`} />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setFocusedField('password')}
                    onBlur={() => setFocusedField(null)}
                    className="w-full pl-12 pr-4 py-3.5 bg-white/[0.02] border border-white/10 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all text-white placeholder-gray-500 hover:border-white/20"
                    placeholder="••••••••"
                    required
                    minLength={8}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2 font-medium">
                  ✓ Must be at least 8 characters
                </p>
              </motion.div>

              {/* Submit Button */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="mt-6"
              >
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={loading}
                  icon={UserPlus}
                  iconPosition="left"
                  fullWidth
                >
                  {loading ? 'Creating account...' : 'Create Account'}
                </Button>
              </motion.div>
            </form>

            {/* Google Signup - Only show if configured */}
            {import.meta.env.VITE_GOOGLE_CLIENT_ID && (
              <>
                <div className="relative my-8">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/10"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 bg-[#0a0a1a] text-gray-400 font-medium">Or continue with</span>
                  </div>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                  className="flex justify-center"
                >
                  <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={handleGoogleError}
                    theme="outline"
                    size="large"
                    text="signup_with"
                    shape="rectangular"
                  />
                </motion.div>
              </>
            )}

            {/* Login Link */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="text-center text-sm text-gray-400 mt-8"
            >
              Already have an account?{' '}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-bold transition-colors">
                Login here →
              </Link>
            </motion.p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Signup
