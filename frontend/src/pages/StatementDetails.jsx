import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { statementsAPI } from '../services/api';
import {
  ArrowLeft,
  FileText,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Loader,
  Filter,
  Search,
  Trash2
} from 'lucide-react';

export default function StatementDetails() {
  const { uploadId } = useParams();
  const navigate = useNavigate();
  const [statement, setStatement] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    fetchStatementDetails();
  }, [uploadId]);

  useEffect(() => {
    filterTransactions();
  }, [transactions, searchTerm, filterCategory, filterType]);

  const fetchStatementDetails = async () => {
    try {
      setLoading(true);
      const data = await statementsAPI.getStatementDetails(uploadId);
      if (data.status === 'success') {
        setStatement(data.statement);
        setTransactions(data.transactions || []);
      } else {
        setError('Failed to fetch statement details');
      }
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 404) {
        setError('This statement could not be found. It may have been deleted.');
      } else if (status === 401) {
        setError('Your session has expired. Please log in again.');
      } else {
        setError(detail || 'Failed to load statement details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const filterTransactions = () => {
    let filtered = [...transactions];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(t =>
        String(t.description || '').toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Category filter
    if (filterCategory !== 'all') {
      filtered = filtered.filter(t => t.category === filterCategory);
    }

    // Type filter (debit/credit)
    if (filterType === 'debit') {
      filtered = filtered.filter(t => t.debit > 0);
    } else if (filterType === 'credit') {
      filtered = filtered.filter(t => t.credit > 0);
    }

    setFilteredTransactions(filtered);
  };

  const handleDeleteStatement = async () => {
    try {
      setDeleting(true);
      const result = await statementsAPI.deleteStatement(uploadId);

      if (result.status === 'success') {
        // Navigate back to statements page
        navigate('/statements');
      } else {
        alert('Failed to delete statement');
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert(err.response?.data?.detail || 'Failed to delete statement');
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount) => {
    return `₹${parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const categories = [...new Set(transactions.map(t => t.category))];

  const totalDebit = transactions.reduce((sum, t) => sum + (Number(t.debit) || 0), 0);
  const totalCredit = transactions.reduce((sum, t) => sum + (Number(t.credit) || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader className="w-12 h-12 text-indigo-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Loading statement details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="card max-w-md w-full text-center p-8">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Statement unavailable</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/statements')}
            className="px-5 py-2.5 bg-indigo-600 text-[var(--text-primary)] rounded-lg hover:bg-indigo-700 font-medium transition-colors"
          >
            Back to Statements
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/statements')}
            className="flex items-center text-gray-500 hover:text-gray-900 dark:hover:text-[var(--text-primary)] mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Statements
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl sm:text-4xl font-black text-gray-900 dark:from-white dark:to-gray-400 mb-2">
                {statement?.filename}
              </h1>
              <p className="text-gray-500">
                {statement?.bank_name} • {transactions.length} transactions
              </p>
            </div>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleting}
              className="px-4 py-2 bg-red-500 text-[var(--text-primary)] rounded-lg hover:bg-red-600 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deleting ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              <span>{deleting ? 'Deleting...' : 'Delete Statement'}</span>
            </button>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] max-w-md w-full p-6 shadow-2xl">
              <div className="flex items-start space-x-3 mb-4">
                <AlertCircle className="w-6 h-6 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">
                    Confirm Deletion
                  </h3>
                  <p className="text-gray-400 mb-3">
                    Are you sure you want to delete &quot;{statement?.filename}&quot;?
                  </p>
                  <p className="text-sm text-gray-500 mb-3">
                    This will permanently remove:
                  </p>
                  <ul className="text-sm text-gray-400 mb-4 space-y-1 ml-4">
                    <li>• {transactions.length} transactions from database</li>
                    <li>• All search vectors from Pinecone</li>
                    <li>• Statement metadata and insights</li>
                  </ul>
                  <p className="text-sm font-semibold text-red-600 mb-4">
                    ⚠️ This action cannot be undone!
                  </p>
                </div>
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleDeleteStatement}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-red-600 text-[var(--text-primary)] rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50"
                >
                  {deleting ? 'Deleting...' : 'Yes, Delete'}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-[var(--bg-surface)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-colors font-medium border border-[var(--border-subtle)] disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Statement Info Card */}
        <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">Bank</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">{statement?.bank_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Extraction Method</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">{statement?.extraction_method}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Processing Time</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">
                {statement?.processing_time_seconds?.toFixed(2)}s
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">Pages</p>
              <p className="text-lg font-semibold text-[var(--text-primary)]">{statement?.page_count}</p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm mb-1">Total Transactions</p>
                <p className="text-3xl font-bold text-[var(--text-primary)]">{transactions.length}</p>
              </div>
              <FileText className="w-12 h-12 text-indigo-500 opacity-20" />
            </div>
          </div>

          <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm mb-1">Total Debits</p>
                <p className="text-3xl font-bold text-rose-400">{formatCurrency(totalDebit)}</p>
              </div>
              <TrendingDown className="w-12 h-12 text-rose-500 opacity-20" />
            </div>
          </div>

          <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm mb-1">Total Credits</p>
                <p className="text-3xl font-bold text-emerald-400">{formatCurrency(totalCredit)}</p>
              </div>
              <TrendingUp className="w-12 h-12 text-emerald-500 opacity-20" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                <Search className="w-4 h-4 inline mr-2" />
                Search
              </label>
              <input
                type="text"
                placeholder="Search transactions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-[var(--text-primary)] placeholder-gray-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Filter className="w-4 h-4 inline mr-2" />
                Category
              </label>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-[var(--text-primary)] appearance-none"
              >
                <option value="all">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Filter className="w-4 h-4 inline mr-2" />
                Type
              </label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-[var(--text-primary)] appearance-none"
              >
                <option value="all">All Types</option>
                <option value="debit">Debits Only</option>
                <option value="credit">Credits Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[var(--bg-surface)] border-b border-[var(--border-subtle)]">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTransactions.map((transaction) => (
                <tr key={transaction.id} className="hover:bg-[var(--bg-surface)] transition-colors border-b border-[var(--border-subtle)]">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-primary)]">
                    {formatDate(transaction.date)}
                  </td>
                  <td className="px-6 py-4 text-sm text-[var(--text-primary)]">
                    <div className="max-w-md truncate">{transaction.description}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border-subtle)]`}>
                      {transaction.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {transaction.debit > 0 ? (
                      <span className="flex items-center text-rose-400 font-medium">
                        <TrendingDown className="w-4 h-4 mr-1" />
                        Expense
                      </span>
                    ) : (
                      <span className="flex items-center text-emerald-400 font-medium">
                        <TrendingUp className="w-4 h-4 mr-1" />
                        Income
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-semibold">
                    <span className={transaction.debit > 0 ? 'text-rose-400' : 'text-emerald-400'}>
                      {formatCurrency(transaction.amount)}
                    </span>
                  </td>
                </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredTransactions.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No transactions found matching your filters</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
