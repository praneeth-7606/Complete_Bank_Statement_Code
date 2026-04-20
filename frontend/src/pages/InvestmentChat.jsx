import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Sparkles, TrendingUp, DollarSign, PieChart, Info, ShieldCheck, BarChart3, Search, MessageCircle, X, ExternalLink } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { chatAPI } from '../services/api'
import RAGResponseFormatter from '../components/chat/RAGResponseFormatter'
import { Button, Badge, Card } from '../components/ui'

const InvestmentChat = () => {
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: '🟢 Welcome to your Groww Investment Assistant! I can help you analyze your portfolio, get live market quotes, and discover new investment opportunities. How can I assist your wealth journey today?',
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
            const response = await chatAPI.sendInvestmentQuery(input)

            const assistantMessage = {
                role: 'assistant',
                content: response, // Expected to be in structured format { status, data: { answer, ... } }
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
        { icon: PieChart, text: 'Show my portfolio holdings', color: 'from-emerald-500 to-green-500' },
        { icon: TrendingUp, text: 'What is the current price of RELIANCE?', color: 'from-blue-500 to-indigo-500' },
        { icon: BarChart3, text: 'Analyze my profit and loss', color: 'from-purple-500 to-pink-500' },
        { icon: Search, text: 'Find top-performing ETFs', color: 'from-orange-500 to-red-500' },
        { icon: Info, text: 'Stock details for HDFCBANK', color: 'from-cyan-500 to-blue-500' },
        { icon: DollarSign, text: 'Check available margin', color: 'from-yellow-500 to-orange-500' },
    ]

    const handleSuggestedQuestion = (question) => setInput(question)
    const clearChat = () => {
        setMessages([{
            role: 'assistant',
            content: '🟢 History cleared. Ready for your next investment query.',
            timestamp: new Date()
        }])
        toast.success('Session cleared')
    }

    return (
        <div className="h-[calc(100vh-6rem)] flex flex-col w-full py-4">
            {/* Header - Emerald Theme */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-2xl mb-6 shadow-2xl border border-emerald-500/20"
            >
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-950/40 via-green-950/40 to-teal-950/40"></div>
                <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

                <div className="relative p-8 lg:p-10">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-6 font-primary">
                        <div className="flex items-center gap-6">
                            <motion.div
                                animate={{ scale: [1, 1.1, 1] }}
                                transition={{ duration: 4, repeat: Infinity }}
                                className="w-16 h-16 sm:w-20 sm:h-20 bg-white/20 backdrop-blur-2xl rounded-3xl flex items-center justify-center shadow-2xl border border-white/40"
                            >
                                <TrendingUp className="w-10 h-10 text-white" />
                            </motion.div>
                            <div>
                                <h2 className="text-3xl font-black text-white tracking-tighter flex items-center gap-3">
                                    Groww Assistant
                                    <span className="text-xs bg-white/30 px-2 py-1 rounded-full font-bold">MCP POWERED</span>
                                </h2>
                                <div className="flex items-center gap-2 text-emerald-100 text-sm font-medium mt-1">
                                    <ShieldCheck className="w-4 h-4 text-emerald-300" />
                                    <span>Secure Brokerage API Connection</span>
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-4">
                            <button onClick={clearChat} className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded-xl text-white text-sm font-bold border border-white/20 transition-all flex items-center gap-2">
                                <X className="w-4 h-4" /> Reset
                            </button>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Main Chat & Sidebar */}
            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col bg-white/[0.02] backdrop-blur-xl rounded-3xl border border-white/5 shadow-2xl overflow-hidden">
                    <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
                        <AnimatePresence>
                            {messages.map((m, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: m.role === 'user' ? 20 : -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                                >
                                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shadow-lg flex-shrink-0 ${m.role === 'user' ? 'bg-emerald-600' : 'bg-gray-800'
                                        }`}>
                                        {m.role === 'user' ? <User className="w-6 h-6 text-white" /> : <Bot className="w-6 h-6 text-emerald-400" />}
                                    </div>
                                    <div className={`max-w-[80%] ${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                                        {m.role === 'user' ? (
                                            <div className="inline-block p-4 rounded-2xl bg-emerald-600 text-white font-medium shadow-xl">
                                                {m.content}
                                            </div>
                                        ) : (
                                            <div className="bg-white/[0.03] backdrop-blur-md rounded-2xl p-6 shadow-xl border border-white/5 min-w-[300px]">
                                                <RAGResponseFormatter
                                                    response={typeof m.content === 'string' ? { data: { answer: m.content } } : m.content}
                                                    loading={false}
                                                />
                                            </div>
                                        )}
                                        <span className="text-[10px] text-gray-500 mt-2 block px-2">
                                            {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Quick Actions Bar */}
                    {messages.length === 1 && (
                        <div className="px-6 pb-2">
                            <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide py-2">
                                {suggestedQuestions.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestedQuestion(q.text)}
                                        className="flex-shrink-0 flex items-center gap-2 px-4 py-3 bg-white/[0.03] border border-white/5 rounded-2xl hover:border-emerald-500/30 hover:bg-white/[0.06] transition-all text-sm font-semibold text-gray-400 hover:text-gray-200"
                                    >
                                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${q.color} flex items-center justify-center`}>
                                            <q.icon className="w-4 h-4 text-white" />
                                        </div>
                                        {q.text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Input Area */}
                    <div className="p-6 bg-transparent border-t border-white/5">
                        <form onSubmit={handleSubmit} className="flex gap-4">
                            <div className="flex-1 relative">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Ask about your stocks, portfolio or market..."
                                    className="w-full px-6 py-4 bg-white/[0.03] border border-white/10 rounded-2xl focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 transition-all font-medium text-white placeholder-gray-500"
                                    disabled={loading}
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={loading || !input.trim()}
                                className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-4 rounded-2xl font-bold shadow-emerald-200 shadow-xl disabled:opacity-50 transition-all flex items-center gap-2"
                            >
                                {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <><Send className="w-5 h-5" /> Send</>}
                            </button>
                        </form>
                    </div>
                </div>

                {/* Desktop Sidebar Widget */}
                <div className="hidden lg:flex w-80 flex-col gap-6">
                    <div className="bg-white/[0.03] backdrop-blur-xl rounded-3xl p-6 border border-white/5 shadow-xl">
                        <h3 className="text-lg font-black text-white mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-emerald-600" /> Portfolio Health
                        </h3>
                        <div className="space-y-4">
                            <div className="p-4 bg-emerald-500/5 rounded-2xl border border-emerald-500/10">
                                <p className="text-xs text-emerald-500 font-bold uppercase tracking-wider">Total Value</p>
                                <p className="text-2xl font-black text-white mt-1">₹ --,---</p>
                            </div>
                            <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                                <p className="text-xs text-gray-500 font-bold uppercase tracking-wider">Today's Gain</p>
                                <p className="text-xl font-black text-emerald-500 mt-1">+₹ -.-%</p>
                            </div>
                            <button className="w-full py-4 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-700 rounded-2xl font-bold text-sm transition-all flex items-center justify-center gap-2">
                                View Full Portfolio <ExternalLink className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                    <div className="bg-[#0f0f1a] rounded-3xl p-6 text-white shadow-2xl relative overflow-hidden border border-white/5">
                        <div className="absolute -right-4 -top-4 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl"></div>
                        <h3 className="text-md font-bold mb-3 flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-emerald-500" /> Market Insights
                        </h3>
                        <p className="text-sm text-gray-400 leading-relaxed italic">
                            "Nifty 50 showing strong support at 22,000. Technology sector continues to outperform..."
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default InvestmentChat
