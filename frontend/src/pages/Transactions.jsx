import { useState, useEffect } from 'react'
import { Download, Loader2, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '../components/common'
import FilterBar from '../components/transactions/FilterBar'
import TransactionTable from '../components/transactions/TransactionTable'
import { pageTransition } from '../utils/animations'
import { statementsAPI } from '../services/api'
import api from '../services/api'
import toast from 'react-hot-toast'

const Transactions = () => {
  // Filter state
  const [filters, setFilters] = useState({
    categories: [],
    type: 'all',
    search: ''
  })

  // Pagination state
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0
  })

  // Data state
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch transactions with filters and pagination
  const fetchTransactions = async (pageNum = 1) => {
    try {
      setLoading(true)
      setError(null)

      // Build query parameters
      const params = {
        page: pageNum,
        limit: pagination.limit
      }

      if (filters.categories && filters.categories.length > 0) {
        // Send as a comma-separated string for simplicity with the modified backend
        params.categories = filters.categories.join(',')
      }
      if (filters.type && filters.type !== 'all') {
        params.type = filters.type
      }
      if (filters.search && filters.search.trim()) {
        params.search = filters.search.trim()
      }

      // Fetch from backend using axios
      const response = await api.get('/api/transactions/filtered', { params })

      if (response.data.status === 'success') {
        setTransactions(response.data.data.transactions)
        setPagination({
          page: response.data.data.page,
          limit: response.data.data.limit,
          total: response.data.data.total,
          totalPages: response.data.data.total_pages
        })
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (error) {
      console.error('Error fetching transactions:', error)
      setError(error.message || 'Failed to load transactions')
      toast.error('Failed to load transactions')
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }

  // Fetch on component mount
  useEffect(() => {
    fetchTransactions(1)
  }, [])

  // Refetch when filters change
  useEffect(() => {
    fetchTransactions(1)
  }, [filters])

  const handleFilterChange = ({ categories, type }) => {
    setFilters(prev => ({
      ...prev,
      categories: categories || [],
      type: type === 'all' ? 'all' : type
    }))
  }

  const handleSearchChange = (term) => {
    setFilters(prev => ({
      ...prev,
      search: term
    }))
  }

  const removeCategory = (cat) => {
    setFilters(prev => ({
      ...prev,
      categories: prev.categories.filter(c => c !== cat)
    }))
  }

  const removeType = () => {
    setFilters(prev => ({
      ...prev,
      type: 'all'
    }))
  }

  const clearAllFilters = () => {
    setFilters({
      categories: [],
      type: 'all',
      search: ''
    })
  }

  const handlePageChange = (page) => {
    fetchTransactions(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleExport = () => {
    const csv = [
      ['Date', 'Description', 'Category', 'Type', 'Amount'],
      ...transactions.map(t => [
        t.date,
        t.description,
        t.category || 'N/A',
        t.credit > 0 ? 'income' : 'expense',
        t.amount
      ])
    ].map(row => row.join(',')).join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-16 h-16 text-indigo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Loading transactions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <motion.div {...pageTransition} className="space-y-6">
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Transactions</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <Button
            variant="primary"
            onClick={() => fetchTransactions(1)}
          >
            Retry
          </Button>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div {...pageTransition} className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">Transactions</h2>
          <p className="text-xs sm:text-sm text-gray-600 mt-1">
            Showing {transactions.length} of {pagination.total} transactions
          </p>
        </div>
        <Button
          variant="primary"
          icon={Download}
          iconPosition="left"
          onClick={handleExport}
          disabled={transactions.length === 0}
          className="w-full sm:w-auto"
        >
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onSearchChange={handleSearchChange}
      />

      {/* Active Filter Chips */}
      {(filters.categories.length > 0 || filters.type !== 'all' || filters.search) && (
        <div className="flex flex-wrap items-center gap-2 py-2">
          <span className="text-sm font-medium text-gray-500 mr-2">Active Filters:</span>

          {filters.search && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1 px-3 py-1 bg-indigo-50 border border-indigo-200 text-indigo-700 rounded-full text-xs font-medium"
            >
              Search: "{filters.search}"
              <button
                onClick={() => handleSearchChange('')}
                className="hover:text-indigo-900 ml-1"
              >
                <X size={14} />
              </button>
            </motion.div>
          )}

          {filters.type !== 'all' && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1 px-3 py-1 bg-purple-50 border border-purple-200 text-purple-700 rounded-full text-xs font-medium capitalize"
            >
              Type: {filters.type}
              <button
                onClick={removeType}
                className="hover:text-purple-900 ml-1"
              >
                <X size={14} />
              </button>
            </motion.div>
          )}

          {filters.categories.map((cat) => (
            <motion.div
              key={cat}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1 px-3 py-1 bg-blue-50 border border-blue-200 text-blue-700 rounded-full text-xs font-medium"
            >
              {cat}
              <button
                onClick={() => removeCategory(cat)}
                className="hover:text-blue-900 ml-1"
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="text-xs text-gray-500 hover:text-indigo-600 ml-2"
          >
            Clear All
          </Button>
        </div>
      )}

      {/* Transactions Table */}
      {transactions.length > 0 ? (
        <TransactionTable
          transactions={transactions}
          onSort={(field, direction) => {
            // Sorting is handled by backend, but we can implement client-side sorting if needed
          }}
        />
      ) : (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 text-center">
          <p className="text-gray-600">No transactions found matching your filters.</p>
        </div>
      )}

      {/* Pagination */}
      {transactions.length > 0 && pagination.totalPages > 1 && (
        <div className="bg-white rounded-xl sm:rounded-2xl shadow-lg border border-gray-100 p-3 sm:p-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <p className="text-xs sm:text-sm text-gray-600 text-center sm:text-left">
              Page {pagination.page} of {pagination.totalPages} ({pagination.total} total)
            </p>
            <div className="flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="flex-1 sm:flex-none"
              >
                Previous
              </Button>
              <span className="px-2 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 whitespace-nowrap">
                {pagination.page} / {pagination.totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.totalPages}
                className="flex-1 sm:flex-none"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}

export default Transactions
