import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Sparkles, TrendingUp, DollarSign, PieChart, Calendar, Zap, Brain, MessageCircle, X, Mic, MicOff } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { chatAPI } from '../services/api'
import RAGResponseFormatter from '../components/chat/RAGResponseFormatter'
import { Button } from '../components/ui'

// Voice Recognition Imports
import 'regenerator-runtime/runtime'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

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

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
    isMicrophoneAvailable
  } = useSpeechRecognition()

  useEffect(() => {
    if (transcript) {
      console.log("Voice Transcript Incoming:", transcript);
      setInput(transcript)
    }
  }, [transcript])

  useEffect(() => {
    console.log("Speech Recognition Status:", listening ? "Listening" : "Inactive");
    console.log("Mic Available:", isMicrophoneAvailable);
    if (listening && !isMicrophoneAvailable) {
      toast.error("Microphone access denied")
    }
  }, [listening, isMicrophoneAvailable])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const toggleListening = () => {
    if (listening) {
      console.log("Stopping listening...");
      SpeechRecognition.stopListening()
    } else {
      console.log("Starting listening...");
      resetTranscript()
      SpeechRecognition.startListening({
        continuous: true,
        language: 'en-IN',
        interimResults: true
      })
    }
  }

  if (!browserSupportsSpeechRecognition) {
    console.warn("Browser doesn't support speech recognition.")
  }

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
      // Prep history for backend: map to {role: 'user'|'assistant', content: '...'}
      const history = messages.map(m => ({
        role: m.role,
        content: typeof m.content === 'string' ? m.content : (m.content?.data?.answer || "Financial Data")
      })).slice(-10) // Only send last 10 messages for token efficiency

      const response = await chatAPI.sendQuery(input, history)

      const assistantMessage = {
        role: 'assistant',
        content: response, // Store the entire metadata-rich object
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

  const clearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: '👋 History cleared. How can I help you now?',
        timestamp: new Date()
      }
    ])
    toast.success('Conversation history cleared')
  }

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col w-full py-4">
      {/* Chat Header - Enhanced */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-xl sm:rounded-2xl mb-4 sm:mb-6 shadow-2xl"
      >
        {/* Animated Background - Darker for better contrast */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary-700 via-primary-800 to-primary-900"></div>
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-40 h-40 sm:w-72 sm:h-72 bg-white rounded-full filter blur-3xl animate-pulse"></div>
          <div className="absolute bottom-0 right-0 w-40 h-40 sm:w-72 sm:h-72 bg-white rounded-full filter blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        </div>

        {/* Content */}
        <div className="relative p-6 sm:p-8 lg:p-10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex items-center gap-5 sm:gap-6 flex-1 min-w-0">
              <motion.div
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                className="w-16 h-16 sm:w-20 sm:h-20 bg-white/20 backdrop-blur-xl rounded-2xl sm:rounded-3xl flex items-center justify-center shadow-2xl border-2 border-white/40 flex-shrink-0"
              >
                <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
              </motion.div>
              <div className="min-w-0">
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white mb-1 sm:mb-2 flex items-center gap-3 flex-wrap tracking-tight drop-shadow-lg">
                  Financial Intelligence
                  <motion.span
                    animate={{ scale: [1, 1.2, 1], rotate: [0, 10, -10, 0] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  >
                    💎
                  </motion.span>
                </h2>
                <div className="flex items-center gap-3 text-white text-sm sm:text-base font-semibold">
                  <span className="flex items-center gap-1.5"><Brain className="w-4 h-4" /> Agentic RAG v2.0</span>
                  <span className="w-1.5 h-1.5 bg-white rounded-full"></span>
                  <span>Long-term Memory Enabled</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={clearChat}
                className="flex items-center gap-2 bg-white/20 hover:bg-white/30 backdrop-blur-lg px-4 py-2 rounded-xl border-2 border-white/30 transition-all text-white text-sm font-semibold shadow-lg"
              >
                <X className="w-4 h-4" /> Clear Session
              </button>
              <div className="hidden sm:flex items-center gap-2 bg-green-500 backdrop-blur-xl px-4 py-2 rounded-full border-2 border-green-400 shadow-xl">
                <div className="w-2.5 h-2.5 bg-white rounded-full animate-pulse shadow-[0_0_10px_rgba(255,255,255,0.8)]"></div>
                <span className="text-white text-sm font-bold tracking-wide">AI ALIVE</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Messages Container - Enhanced */}
      <div className="relative flex-1 flex flex-col overflow-hidden rounded-xl sm:rounded-2xl bg-white/70 backdrop-blur-md border border-white/40 shadow-2xl">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 space-y-4 sm:space-y-6">
          <AnimatePresence>
            {messages.map((message, index) => {
              const isAssistant = message.role === 'assistant';
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ delay: index * 0.05, type: "spring", stiffness: 200 }}
                  className={`flex gap-4 ${!isAssistant ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* Avatar */}
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    className={`w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 rounded-lg sm:rounded-xl lg:rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg ${!isAssistant
                      ? 'bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500'
                      : 'bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500'
                      }`}
                  >
                    {!isAssistant ? (
                      <User className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-white" />
                    )}
                  </motion.div>

                  {/* Message Bubble */}
                  <div className={`flex-1 max-w-[85%] sm:max-w-[80%] lg:max-w-[75%] ${!isAssistant ? 'text-right' : 'text-left'
                    }`}>
                    <div className={`inline-block p-4 sm:p-5 lg:p-6 rounded-2xl sm:rounded-3xl lg:rounded-[2rem] shadow-sm ${isAssistant
                      ? 'bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-tl-none'
                      : 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-tr-none'
                      }`}>
                      {isAssistant ? (
                        <RAGResponseFormatter
                          response={typeof message.content === 'string' ? { data: { answer: message.content } } : message.content}
                          loading={false}
                        />
                      ) : (
                        <div className="whitespace-pre-wrap text-sm sm:text-base lg:text-lg font-medium leading-relaxed tracking-tight">
                          {message.content}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2 mt-1 sm:mt-2 px-2">
                      <p className="text-xs text-[var(--text-secondary)]">
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                      {isAssistant && (
                        <span className="text-xs text-[var(--text-secondary)] hidden sm:inline">• AI Response</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )
            })}
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
              <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl p-5 shadow-lg">
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
                  <span className="text-sm text-[var(--text-secondary)]">AI is thinking...</span>
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
            className="mb-4 sm:mb-6 p-4 sm:p-6 bg-[var(--bg-card)] rounded-xl sm:rounded-2xl border border-[var(--border-subtle)] shadow-xl"
          >
            <div className="flex items-center gap-2 mb-3 sm:mb-4">
              <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-600" />
              <p className="text-sm sm:text-base font-bold text-[var(--text-primary)]">Try asking me:</p>
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
                    className="group relative overflow-hidden text-left px-3 sm:px-4 py-3 sm:py-4 bg-[var(--bg-surface)] hover:bg-[var(--bg-card)] rounded-lg sm:rounded-xl transition-all border border-[var(--border-subtle)] hover:border-indigo-500/30 shadow-sm"
                  >
                    <div className={`absolute inset-0 bg-gradient-to-br ${question.color} opacity-0 group-hover:opacity-10 transition-opacity`}></div>
                    <div className="relative flex items-center gap-2 sm:gap-3">
                      <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br ${question.color} flex items-center justify-center shadow-md flex-shrink-0`}>
                        <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                      </div>
                      <span className="text-xs sm:text-sm font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] flex-1 line-clamp-2">
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
        <div className="p-3 sm:p-4 lg:p-6 bg-[var(--bg-surface)] border-t border-[var(--border-subtle)]">
          <form onSubmit={handleSubmit} className="space-y-2 sm:space-y-3">
            <div className="flex gap-4 sm:gap-6 items-center">
              <div className="flex-1 relative group">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={listening ? "Listening... Speak now..." : "Ask me anything about your finances..."}
                  className="w-full px-6 sm:px-8 lg:px-10 py-4 sm:py-5 lg:py-6 pr-24 sm:pr-32 rounded-2xl sm:rounded-3xl lg:rounded-[2.5rem] border border-[var(--border-subtle)] focus:border-indigo-500 focus:ring-8 focus:ring-indigo-500/10 transition-all text-sm sm:text-base lg:text-lg bg-[var(--bg-card)] hover:bg-[var(--bg-surface)] focus:bg-[var(--bg-surface)] placeholder-[var(--text-secondary)] font-medium text-[var(--text-primary)]"
                  disabled={loading}
                  autoFocus
                />
                <div className="absolute right-6 sm:right-8 top-1/2 -translate-y-1/2 flex items-center gap-3">
                  {browserSupportsSpeechRecognition && (
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={toggleListening}
                      className={`p-2 rounded-full transition-all ${listening
                        ? 'bg-red-500 text-white shadow-lg shadow-red-200'
                        : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-card)]'
                        }`}
                    >
                      {listening ? (
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ repeat: Infinity, duration: 1 }}
                        >
                          <Mic className="w-5 h-5 sm:w-6 sm:h-6" />
                        </motion.div>
                      ) : (
                        <Mic className="w-5 h-5 sm:w-6 sm:h-6" />
                      )}
                    </motion.button>
                  )}
                  <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-400 animate-pulse" />
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.05, boxShadow: "0 20px 25px -5px rgb(79 70 229 / 0.4)" }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={loading || !input.trim()}
                className="px-6 sm:px-8 lg:px-12 py-4 sm:py-5 lg:py-6 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 hover:from-indigo-700 hover:via-purple-700 hover:to-indigo-800 text-white rounded-2xl sm:rounded-3xl lg:rounded-[2.5rem] font-bold shadow-[0_10px_15px_-3px_rgb(79_70_229_/_0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 whitespace-nowrap min-w-[120px] sm:min-w-[180px] justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 sm:w-6 sm:h-6 animate-spin" />
                    <span className="hidden sm:inline text-sm lg:text-base">Processing...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5 sm:w-6 sm:h-6" />
                    <span className="hidden sm:inline text-sm lg:text-base tracking-wide">Send Query</span>
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
