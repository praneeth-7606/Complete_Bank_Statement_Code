import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { statementsAPI } from '../services/api';
import {
  FileText,
  Clock,
  Database,
  TrendingUp,
  Calendar,
  CheckCircle,
  AlertCircle,
  Loader,
  Eye,
  Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, Button, Badge, Skeleton, EmptyState, Modal } from '../components/ui';

export default function Statements() {
  const [statements, setStatements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchStatements();
  }, []);

  const fetchStatements = async () => {
    try {
      setLoading(true);
      const data = await statementsAPI.getAllStatements();
      if (data.status === 'success') {
        setStatements(data.statements || []);
      } else {
        setError('Failed to fetch statements');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch statements');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStatement = async (uploadId, filename) => {
    try {
      setDeletingId(uploadId);
      const result = await statementsAPI.deleteStatement(uploadId);

      if (result.status === 'success') {
        setStatements(statements.filter(s => s.upload_id !== uploadId));
        setShowDeleteConfirm(null);
        console.log(`✅ Deleted: ${filename}`);
      } else {
        alert('Failed to delete statement');
      }
    } catch (err) {
      console.error('Delete error:', err);
      alert(err.response?.data?.detail || 'Failed to delete statement');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getMethodBadgeColor = (method) => {
    switch (method) {
      case 'PDFPLUMBER':
        return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'GEMINI_TEXT':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'GEMINI_VISION':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader className="w-12 h-12 text-indigo-500 animate-spin mx-auto mb-4" />
          <p className="text-[var(--text-secondary)]">Loading statements...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
          <p className="text-rose-400 mb-4">{error}</p>
          <button
            onClick={fetchStatements}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-black text-[var(--text-primary)] mb-2">
          Bank Statements
        </h1>
        <p className="text-[var(--text-secondary)]">
          View and manage all your processed bank statements
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'Total Statements', value: statements.length, icon: FileText, color: 'text-indigo-500' },
          {
            label: 'Total Transactions',
            value: statements.reduce((sum, s) => sum + (s.total_transactions || 0), 0),
            icon: TrendingUp,
            color: 'text-emerald-500'
          },
          {
            label: 'Avg Processing',
            value: (statements.length > 0
              ? (statements.reduce((sum, s) => sum + (s.processing_time_seconds || 0), 0) / statements.length).toFixed(1)
              : 0) + 's',
            icon: Clock,
            color: 'text-purple-500'
          },
          {
            label: 'Total Data',
            value: formatFileSize(statements.reduce((sum, s) => sum + (s.file_size_bytes || 0), 0)),
            icon: Database,
            color: 'text-orange-500'
          }
        ].map((stat, i) => (
          <div key={i} className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[var(--text-secondary)] text-sm">{stat.label}</p>
                <p className="text-3xl font-bold text-[var(--text-primary)]">{stat.value}</p>
              </div>
              <stat.icon className={`w-12 h-12 ${stat.color} opacity-20`} />
            </div>
          </div>
        ))}
      </div>

      {/* Statements List */}
      <AnimatePresence>
        {statements.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-12 text-center"
          >
            <FileText className="w-16 h-16 text-[var(--text-secondary)] mx-auto mb-4 opacity-20" />
            <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-2">No Statements Yet</h3>
            <p className="text-[var(--text-secondary)] mb-6">Upload your first bank statement to get started</p>
            <button
              onClick={() => navigate('/upload')}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-lg"
            >
              Upload Statement
            </button>
          </motion.div>
        ) : (
          <div className="space-y-4">
            {statements.map((statement, idx) => (
              <motion.div
                key={statement.upload_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] overflow-hidden transition-all hover:bg-[var(--bg-surface)]/50 shadow-sm"
              >
                <div className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="p-3 bg-indigo-500/10 rounded-lg">
                        <FileText className="w-8 h-8 text-indigo-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-1 truncate">
                          {statement.filename}
                        </h3>
                        <div className="flex flex-wrap items-center gap-4 text-sm text-[var(--text-secondary)]">
                          <span className="flex items-center">
                            <Calendar className="w-4 h-4 mr-1" />
                            {formatDate(statement.uploaded_at)}
                          </span>
                          <span className="flex items-center">
                            {getStatusIcon(statement.status)}
                            <span className="ml-1 capitalize">{statement.status}</span>
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getMethodBadgeColor(statement.extraction_method)}`}>
                            {statement.extraction_method || 'Unknown'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => navigate(`/statement/${statement.upload_id}`)}
                        className="flex-1 lg:flex-none px-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-lg hover:bg-[var(--bg-card)] transition-colors flex items-center justify-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(statement.upload_id)}
                        disabled={deletingId === statement.upload_id}
                        className="flex-1 lg:flex-none px-4 py-2 bg-rose-500/10 text-rose-500 border border-rose-500/20 rounded-lg hover:bg-rose-500 hover:text-white transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                      >
                        {deletingId === statement.upload_id ? (
                          <Loader className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>

                  {showDeleteConfirm === statement.upload_id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-6 p-4 bg-rose-500/5 border border-rose-500/20 rounded-lg"
                    >
                      <div className="flex items-start space-x-3">
                        <AlertCircle className="w-5 h-5 text-rose-500 mt-0.5" />
                        <div className="flex-1">
                          <h4 className="font-semibold text-rose-500 mb-1">Confirm Deletion</h4>
                          <p className="text-sm text-[var(--text-secondary)] mb-3">
                            Are you sure you want to delete "{statement.filename}"? This will permanently remove all associated transactions and insights.
                          </p>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleDeleteStatement(statement.upload_id, statement.filename)}
                              disabled={deletingId === statement.upload_id}
                              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition-colors text-sm font-medium shadow-lg"
                            >
                              {deletingId === statement.upload_id ? 'Deleting...' : 'Yes, Delete'}
                            </button>
                            <button
                              onClick={() => setShowDeleteConfirm(null)}
                              disabled={deletingId === statement.upload_id}
                              className="px-4 py-2 bg-[var(--bg-surface)] text-[var(--text-primary)] border border-[var(--border-subtle)] rounded-lg hover:hover:bg-[var(--bg-card)] transition-colors text-sm font-medium"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                    {[
                      { label: 'Bank', value: statement.bank_name || '探索中...' },
                      { label: 'Transactions', value: statement.total_transactions },
                      { label: 'Pages', value: statement.page_count || 0 },
                      { label: 'Processing', value: (statement.processing_time_seconds || 0).toFixed(2) + 's' }
                    ].map((item, i) => (
                      <div key={i} className="bg-[var(--bg-surface)]/50 rounded-lg p-3 border border-[var(--border-subtle)]">
                        <p className="text-xs text-[var(--text-secondary)] mb-1 uppercase tracking-wider">{item.label}</p>
                        <p className="font-semibold text-[var(--text-primary)]">{item.value}</p>
                      </div>
                    ))}
                  </div>

                  {statement.insights && statement.insights.length > 0 && (
                    <div className="mt-6 p-4 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                      <div className="flex items-center space-x-2 mb-3">
                        <TrendingUp className="w-5 h-5 text-indigo-400" />
                        <h4 className="font-semibold text-indigo-500">AI Insights Preview</h4>
                      </div>
                      <ul className="space-y-2">
                        {statement.insights.slice(0, 2).map((insight, idx) => (
                          <li key={idx} className="text-sm text-[var(--text-secondary)] flex items-start space-x-2">
                            <span className="text-indigo-400 mt-1">•</span>
                            <span>{insight}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
