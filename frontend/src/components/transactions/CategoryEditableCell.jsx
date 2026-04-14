import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Loader2, Check, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import api from '../../services/api'
import { TRANSACTION_CATEGORIES } from '../../utils/constants'

const CATEGORIES = Object.values(TRANSACTION_CATEGORIES).map(cat => cat.label)

const CATEGORY_COLORS = {
  'Food & Dining': 'from-orange-500 to-red-500',
  'Transportation': 'from-green-500 to-emerald-500',
  'Shopping': 'from-pink-500 to-rose-500',
  'Entertainment': 'from-yellow-500 to-orange-500',
  'Bills & Utilities': 'from-purple-500 to-indigo-500',
  'Healthcare': 'from-red-500 to-pink-500',
  'Education': 'from-blue-600 to-indigo-600',
  'Travel': 'from-sky-500 to-blue-600',
  'Investment': 'from-indigo-600 to-purple-600',
  'Dividend': 'from-emerald-500 to-teal-500',
  'Salary': 'from-green-600 to-teal-600',
  'Transfer': 'from-slate-400 to-gray-400',
  'Personal Transfer': 'from-blue-500 to-cyan-500',
  'Other Transfers': 'from-blue-400 to-indigo-400',
  'Other': 'from-gray-500 to-slate-500'
}

const CategoryEditableCell = ({ transactionId, description, currentCategory, allTransactions = [], onUpdate, onError }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState(currentCategory)
  const [searchTerm, setSearchTerm] = useState('')
  const dropdownRef = useRef(null)

  // Filter categories based on search
  const filteredCategories = CATEGORIES.filter(cat =>
    cat.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
        setSearchTerm('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleCategorySelect = async (newCategory) => {
    if (newCategory === selectedCategory) {
      setIsOpen(false)
      return
    }

    // Identify similar transactions for proactive notification
    const extractIdentity = (desc) => {
      if (!desc) return ""
      let clean = desc.toUpperCase().replace(/UPI TXN: /i, "").trim()
      clean = clean.split('/')[0].trim() // Take the name part before the first "/"
      return clean
    }

    const currentIdentity = extractIdentity(description)
    const matches = allTransactions.filter(t =>
      t.id !== transactionId &&
      extractIdentity(t.description || t.narration) === currentIdentity
    )
    const matchCount = matches.length

    const previousCategory = selectedCategory
    try {
      setIsLoading(true)

      // 1. Perform Single Update
      const response = await api.put(
        `/api/transactions/${transactionId}/category`,
        { new_category: newCategory }
      )

      if (response.data.status === 'success') {
        setSelectedCategory(newCategory)
        setIsOpen(false)
        setSearchTerm('')

        if (onUpdate) onUpdate(newCategory)

        // 2. Propose Global Propagation (Self-Learning)
        if (matchCount > 0) {
          toast.success((t) => (
            <div className="flex flex-col gap-2">
              <span className="font-medium text-gray-900 border-b pb-1">Similar Transactions Found!</span>
              <p className="text-xs text-gray-600">
                We found <span className="font-bold text-indigo-600">{matchCount}</span> other transactions for <span className="italic">"{currentIdentity}"</span>.
              </p>
              <span className="text-[11px] text-gray-500 font-medium">Change their category to {newCategory} too?</span>
              <div className="flex gap-2 mt-1">
                <button
                  onClick={async () => {
                    toast.dismiss(t.id)
                    try {
                      toast.loading(`Updating ${matchCount + 1} transactions...`, { id: "propagation-loading" })
                      await api.post('/correct-transaction/', {
                        transaction_description_keyword: description,
                        correct_category: newCategory
                      })
                      toast.dismiss("propagation-loading")
                      toast.success(`✅ Successfully updated all ${matchCount + 1} transactions!`)

                      // Instant UI feedback: update all matches in the list
                      matches.forEach(m => { m.category = newCategory })
                      if (onUpdate) onUpdate(newCategory)

                      // Refresh after a short delay to ensure DB sync
                      setTimeout(() => window.location.reload(), 1500)
                    } catch (err) {
                      toast.dismiss("propagation-loading")
                      toast.error("Failed to propagate changes")
                    }
                  }}
                  className="px-3 py-1.5 bg-indigo-600 text-white rounded shadow-sm text-xs hover:bg-indigo-700 transition-all font-bold"
                >
                  Yes, Change All
                </button>
                <button
                  onClick={() => toast.dismiss(t.id)}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200 transition-all font-medium"
                >
                  No, Just This One
                </button>
              </div>
            </div>
          ), { duration: 10000, position: 'bottom-right' })
        } else {
          toast.success(`Category updated to ${newCategory}`)
        }
      }
    } catch (error) {
      console.error('Error updating category:', error)
      setSelectedCategory(previousCategory)
      const errorMessage = error.response?.data?.detail || 'Failed to update category'
      toast.error(errorMessage)
      if (onError) onError(error)
    } finally {
      setIsLoading(false)
    }
  }

  const colorClass = CATEGORY_COLORS[selectedCategory] || CATEGORY_COLORS['Other']

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Category Badge - Clickable */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold text-white bg-gradient-to-r ${colorClass} shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-3 h-3 sm:w-4 sm:h-4 animate-spin" />
            <span className="hidden sm:inline">Updating...</span>
          </>
        ) : (
          <>
            <span>{selectedCategory}</span>
            <ChevronDown className={`w-3 h-3 sm:w-4 sm:h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </>
        )}
      </motion.button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full right-0 mt-2 w-48 sm:w-56 bg-white rounded-lg shadow-xl border border-gray-200 z-50"
          >
            {/* Search Input */}
            <div className="p-2 border-b border-gray-100">
              <input
                type="text"
                placeholder="Search categories..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                autoFocus
              />
            </div>

            {/* Categories List */}
            <div className="max-h-64 overflow-y-auto">
              {filteredCategories.length > 0 ? (
                filteredCategories.map((category) => (
                  <motion.button
                    key={category}
                    whileHover={{ backgroundColor: '#f3f4f6' }}
                    onClick={() => handleCategorySelect(category)}
                    className={`w-full text-left px-4 py-2.5 text-xs sm:text-sm font-medium transition-colors flex items-center justify-between ${selectedCategory === category
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-700 hover:bg-gray-50'
                      }`}
                  >
                    <span>{category}</span>
                    {selectedCategory === category && (
                      <Check className="w-4 h-4 text-indigo-600" />
                    )}
                  </motion.button>
                ))
              ) : (
                <div className="px-4 py-3 text-center text-xs sm:text-sm text-gray-500">
                  No categories found
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default CategoryEditableCell
