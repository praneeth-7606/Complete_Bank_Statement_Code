import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Sparkles, TrendingUp, DollarSign, PieChart, Calendar, Zap, Brain, MessageCircle, X, Mic, MicOff } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { chatAPI } from '../services/api'
import RAGResponseFormatter from '../components/chat/RAGResponseFormatter'
import ChatSessionHistory from '../components/chat/ChatSessionHistory'
import { useChatSession } from '../hooks/useChatSession'
import { Button } from '../components/ui'

// Voice Recognition Imports
import 'regenerator-runtime/runtime'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'

const WELCOME_TEXT =
  '👋 Hello! I\'m your AI-powered financial assistant. I can help you analyze your transactions, understand spending patterns, and provide personalized financial insights. What would you like to know?'

const Chat = () => {
  const {
    messages,
    setMessages,
    clearSession,
    openArchived,
    removeArchived,
    archived,
    activeId,
  } = useChatSession('rag', WELCOME_TEXT)
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
      setInput(transcript)
    }
  }, [transcript])

  useEffect(() => {
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
      SpeechRecognition.stopListening()
    } else {
      resetTranscript()
      SpeechRecognition.startListening({
        continuous: true,
        language: 'en-IN',
        interimResults: true
      })
    }
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
      const history = messages.map(m => ({
        role: m.role,
        content: typeof m.content === 'string' ? m.content : (m.content?.data?.answer || "Financial Data")
      })).slice(-10)

      const response = await chatAPI.sendQuery(input, history)

      const assistantMessage = {
        role: 'assistant',
        content: response,
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
    clearSession()
    toast.success('Session archived. Starting a new conversation.')
  }

  const firstUserMsg = messages.find((m) => m.role === 'user')
  const activeTitle = firstUserMsg
    ? String(firstUserMsg.content).slice(0, 80)
    : 'New conversation'

  return (
    <div className="h-[calc(100vh-8rem)] sm:h-[calc(100vh-9rem)] flex flex-col w-full">
      {/* Compact toolbar header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between gap-3 px-4 sm:px-5 py-3 mb-3 sm:mb-4 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-sm"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-primary-600 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm sm:text-base font-bold text-[var(--text-primary)] tracking-tight truncate">
              Financial Assistant
            </h2>
            <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
              <span className="flex items-center gap-1"><Brain className="w-3 h-3" /> Agentic RAG</span>
              <span className="w-1 h-1 bg-[var(--text-secondary)] rounded-full"></span>
              <span className="hidden sm:inline">Long-term Memory</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="hidden sm:flex items-center gap-1.5 bg-green-500/10 dark:bg-green-500/15 px-2.5 py-1.5 rounded-full border border-green-500/30">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-green-600 dark:text-green-400 text-[10px] font-bold uppercase tracking-wide">Online</span>
          </div>
          <ChatSessionHistory
            activeId={activeId}
            activeTitle={activeTitle}
            activeCount={messages.length}
            archived={archived}
            onOpen={openArchived}
            onDelete={removeArchived}
            accent="blue"
          />
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] hover:border-red-400/50 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all text-[var(--text-secondary)] hover:text-red-600 dark:hover:text-red-400 text-xs font-semibold"
          >
            <X className="w-3.5 h-3.5" /> Clear
          </button>
        </div>
      </motion.div>

      {/* Messages container */}
      <div className="relative flex-1 flex flex-col overflow-hidden rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] shadow-sm">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5 space-y-4">
          <AnimatePresence>
            {messages.map((message, index) => {
              const isAssistant = message.role === 'assistant';
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ type: "spring", stiffness: 250, damping: 25 }}
                  className={`flex gap-3 ${!isAssistant ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${!isAssistant
                    ? 'bg-primary-600'
                    : 'bg-[var(--bg-surface)] border border-[var(--border-subtle)]'
                    }`}>
                    {!isAssistant ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                    )}
                  </div>

                  <div className={`flex-1 max-w-[85%] sm:max-w-[80%] ${!isAssistant ? 'text-right' : 'text-left'}`}>
                    <div className={`inline-block p-3.5 sm:p-4 rounded-2xl text-left ${isAssistant
                      ? 'bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-tl-none w-full'
                      : 'bg-primary-600 text-white rounded-tr-none'
                      }`}>
                      {isAssistant ? (
                        <RAGResponseFormatter
                          response={typeof message.content === 'string' ? { data: { answer: message.content } } : message.content}
                          loading={false}
                        />
                      ) : (
                        <div className="whitespace-pre-wrap text-sm font-medium leading-relaxed">
                          {message.content}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1 px-1">
                      <p className="text-[10px] text-[var(--text-secondary)]">
                        {(() => {
                          const ts = message.timestamp instanceof Date
                            ? message.timestamp
                            : new Date(message.timestamp)
                          return Number.isNaN(ts.getTime())
                            ? ''
                            : ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        })()}
                      </p>
                      {isAssistant && (
                        <span className="text-[10px] text-[var(--text-secondary)] hidden sm:inline">• AI</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <div className="w-8 h-8 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl rounded-tl-none p-3.5">
                <div className="flex items-center gap-2.5">
                  <Loader2 className="w-4 h-4 text-primary-600 animate-spin" />
                  <div className="flex gap-1">
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                      className="w-1.5 h-1.5 bg-primary-500 rounded-full"
                    />
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }}
                      className="w-1.5 h-1.5 bg-primary-500 rounded-full"
                    />
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }}
                      className="w-1.5 h-1.5 bg-primary-500 rounded-full"
                    />
                  </div>
                  <span className="text-xs text-[var(--text-secondary)]">Thinking...</span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested questions */}
        {messages.length === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="px-3 sm:px-4 pb-3"
          >
            <div className="flex items-center gap-1.5 mb-2 px-1">
              <MessageCircle className="w-3.5 h-3.5 text-primary-500" />
              <p className="text-xs font-semibold text-[var(--text-secondary)]">Try asking:</p>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              {suggestedQuestions.map((question, index) => {
                const Icon = question.icon
                return (
                  <button
                    key={index}
                    onClick={() => handleSuggestedQuestion(question.text)}
                    className="flex-shrink-0 flex items-center gap-2 px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg hover:border-primary-400/50 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  >
                    <Icon className="w-3.5 h-3.5 text-primary-500" />
                    <span className="whitespace-nowrap">{question.text}</span>
                  </button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Input form */}
        <div className="p-3 sm:p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <form onSubmit={handleSubmit} className="space-y-2">
            <div className="flex gap-2 sm:gap-3 items-center">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={listening ? "Listening... Speak now..." : "Ask about your finances..."}
                  className="w-full px-4 sm:px-5 py-3 pr-20 rounded-xl border border-[var(--border-subtle)] focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all text-sm bg-[var(--bg-card)] placeholder:text-[var(--text-secondary)] font-medium text-[var(--text-primary)]"
                  disabled={loading}
                  autoFocus
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                  {browserSupportsSpeechRecognition && (
                    <button
                      type="button"
                      onClick={toggleListening}
                      className={`p-1.5 rounded-lg transition-all ${listening
                        ? 'bg-red-500 text-white'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'
                        }`}
                    >
                      {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>
                  )}
                  <Sparkles className="w-4 h-4 text-primary-400" />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className={`px-4 sm:px-5 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${loading || !input.trim()
                  ? 'bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-400 cursor-not-allowed'
                  : 'bg-primary-600 hover:bg-primary-700 text-white shadow-md shadow-primary-500/25'
                  }`}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span className="hidden sm:inline text-sm">Send</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-[10px] text-[var(--text-secondary)] text-center">
              Be specific with your questions for better insights
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Chat
