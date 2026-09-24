import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Sparkles, TrendingUp, DollarSign, PieChart, Info, ShieldCheck, BarChart3, Search, MessageCircle, X, ExternalLink } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { chatAPI } from '../services/api'
import RAGResponseFormatter from '../components/chat/RAGResponseFormatter'
import ChatSessionHistory from '../components/chat/ChatSessionHistory'
import { useChatSession } from '../hooks/useChatSession'

const WELCOME_TEXT =
    '🟢 Welcome to your Groww Investment Assistant! I can help you analyze your portfolio, get live market quotes, and discover new investment opportunities. How can I assist your wealth journey today?'

const InvestmentChat = () => {
    const {
        messages,
        setMessages,
        clearSession,
        openArchived,
        removeArchived,
        archived,
        activeId,
    } = useChatSession('investment', WELCOME_TEXT)
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
            const response = await chatAPI.sendInvestmentQuery(input)

            const assistantMessage = {
                role: 'assistant',
                content: response,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, assistantMessage])
        } catch (error) {
            console.error('Investment Chat error:', error)
            toast.error('Failed to get response from Groww Assistant')

            const errorMessage = {
                role: 'assistant',
                content: 'I apologize, but I encountered an error connecting to the brokerage service. Please verify your MCP configuration.',
                timestamp: new Date()
            }
            setMessages(prev => [...prev, errorMessage])
        } finally {
            setLoading(false)
        }
    }

    const suggestedQuestions = [
        { icon: PieChart, text: 'Show my portfolio holdings' },
        { icon: TrendingUp, text: 'What is the current price of RELIANCE?' },
        { icon: BarChart3, text: 'Analyze my profit and loss' },
        { icon: Search, text: 'Find top-performing ETFs' },
        { icon: Info, text: 'Stock details for HDFCBANK' },
        { icon: DollarSign, text: 'Check available margin' },
    ]

    const handleSuggestedQuestion = (question) => setInput(question)
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
            {/* Compact toolbar header — emerald brand accent */}
            <motion.div
                initial={{ opacity: 0, y: -12 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between gap-3 px-4 sm:px-5 py-3 mb-3 sm:mb-4 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-sm"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center flex-shrink-0">
                        <TrendingUp className="w-5 h-5 text-white" />
                    </div>
                    <div className="min-w-0">
                        <h2 className="text-sm sm:text-base font-bold text-[var(--text-primary)] tracking-tight truncate flex items-center gap-2">
                            Groww Assistant
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">MCP</span>
                        </h2>
                        <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                            <ShieldCheck className="w-3 h-3" />
                            <span>Secure Brokerage API</span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="hidden sm:flex items-center gap-1.5 bg-emerald-500/10 px-2.5 py-1.5 rounded-full border border-emerald-500/30">
                        <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                        <span className="text-emerald-600 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wide">Live</span>
                    </div>
                    <ChatSessionHistory
                        activeId={activeId}
                        activeTitle={activeTitle}
                        activeCount={messages.length}
                        archived={archived}
                        onOpen={openArchived}
                        onDelete={removeArchived}
                        accent="emerald"
                    />
                    <button
                        onClick={clearChat}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] hover:border-red-400/50 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all text-[var(--text-secondary)] hover:text-red-600 dark:hover:text-red-400 text-xs font-semibold"
                    >
                        <X className="w-3.5 h-3.5" /> Clear
                    </button>
                </div>
            </motion.div>

            {/* Main Chat & Sidebar */}
            <div className="flex-1 flex gap-4 sm:gap-6 overflow-hidden min-h-0">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] shadow-sm overflow-hidden min-w-0">
                    <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4 scrollbar-hide">
                        <AnimatePresence>
                            {messages.map((m, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ type: "spring", stiffness: 250, damping: 25 }}
                                    className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                                >
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${m.role === 'user' ? 'bg-emerald-600' : 'bg-[var(--bg-surface)] border border-[var(--border-subtle)]'
                                        }`}>
                                        {m.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                                    </div>
                                    <div className={`flex-1 max-w-[85%] sm:max-w-[80%] ${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                                        {m.role === 'user' ? (
                                            <div className="inline-block p-3.5 rounded-2xl rounded-tr-none bg-emerald-600 text-white font-medium text-sm">
                                                {m.content}
                                            </div>
                                        ) : (
                                            <div className="bg-[var(--bg-surface)] rounded-2xl rounded-tl-none p-3.5 border border-[var(--border-subtle)] text-[var(--text-primary)] w-full">
                                                <RAGResponseFormatter
                                                    response={typeof m.content === 'string' ? { data: { answer: m.content } } : m.content}
                                                    loading={false}
                                                />
                                            </div>
                                        )}
                                        <span className="text-[10px] text-[var(--text-secondary)] mt-1 block px-1">
                                            {(() => {
                                                const ts = m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp)
                                                return Number.isNaN(ts.getTime())
                                                    ? ''
                                                    : ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                            })()}
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>

                        {loading && (
                            <motion.div
                                initial={{ opacity: 0, y: 12 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex gap-3"
                            >
                                <div className="w-8 h-8 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex items-center justify-center">
                                    <Bot className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                                </div>
                                <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl rounded-tl-none p-3.5">
                                    <div className="flex items-center gap-2.5">
                                        <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />
                                        <span className="text-xs text-[var(--text-secondary)]">Thinking...</span>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Suggested questions */}
                    {messages.length === 1 && (
                        <div className="px-3 sm:px-4 pb-2">
                            <div className="flex items-center gap-1.5 mb-2 px-1">
                                <MessageCircle className="w-3.5 h-3.5 text-emerald-500" />
                                <p className="text-xs font-semibold text-[var(--text-secondary)]">Try asking:</p>
                            </div>
                            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                                {suggestedQuestions.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestedQuestion(q.text)}
                                        className="flex-shrink-0 flex items-center gap-2 px-3 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg hover:border-emerald-400/50 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-all text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                    >
                                        <q.icon className="w-3.5 h-3.5 text-emerald-500" />
                                        <span className="whitespace-nowrap">{q.text}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Input Area */}
                    <div className="p-3 sm:p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                        <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
                            <div className="flex-1 relative">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Ask about your stocks, portfolio or market..."
                                    className="w-full px-4 sm:px-5 py-3 rounded-xl border border-[var(--border-subtle)] focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all text-sm font-medium bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-secondary)]"
                                    disabled={loading}
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={loading || !input.trim()}
                                className={`px-4 sm:px-5 py-3 rounded-xl font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${loading || !input.trim()
                                    ? 'bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-400 cursor-not-allowed'
                                    : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-500/25'
                                    }`}
                            >
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Send className="w-4 h-4" /> <span className="hidden sm:inline text-sm">Send</span></>}
                            </button>
                        </form>
                    </div>
                </div>

                {/* Desktop Sidebar Widget */}
                <div className="hidden lg:flex w-72 xl:w-80 flex-col gap-4">
                    <div className="bg-[var(--bg-card)] rounded-xl p-5 border border-[var(--border-subtle)] shadow-sm">
                        <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3 flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> Portfolio Health
                        </h3>
                        <div className="space-y-3">
                            <div className="p-3.5 bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                                <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold uppercase tracking-wider">Total Value</p>
                                <p className="text-xl font-bold text-[var(--text-primary)] mt-0.5">₹ --,---</p>
                            </div>
                            <div className="p-3.5 bg-[var(--bg-surface)] rounded-xl border border-[var(--border-subtle)]">
                                <p className="text-[10px] text-[var(--text-secondary)] font-bold uppercase tracking-wider">Today's Gain</p>
                                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">+₹ -.-%</p>
                            </div>
                            <button className="w-full py-3 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-700 dark:text-emerald-400 rounded-xl font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
                                View Full Portfolio <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>
                    <div className="bg-[var(--bg-card)] rounded-xl p-5 text-[var(--text-primary)] shadow-sm border border-[var(--border-subtle)] relative overflow-hidden">
                        <div className="absolute -right-4 -top-4 w-20 h-20 bg-emerald-500/10 rounded-full blur-2xl"></div>
                        <h3 className="text-xs font-bold mb-2 flex items-center gap-1.5 uppercase tracking-wider text-[var(--text-secondary)]">
                            <Sparkles className="w-3.5 h-3.5 text-emerald-500" /> Market Insights
                        </h3>
                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                            "Nifty 50 showing strong support at 22,000. Technology sector continues to outperform..."
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default InvestmentChat
