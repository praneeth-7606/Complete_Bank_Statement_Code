import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import { 
  Sparkles, FileText, CreditCard, Receipt, Shield, TrendingUp, Brain, Zap,
  CheckCircle, ArrowRight, BarChart3, MessageSquare, Upload, DollarSign,
  PieChart, Calendar, Lock, Cpu, Target, Users, Clock, Activity, Eye,
  Database, Search, ChevronDown, ChevronUp, Play
} from 'lucide-react'

const Home = () => {
  const [expandedFaq, setExpandedFaq] = useState(null)

  // Trust indicators
  const trustLogos = [
    { name: 'User 1', avatar: '👤' },
    { name: 'User 2', avatar: '👥' },
    { name: 'User 3', avatar: '🧑' },
    { name: 'User 4', avatar: '👨' },
  ]

  // Stats for ribbon
  const stats = [
    { icon: FileText, value: '10K+', label: 'Statements Processed', color: 'from-blue-500 to-cyan-500' },
    { icon: Target, value: '99.9%', label: 'Accuracy Rate', color: 'from-purple-500 to-pink-500' },
    { icon: Zap, value: '<2s', label: 'Average Processing Time', color: 'from-green-500 to-emerald-500' },
    { icon: MessageSquare, value: '24/7', label: 'AI Support', color: 'from-orange-500 to-red-500' }
  ]

  // How it works steps
  const steps = [
    {
      number: '01',
      title: 'Upload Your Statements',
      description: 'Drag and drop any financial document - bank statements, credit cards, EMI, or policy documents. Password-protected PDFs supported.',
      icon: Upload,
      preview: '📄'
    },
    {
      number: '02',
      title: 'AI Extracts & Categorizes Transactions',
      description: 'Our AI engine processes your document, extracts transactions, and automatically categorizes spending with 99.9% accuracy.',
      icon: Brain,
      preview: '🤖'
    },
    {
      number: '03',
      title: 'Get Dashboards, Insights & Chat Support',
      description: 'Access powerful analytics, real-time insights, and chat with your AI assistant about your finances anytime.',
      icon: BarChart3,
      preview: '📊'
    }
  ]

  // Document types
  const documentTypes = [
    {
      icon: FileText,
      title: 'Bank Statements',
      description: 'Extract transactions, balances, and account activity from any bank statement',
      color: 'from-blue-500 to-cyan-500',
      badge: 'Most Popular',
      badgeColor: 'bg-blue-500'
    },
    {
      icon: CreditCard,
      title: 'Credit Card Statements',
      description: 'Analyze spending patterns, track rewards, and monitor credit utilization',
      color: 'from-purple-500 to-pink-500',
      badge: 'Popular',
      badgeColor: 'bg-purple-500'
    },
    {
      icon: Receipt,
      title: 'EMI Statements',
      description: 'Track loan payments, monitor EMI schedules, and manage debt efficiently',
      color: 'from-green-500 to-emerald-500',
      badge: null
    },
    {
      icon: Shield,
      title: 'Policy Statements',
      description: 'Keep track of insurance policies, premiums, coverage, and renewal dates',
      color: 'from-orange-500 to-red-500',
      badge: 'New',
      badgeColor: 'bg-orange-500'
    }
  ]

  // AI Capabilities
  const capabilities = [
    { icon: Brain, title: 'AI-Powered Analysis', description: 'Advanced ML algorithms understand your financial patterns', badge: 'AI' },
    { icon: Zap, title: 'Instant Processing', description: 'Process statements in under 2 seconds with real-time updates', badge: 'Speed' },
    { icon: TrendingUp, title: 'Smart Insights', description: 'Get personalized recommendations to optimize your finances', badge: 'AI' },
    { icon: Lock, title: 'Bank-Level Security', description: 'End-to-end encryption with industry-standard protection', badge: 'Security' },
    { icon: Cpu, title: 'Automated Categorization', description: 'Intelligent transaction categorization with 99.9% accuracy', badge: 'AI' },
    { icon: Target, title: 'Goal Tracking', description: 'Set financial goals and track progress with visual insights', badge: 'Speed' }
  ]

  // AI Insights examples
  const aiInsights = [
    { text: 'Your highest spending category this month is Dining & Entertainment at ₹12,450', icon: TrendingUp, color: 'from-red-500 to-orange-500' },
    { text: 'You saved 23% compared to last month - great job!', icon: CheckCircle, color: 'from-green-500 to-emerald-500' },
    { text: 'Recurring subscription of ₹999 detected - Netflix Premium', icon: Calendar, color: 'from-blue-500 to-cyan-500' },
    { text: 'Your average daily spending is ₹1,247 this week', icon: BarChart3, color: 'from-purple-500 to-pink-500' }
  ]

  // FAQ items
  const faqs = [
    {
      question: 'Which banks and financial institutions are supported?',
      answer: 'FinanceAI supports statements from all major banks, credit card providers, and financial institutions. Our AI can process any standard PDF statement format, including password-protected files.'
    },
    {
      question: 'How are password-protected PDFs handled?',
      answer: 'You can securely provide the password during upload. The password is used only to decrypt the PDF in memory and is never stored. All processing happens securely on our servers with bank-level encryption.'
    },
    {
      question: 'What happens to my data after processing?',
      answer: 'Your data is encrypted at rest and in transit. You have full control - you can delete your statements and data anytime. We never share your financial information with third parties.'
    },
    {
      question: 'Is there a limit on the number of statements I can upload?',
      answer: 'Free users can upload up to 10 statements per month. Premium users get unlimited uploads, priority processing, and advanced analytics features.'
    },
    {
      question: 'How accurate is the AI extraction?',
      answer: 'Our AI achieves 99.9% accuracy in transaction extraction and categorization. You can review and correct any transactions through our intuitive corrections interface.'
    },
    {
      question: 'Can I export my data?',
      answer: 'Yes! You can export your transactions and analytics to CSV, Excel, or PDF formats anytime. Your data is always accessible and portable.'
    }
  ]

  return (
    <div className="space-y-0">

      {/* HERO SECTION */}
      <section className="relative overflow-hidden py-12 sm:py-16 md:py-24 lg:py-32">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 opacity-10"></div>
        <div className="absolute inset-0">
          <div className="absolute top-0 left-0 w-48 h-48 sm:w-72 sm:h-72 lg:w-96 lg:h-96 bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
          <div className="absolute bottom-0 right-0 w-48 h-48 sm:w-72 sm:h-72 lg:w-96 lg:h-96 bg-pink-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/2 w-48 h-48 sm:w-72 sm:h-72 lg:w-96 lg:h-96 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '2s' }}></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-10 lg:gap-12 items-center">
            {/* Left: Hero Content */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: "spring" }}
                className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 backdrop-blur-sm px-4 py-2 rounded-full mb-6 border border-indigo-200"
              >
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span className="text-sm font-semibold text-indigo-900">AI-Powered Financial Intelligence</span>
              </motion.div>

              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-gray-900 mb-4 sm:mb-6 leading-tight">
                Transform Your
                <br />
                <span className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                  Financial Data
                </span>
              </h1>

              <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-gray-600 mb-6 sm:mb-8 leading-relaxed">
                Upload any financial statement and get instant AI-powered insights. Bank statements, credit cards, EMIs, policies - we handle it all.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <Link to="/upload">
                  <motion.button
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="group px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl transition-all flex items-center gap-3 justify-center"
                  >
                    <Upload className="w-6 h-6" />
                    Upload Statement
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </motion.button>
                </Link>
                <Link to="/chat">
                  <motion.button
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 bg-white text-indigo-600 rounded-2xl font-bold text-lg border-2 border-indigo-200 hover:border-indigo-300 shadow-lg hover:shadow-xl transition-all flex items-center gap-3 justify-center"
                  >
                    <MessageSquare className="w-6 h-6" />
                    Try AI Assistant
                  </motion.button>
                </Link>
              </div>

              {/* Trust indicators */}
              <div className="flex items-center gap-4">
                <div className="flex -space-x-2">
                  {trustLogos.map((user, i) => (
                    <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white border-2 border-white shadow-lg">
                      {user.avatar}
                    </div>
                  ))}
                </div>
                <div className="text-sm">
                  <div className="font-semibold text-gray-900">Trusted by thousands</div>
                  <div className="text-gray-600">Join 10,000+ users</div>
                </div>
              </div>
            </motion.div>

            {/* Right: Product Preview Cards */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative w-full h-auto sm:h-[400px] md:h-[500px] lg:h-[600px] hidden sm:block"
            >
              {/* Upload Card - Top */}
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-0 right-0 w-full sm:w-72 md:w-80 bg-white/80 backdrop-blur-xl rounded-2xl sm:rounded-3xl shadow-xl sm:shadow-2xl border border-gray-200 p-4 sm:p-6 z-30"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                    <Upload className="w-5 h-5 text-white" />
                  </div>
                  <div className="font-bold text-gray-900">Upload Statement</div>
                </div>
                <div className="border-2 border-dashed border-indigo-300 rounded-2xl p-6 bg-indigo-50/50 mb-3">
                  <div className="text-center">
                    <FileText className="w-8 h-8 text-indigo-600 mx-auto mb-2" />
                    <div className="text-sm text-gray-600">Drop PDF here</div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs">
                    <Lock className="w-4 h-4 text-gray-400" />
                    <input type="password" placeholder="PDF Password (optional)" className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-xs" />
                  </div>
                </div>
              </motion.div>

              {/* Log Viewer Card - Middle */}
              <motion.div
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                className="absolute top-24 sm:top-32 left-0 w-full sm:w-72 md:w-80 bg-white/80 backdrop-blur-xl rounded-2xl sm:rounded-3xl shadow-xl sm:shadow-2xl border border-gray-200 p-4 sm:p-6 z-20"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-white" />
                    </div>
                    <div className="font-bold text-gray-900">Processing</div>
                  </div>
                  <div className="flex items-center gap-1 px-2 py-1 bg-green-100 rounded-full">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-semibold text-green-700">Live</span>
                  </div>
                </div>
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex gap-2"><span className="text-blue-600">[INFO]</span> <span className="text-gray-600">Extracting text...</span></div>
                  <div className="flex gap-2"><span className="text-green-600">[SUCCESS]</span> <span className="text-gray-600">Found 45 transactions</span></div>
                  <div className="flex gap-2"><span className="text-blue-600">[INFO]</span> <span className="text-gray-600">Categorizing...</span></div>
                  <div className="flex gap-2"><span className="text-green-600">[SUCCESS]</span> <span className="text-gray-600">Analysis complete</span></div>
                </div>
              </motion.div>

              {/* Analytics Card - Bottom */}
              <motion.div
                animate={{ y: [0, -15, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                className="absolute bottom-0 right-0 sm:right-8 w-full sm:w-64 md:w-72 bg-white/80 backdrop-blur-xl rounded-2xl sm:rounded-3xl shadow-xl sm:shadow-2xl border border-gray-200 p-4 sm:p-6 z-10"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-white" />
                  </div>
                  <div className="font-bold text-gray-900">Analytics</div>
                </div>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-3">
                    <div className="text-xs text-gray-600 mb-1">Income</div>
                    <div className="text-lg font-bold text-blue-600">₹45.2K</div>
                  </div>
                  <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-3">
                    <div className="text-xs text-gray-600 mb-1">Expenses</div>
                    <div className="text-lg font-bold text-red-600">₹32.8K</div>
                  </div>
                </div>
                <div className="h-20 bg-gradient-to-r from-indigo-100 via-purple-100 to-pink-100 rounded-xl flex items-end justify-around p-2">
                  {[40, 65, 45, 80, 55, 70].map((h, i) => (
                    <div key={i} className="w-6 bg-gradient-to-t from-indigo-500 to-purple-500 rounded-t" style={{ height: `${h}%` }}></div>
                  ))}
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* VALUE STATS RIBBON */}
      <section className="py-12 bg-white/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat, index) => {
              const Icon = stat.icon
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ y: -5, scale: 1.02 }}
                  className="relative group"
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${stat.color} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity`}></div>
                  <div className="relative bg-white/80 backdrop-blur-sm rounded-2xl p-6 border border-gray-200 shadow-lg hover:shadow-xl transition-all">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mb-4 shadow-lg`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent mb-2">
                      {stat.value}
                    </div>
                    <div className="text-sm text-gray-600 font-medium">{stat.label}</div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Get started in three simple steps and unlock powerful financial insights
            </p>
          </motion.div>

          <div className="space-y-12">
            {steps.map((step, index) => {
              const Icon = step.icon
              const isEven = index % 2 === 0
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: isEven ? -50 : 50 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.2 }}
                  className={`flex flex-col ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'} gap-8 items-center`}
                >
                  {/* Step Card */}
                  <div className="flex-1 relative">
                    <div className="absolute -top-6 -left-6 text-8xl font-bold text-indigo-100 z-0">
                      {step.number}
                    </div>
                    <div className="relative bg-white rounded-3xl p-8 shadow-xl border border-gray-200 hover:shadow-2xl transition-all">
                      <div className="flex items-start gap-4 mb-4">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                          <Icon className="w-7 h-7 text-white" />
                        </div>
                        <div>
                          <h3 className="text-2xl font-bold text-gray-900 mb-2">{step.title}</h3>
                          <p className="text-gray-600 leading-relaxed">{step.description}</p>
                        </div>
                      </div>
                      {index < steps.length - 1 && (
                        <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 w-0.5 h-12 bg-gradient-to-b from-indigo-300 to-transparent hidden lg:block"></div>
                      )}
                    </div>
                  </div>

                  {/* Preview */}
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-9xl">{step.preview}</div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* DOCUMENT TYPES GRID */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Analyze Any Financial Document
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Our AI understands multiple types of financial statements and extracts meaningful insights from each
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {documentTypes.map((doc, index) => {
              const Icon = doc.icon
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ y: -10, scale: 1.02 }}
                  className="relative group"
                >
                  {/* Glow effect on hover */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${doc.color} opacity-0 group-hover:opacity-20 rounded-2xl blur-xl transition-opacity`}></div>
                  
                  <div className="relative bg-white rounded-2xl p-6 border-2 border-gray-200 group-hover:border-transparent shadow-lg hover:shadow-2xl transition-all">
                    {doc.badge && (
                      <div className={`absolute top-4 right-4 ${doc.badgeColor} text-white text-xs font-bold px-3 py-1 rounded-full`}>
                        {doc.badge}
                      </div>
                    )}
                    <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${doc.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-3">{doc.title}</h3>
                    <p className="text-gray-600 text-sm leading-relaxed">{doc.description}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* AI CAPABILITIES GRID */}
      <section className="py-20 bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Powerful AI Capabilities
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Built with cutting-edge technology to give you the best financial insights
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((capability, index) => {
              const Icon = capability.icon
              const badgeColors = {
                'AI': 'bg-purple-500',
                'Speed': 'bg-green-500',
                'Security': 'bg-blue-500'
              }
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ y: -5 }}
                  className="relative bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all border border-gray-200"
                >
                  <div className={`absolute top-4 right-4 ${badgeColors[capability.badge]} text-white text-xs font-bold px-2 py-1 rounded-full`}>
                    {capability.badge}
                  </div>
                  <div className="flex gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 mb-2">{capability.title}</h3>
                      <p className="text-gray-600 text-sm leading-relaxed">{capability.description}</p>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* REAL-TIME PROCESSING SPLIT SECTION */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Explainer */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                Real-Time Processing
                <br />
                <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  & Live Logs
                </span>
              </h2>
              <p className="text-xl text-gray-600 mb-6 leading-relaxed">
                Watch your statements being processed in real-time with our live log streaming. Every step is transparent, from text extraction to AI categorization.
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Background Task Processing</div>
                    <div className="text-gray-600">Asynchronous processing ensures fast, reliable results</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">99.9% Accuracy</div>
                    <div className="text-gray-600">Advanced AI models trained on millions of transactions</div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Instant Feedback</div>
                    <div className="text-gray-600">See progress updates as they happen</div>
                  </div>
                </div>
              </div>

              {/* Processing Status Mini Card */}
              <div className="mt-8 bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-6 border border-green-200">
                <div className="flex items-center gap-3 mb-4">
                  <Activity className="w-5 h-5 text-green-600" />
                  <div className="font-bold text-gray-900">Processing Status</div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Extraction</span>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Database Save</span>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Vector Indexing</span>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-green-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-xs text-green-600">In Progress</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Right: Log Viewer Mock */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-gray-200 p-6 h-[600px] flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-white" />
                    </div>
                    <div className="font-bold text-gray-900">Live Processing Logs</div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-full">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-semibold text-green-700">Live</span>
                  </div>
                </div>

                <div className="flex-1 bg-gray-900 rounded-2xl p-4 overflow-hidden font-mono text-sm">
                  <div className="space-y-2">
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Starting document processing...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.7 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Extracting text from PDF...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.9 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Extracted 2,847 characters</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.1 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Detecting statement type...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.3 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Detected: Bank Statement</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.5 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Extracting transactions...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.7 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Found 45 transactions</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.9 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Running AI categorization...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 2.1 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Categorized all transactions</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 2.3 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Saving to database...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 2.5 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Database save complete</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 2.7 }}
                      className="flex gap-2"
                    >
                      <span className="text-blue-400">[INFO]</span>
                      <span className="text-gray-300">Creating vector embeddings...</span>
                    </motion.div>
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 2.9 }}
                      className="flex gap-2"
                    >
                      <span className="text-green-400">[SUCCESS]</span>
                      <span className="text-gray-300">Processing complete! ✨</span>
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ANALYTICS & DASHBOARD PREVIEW */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Powerful Analytics At a Glance
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Visualize your financial data with beautiful charts and get AI-powered insights
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-2 gap-12 items-start">
            {/* Left: Analytics Dashboard Mock */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white rounded-3xl shadow-2xl border border-gray-200 p-8"
            >
              {/* KPI Strip */}
              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign className="w-5 h-5 text-blue-600" />
                    <span className="text-sm text-gray-600">Total Balance</span>
                  </div>
                  <div className="text-2xl font-bold text-blue-600">₹12,450</div>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-5 h-5 text-green-600" />
                    <span className="text-sm text-gray-600">Total Income</span>
                  </div>
                  <div className="text-2xl font-bold text-green-600">₹45,200</div>
                </div>
                <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-5 h-5 text-red-600 rotate-180" />
                    <span className="text-sm text-gray-600">Total Expenses</span>
                  </div>
                  <div className="text-2xl font-bold text-red-600">₹32,750</div>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-5 h-5 text-purple-600" />
                    <span className="text-sm text-gray-600">Transactions</span>
                  </div>
                  <div className="text-2xl font-bold text-purple-600">156</div>
                </div>
              </div>

              {/* Charts */}
              <div className="space-y-6">
                {/* Pie Chart */}
                <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Spending by Category
                  </h3>
                  <div className="flex items-center justify-center">
                    <div className="relative w-48 h-48">
                      <svg viewBox="0 0 100 100" className="transform -rotate-90">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#e0e7ff" strokeWidth="20" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#6366f1" strokeWidth="20" strokeDasharray="75 251" strokeDashoffset="0" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#ec4899" strokeWidth="20" strokeDasharray="50 251" strokeDashoffset="-75" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#10b981" strokeWidth="20" strokeDasharray="40 251" strokeDashoffset="-125" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#f59e0b" strokeWidth="20" strokeDasharray="86 251" strokeDashoffset="-165" />
                      </svg>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-indigo-500"></div>
                      <span className="text-gray-600">Food 30%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-pink-500"></div>
                      <span className="text-gray-600">Shopping 20%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <span className="text-gray-600">Transport 16%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                      <span className="text-gray-600">Other 34%</span>
                    </div>
                  </div>
                </div>

                {/* Bar Chart */}
                <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl p-6">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Monthly Trend
                  </h3>
                  <div className="h-32 flex items-end justify-around gap-2">
                    {[65, 45, 80, 55, 70, 85].map((height, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-2">
                        <div className="w-full bg-gradient-to-t from-indigo-500 to-purple-500 rounded-t-lg transition-all hover:from-indigo-600 hover:to-purple-600" style={{ height: `${height}%` }}></div>
                        <span className="text-xs text-gray-600">M{i + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Right: AI Insights */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="space-y-6"
            >
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">AI-Powered Insights</h3>
                <p className="text-gray-600 mb-6">
                  Get personalized recommendations and insights based on your spending patterns
                </p>

                {/* Filter Tags */}
                <div className="flex flex-wrap gap-2 mb-6">
                  {['Overview', 'Spending', 'Income', 'Savings'].map((tag, i) => (
                    <button
                      key={i}
                      className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${
                        i === 0
                          ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg'
                          : 'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300'
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Insight Cards */}
              <div className="space-y-4">
                {aiInsights.map((insight, index) => {
                  const Icon = insight.icon
                  return (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: index * 0.1 }}
                      whileHover={{ x: 5 }}
                      className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200 hover:shadow-xl transition-all"
                    >
                      <div className="flex gap-4">
                        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${insight.color} flex items-center justify-center flex-shrink-0 shadow-lg`}>
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <p className="text-gray-700 leading-relaxed">{insight.text}</p>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* AI CHAT PREVIEW */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left: Chat Interface Mock */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white rounded-3xl shadow-2xl border border-gray-200 p-6 h-[600px] flex flex-col"
            >
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-200">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-bold text-gray-900">AI Financial Assistant</div>
                  <div className="text-sm text-green-600 flex items-center gap-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    Online
                  </div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 space-y-4 overflow-y-auto mb-4">
                {/* User Message */}
                <div className="flex justify-end">
                  <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-xs">
                    <p className="text-sm">Show my biggest recurring expenses</p>
                  </div>
                </div>

                {/* AI Response */}
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-md">
                    <p className="text-sm text-gray-700 mb-3">
                      Here are your top recurring expenses:
                    </p>
                    <div className="space-y-2">
                      <div className="bg-white rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <div className="font-semibold text-gray-900 text-sm">Netflix Premium</div>
                          <div className="text-xs text-gray-500">Monthly subscription</div>
                        </div>
                        <div className="text-sm font-bold text-red-600">₹999</div>
                      </div>
                      <div className="bg-white rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <div className="font-semibold text-gray-900 text-sm">Gym Membership</div>
                          <div className="text-xs text-gray-500">Monthly subscription</div>
                        </div>
                        <div className="text-sm font-bold text-red-600">₹2,500</div>
                      </div>
                      <div className="bg-white rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <div className="font-semibold text-gray-900 text-sm">Internet Bill</div>
                          <div className="text-xs text-gray-500">Monthly utility</div>
                        </div>
                        <div className="text-sm font-bold text-red-600">₹1,299</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* User Message */}
                <div className="flex justify-end">
                  <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-xs">
                    <p className="text-sm">How much did I save last month?</p>
                  </div>
                </div>

                {/* AI Response */}
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-md">
                    <p className="text-sm text-gray-700">
                      Great question! Last month you saved <span className="font-bold text-green-600">₹12,450</span>, which is 23% more than the previous month. Keep up the good work! 🎉
                    </p>
                  </div>
                </div>
              </div>

              {/* Suggested Questions */}
              <div className="mb-4">
                <div className="text-xs text-gray-500 mb-2">Suggested questions:</div>
                <div className="flex flex-wrap gap-2">
                  {['Show spending trends', 'Budget recommendations', 'Upcoming bills'].map((q, i) => (
                    <button key={i} className="px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-full text-xs font-medium hover:bg-indigo-100 transition-colors">
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Ask anything about your finances..."
                  className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <button className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all">
                  Send
                </button>
              </div>
            </motion.div>

            {/* Right: Features */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                Chat With Your
                <br />
                <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  Finances
                </span>
              </h2>
              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                Ask questions in natural language and get instant insights about your financial data
              </p>

              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                    <MessageSquare className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-2">Natural Language Queries</h3>
                    <p className="text-gray-600">Ask questions like you would to a financial advisor - no complex commands needed</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                    <Database className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-2">Uses Your Data</h3>
                    <p className="text-gray-600">AI assistant has access to all your statements and transactions for accurate answers</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                    <Clock className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900 mb-2">Available 24/7</h3>
                    <p className="text-gray-600">Get instant answers anytime, anywhere - your AI assistant never sleeps</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* SECURITY & TRUST SECTION */}
      <section className="py-20 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Your Security is Our Priority
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              We use industry-leading security measures to protect your financial data
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0 }}
              className="bg-white/80 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-200 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mx-auto mb-6 shadow-lg">
                <Lock className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Bank-Level Encryption</h3>
              <p className="text-gray-600 leading-relaxed">
                All data is encrypted using AES-256 encryption, the same standard used by banks and financial institutions
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="bg-white/80 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-200 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mx-auto mb-6 shadow-lg">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Data Privacy & Security</h3>
              <p className="text-gray-600 leading-relaxed">
                Your data is never shared with third parties. You have full control and can delete your data anytime
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="bg-white/80 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-200 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mx-auto mb-6 shadow-lg">
                <Eye className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Transparent Processing</h3>
              <p className="text-gray-600 leading-relaxed">
                Watch your data being processed in real-time with our live log viewer. Complete transparency at every step
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* FAQ SECTION */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-600">
              Everything you need to know about FinanceAI
            </p>
          </motion.div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-2xl border border-gray-200 overflow-hidden hover:shadow-lg transition-all"
              >
                <button
                  onClick={() => setExpandedFaq(expandedFaq === index ? null : index)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="font-semibold text-gray-900 pr-4">{faq.question}</span>
                  {expandedFaq === index ? (
                    <ChevronUp className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  )}
                </button>
                {expandedFaq === index && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="px-6 pb-5"
                  >
                    <p className="text-gray-600 leading-relaxed">{faq.answer}</p>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 p-12 md:p-16 text-center"
          >
            {/* Animated background elements */}
            <div className="absolute inset-0 opacity-20">
              <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse"></div>
              <div className="absolute bottom-0 right-0 w-96 h-96 bg-pink-300 rounded-full mix-blend-overlay filter blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
            </div>

            <div className="relative z-10">
              <motion.div
                initial={{ scale: 0 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{ type: "spring" }}
                className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full mb-6"
              >
                <Sparkles className="w-5 h-5 text-yellow-300" />
                <span className="text-white font-semibold">Start Your Financial Journey Today</span>
              </motion.div>

              <h2 className="text-4xl md:text-6xl font-bold text-white mb-6">
                Ready to Get Started?
              </h2>
              <p className="text-xl md:text-2xl text-white/90 mb-10 max-w-3xl mx-auto leading-relaxed">
                Join thousands of users who are already managing their finances smarter with AI
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/upload">
                  <motion.button
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="group px-8 py-4 bg-white text-indigo-600 rounded-2xl font-bold text-lg shadow-2xl hover:shadow-3xl transition-all flex items-center gap-3 justify-center"
                  >
                    <Upload className="w-6 h-6" />
                    Upload Your First Statement
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </motion.button>
                </Link>
                <Link to="/chat">
                  <motion.button
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 bg-white/10 backdrop-blur-lg text-white rounded-2xl font-bold text-lg border-2 border-white/30 hover:bg-white/20 transition-all flex items-center gap-3 justify-center"
                  >
                    <MessageSquare className="w-6 h-6" />
                    Try AI Assistant
                  </motion.button>
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Floating Upload FAB */}
      <Link to="/upload">
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-full shadow-2xl hover:shadow-3xl transition-all flex items-center justify-center z-50"
        >
          <Upload className="w-7 h-7" />
        </motion.button>
      </Link>
    </div>
  )
}

export default Home
