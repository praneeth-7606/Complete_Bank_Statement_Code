import { useState } from 'react'
import { Save, AlertCircle, CheckCircle, BookOpen } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { correctionAPI } from '../services/api'

const Corrections = () => {
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [corrections, setCorrections] = useState([])

  const categories = [
    'Food & Dining',
    'Shopping',
    'Transportation',
    'Entertainment',
    'Healthcare',
    'Utilities',
    'Education',
    'Personal Care',
    'Travel',
    'Insurance',
    'Investments',
    'Rent',
    'Groceries',
    'Other'
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!keyword.trim() || !category) {
      toast.error('Please fill in all fields')
      return
    }

    setSubmitting(true)

    try {
      const response = await correctionAPI.submitCorrection(keyword, category)
      
      setCorrections(prev => [...prev, {
        keyword,
        category,
        timestamp: new Date().toISOString()
      }])
      
      toast.success('Correction saved successfully!')
      setKeyword('')
      setCategory('')
    } catch (error) {
      console.error('Correction error:', error)
      toast.error(error.response?.data?.detail || 'Failed to save correction')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Info Banner */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200"
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <BookOpen className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Teach the AI</h3>
            <p className="text-sm text-gray-700">
              Help improve transaction categorization by providing corrections. When you specify a keyword 
              and its correct category, the AI will learn and automatically apply this rule to future transactions 
              containing that keyword.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Correction Form */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Add Correction Rule</h2>
            <p className="text-sm text-gray-600">Define keyword-based categorization rules</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Keyword Input */}
          <div>
            <label htmlFor="keyword" className="block text-sm font-medium text-gray-700 mb-2">
              Transaction Keyword
            </label>
            <input
              type="text"
              id="keyword"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="e.g., SWIGGY, AMAZON, UBER"
              className="input-field"
              disabled={submitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter a keyword that appears in transaction descriptions
            </p>
          </div>

          {/* Category Select */}
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
              Correct Category
            </label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input-field"
              disabled={submitting}
            >
              <option value="">Select a category</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Choose the category that should be applied to transactions with this keyword
            </p>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Correction Rule
              </>
            )}
          </button>
        </form>
      </motion.div>

      {/* Saved Corrections */}
      {corrections.length > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <h3 className="text-lg font-semibold mb-4">Recent Corrections</h3>
          <div className="space-y-3">
            {corrections.map((correction, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200"
              >
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="font-medium text-gray-900">
                      Keyword: <span className="text-primary-600">{correction.keyword}</span>
                    </p>
                    <p className="text-sm text-gray-600">
                      Category: {correction.category}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(correction.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Examples */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <h3 className="text-lg font-semibold mb-4">Example Corrections</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900 mb-1">SWIGGY</p>
            <p className="text-sm text-gray-600">→ Food & Dining</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900 mb-1">AMAZON</p>
            <p className="text-sm text-gray-600">→ Shopping</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900 mb-1">UBER</p>
            <p className="text-sm text-gray-600">→ Transportation</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900 mb-1">NETFLIX</p>
            <p className="text-sm text-gray-600">→ Entertainment</p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default Corrections
