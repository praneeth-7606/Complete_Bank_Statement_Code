import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Sparkles, TrendingUp, DollarSign, PieChart, Calendar, Zap, Brain, MessageCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { chatAPI } from '../services/api'
import RAGResponseFormatter from '../components/chat/RAGResponseFormatter'

const Chat = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hello! I\'m your AI-powered financial assistant. I can help you analyze your transactions, understand spending patterns, and provide personalized financial insights. What would you like to know?',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await chatAPI.sendQuery(input)
      
      const assistantMessage = {
        role: 'assistant',
        content: response.answer || 'I apologize, but I couldn\'t generate a response.',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
      toast.error('Failed to get response from AI')
      
      const errorMessage = {
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const suggestedQuestions = [
    { icon: TrendingUp, text: 'Show me my spending trends', color: 'from-blue-500 to-cyan-500' },
    { icon: DollarSign, text: 'What are my total expenses?', color: 'from-green-500 to-emerald-500' },
    { icon: PieChart, text: 'Break down expenses by category', color: 'from-purple-500 to-pink-500' },
    { icon: Calendar, text: 'Show transactions from last month', color: 'from-orange-500 to-red-500' },
    { icon: Zap, text: 'Where can I save money?', color: 'from-yellow-500 to-orange-500' },
    { icon: Brain, text: 'Give me financial insights', color: 'from-indigo-500 to-purple-500' },
  ]

  const handleSuggestedQuestion = (question) => {
    setInput(question)
  }

  return (
    <div className="h-[calc(100vh-8rem)] sm:h-[calc(100vh-10rem)] flex flex-col">
      {/* Chat Header - Enhanced */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-xl sm:rounded-2xl mb-4 sm:mb-6 shadow-lg sm:shadow-2xl"
      >
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600"></div>
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-0 w-40 h-40 sm:w-72 sm:h-72 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse"></div>
          <div className="absolute bottom-0 right-0 w-40 h-40 sm:w-72 sm:h-72 bg-pink-300 rounded-full mix-blend-overlay filter blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        </div>
        
        {/* Content */}
        <div className="relative p-4 sm:p-6 lg:p-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
              <motion.div 
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="w-12 h-12 sm:w-16 sm:h-16 bg-white/20 backdrop-blur-lg rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg sm:shadow-2xl border border-white/30 flex-shrink-0"
              >
                <Sparkles className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
              </motion.div>
              <div className="min-w-0">
                <h2 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-0.5 sm:mb-1 flex items-center gap-2 flex-wrap">
                  AI Financial Assistant
                  <motion.span
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    ✨
                  </motion.span>
                </h2>
                <p className="text-white/90 text-xs sm:text-sm truncate">Powered by advanced AI • Real-time insights • Smart analysis</p>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2 bg-white/20 backdrop-blur-lg px-3 sm:px-4 py-1.5 sm:py-2 rounded-full border border-white/30 flex-shrink-0">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-white text-xs sm:text-sm font-medium">Online</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Messages Container - Enhanced */}
      <div className="relative flex-1 flex flex-col overflow-hidden rounded-xl sm:rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 shadow-lg sm:shadow-xl border border-gray-200">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 space-y-4 sm:space-y-6">
          <AnimatePresence>
            {messages.map((message, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20, scale: 0.95 }}
                transition={{ delay: index * 0.05, type: "spring", stiffness: 200 }}
                className={`flex gap-4 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <motion.div 
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  className={`w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-lg sm:rounded-xl lg:rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500' 
                      : 'bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-white" />
                  )}
                </motion.div>
                
                {/* Message Bubble */}
                <div className={`flex-1 max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg ${
                  message.role === 'user' ? 'text-right' : 'text-left'
                }`}>
                  {message.role === 'user' ? (
                    <motion.div 
                      whileHover={{ scale: 1.02 }}
                      className="inline-block p-3 sm:p-4 lg:p-5 rounded-lg sm:rounded-xl lg:rounded-2xl shadow-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-white"
                    >
                      <div className="whitespace-pre-wrap text-xs sm:text-sm lg:text-base leading-relaxed">
                        {message.content}
                      </div>
                    </motion.div>
                  ) : (
                    <div className="space-y-2">
                      <RAGResponseFormatter 
                        response={typeof message.content === 'string' ? { data: { answer: message.content } } : message.content}
                        loading={false}
                      />
                    </div>
                  )}
                  <div className="flex items-center gap-1 sm:gap-2 mt-1 sm:mt-2 px-2">
                    <p className="text-xs text-gray-500">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                    {message.role === 'assistant' && (
                      <span className="text-xs text-gray-400 hidden sm:inline">• AI Response</span>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-4"
            >
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-xl">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="bg-white border-2 border-gray-100 rounded-2xl p-5 shadow-lg">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                  <div className="flex gap-1">
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                      className="w-2 h-2 bg-indigo-600 rounded-full"
                    />
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                      className="w-2 h-2 bg-purple-600 rounded-full"
                    />
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                      className="w-2 h-2 bg-pink-600 rounded-full"
                    />
                  </div>
                  <span className="text-sm text-gray-600">AI is thinking...</span>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions - Enhanced */}
        {messages.length === 1 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-4 sm:mb-6 p-4 sm:p-6 bg-white rounded-xl sm:rounded-2xl border-2 border-gray-200 shadow-lg"
          >
            <div className="flex items-center gap-2 mb-3 sm:mb-4">
              <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-600" />
              <p className="text-sm sm:text-base font-bold text-gray-900">Try asking me:</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
              {suggestedQuestions.map((question, index) => {
                const Icon = question.icon
                return (
                  <motion.button
                    key={index}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleSuggestedQuestion(question.text)}
                    className="group relative overflow-hidden text-left px-3 sm:px-4 py-3 sm:py-4 bg-gradient-to-br from-gray-50 to-white hover:from-white hover:to-gray-50 rounded-lg sm:rounded-xl transition-all border-2 border-gray-200 hover:border-indigo-300 shadow-sm hover:shadow-xl"
                  >
                    <div className={`absolute inset-0 bg-gradient-to-br ${question.color} opacity-0 group-hover:opacity-10 transition-opacity`}></div>
                    <div className="relative flex items-center gap-2 sm:gap-3">
                      <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br ${question.color} flex items-center justify-center shadow-md flex-shrink-0`}>
                        <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                      </div>
                      <span className="text-xs sm:text-sm font-medium text-gray-700 group-hover:text-gray-900 flex-1 line-clamp-2">
                        {question.text}
                      </span>
                    </div>
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Input Form - Enhanced */}
        <div className="p-3 sm:p-4 lg:p-6 bg-white border-t-2 border-gray-200">
          <form onSubmit={handleSubmit} className="space-y-2 sm:space-y-3">
            <div className="flex gap-2 sm:gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask me anything about your finances..."
                  className="w-full px-3 sm:px-4 lg:px-6 py-2.5 sm:py-3 lg:py-4 pr-10 sm:pr-12 rounded-lg sm:rounded-xl lg:rounded-2xl border-2 border-gray-300 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all text-xs sm:text-sm lg:text-base bg-gray-50 focus:bg-white placeholder-gray-500"
                  disabled={loading}
                  autoFocus
                />
                <Sparkles className="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400 pointer-events-none" />
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={loading || !input.trim()}
                className="px-3 sm:px-6 lg:px-8 py-2.5 sm:py-3 lg:py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg sm:rounded-xl lg:rounded-2xl font-semibold shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 sm:gap-2 whitespace-nowrap flex-shrink-0"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
                    <span className="hidden sm:inline text-xs lg:text-sm">Sending...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                    <span className="hidden sm:inline text-xs lg:text-sm">Send</span>
                  </>
                )}
              </motion.button>
            </div>
            <p className="text-xs text-gray-500 text-center">
              💡 Tip: Be specific with your questions for better insights
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Chat
