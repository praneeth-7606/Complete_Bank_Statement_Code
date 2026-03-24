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
  Download,
  Trash2
} from 'lucide-react';

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
        // Remove from local state
        setStatements(statements.filter(s => s.upload_id !== uploadId));
        setShowDeleteConfirm(null);
        
        // Show success message (you can add a toast notification here)
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
        return 'bg-green-100 text-green-800 border-green-200';
      case 'GEMINI_TEXT':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'GEMINI_VISION':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
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
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading statements...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={fetchStatements}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            📄 Bank Statements
          </h1>
          <p className="text-gray-600">
            View and manage all your processed bank statements
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Total Statements</p>
                <p className="text-3xl font-bold text-gray-900">{statements.length}</p>
              </div>
              <FileText className="w-12 h-12 text-blue-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Total Transactions</p>
                <p className="text-3xl font-bold text-gray-900">
                  {statements.reduce((sum, s) => sum + (s.total_transactions || 0), 0)}
                </p>
              </div>
              <TrendingUp className="w-12 h-12 text-green-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Avg Processing Time</p>
                <p className="text-3xl font-bold text-gray-900">
                  {statements.length > 0
                    ? (statements.reduce((sum, s) => sum + (s.processing_time_seconds || 0), 0) / statements.length).toFixed(1)
                    : 0}s
                </p>
              </div>
              <Clock className="w-12 h-12 text-purple-500 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Total Data Size</p>
                <p className="text-3xl font-bold text-gray-900">
                  {formatFileSize(statements.reduce((sum, s) => sum + (s.file_size_bytes || 0), 0))}
                </p>
              </div>
              <Database className="w-12 h-12 text-orange-500 opacity-20" />
            </div>
          </div>
        </div>

        {/* Statements List */}
        {statements.length === 0 ? (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Statements Yet</h3>
            <p className="text-gray-600 mb-6">Upload your first bank statement to get started</p>
            <button
              onClick={() => navigate('/upload')}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Upload Statement
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {statements.map((statement) => (
              <div
                key={statement.upload_id}
                className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <FileText className="w-8 h-8 text-blue-500" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold text-gray-900 mb-1">
                          {statement.filename}
                        </h3>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span className="flex items-center">
                            <Calendar className="w-4 h-4 mr-1" />
                            {formatDate(statement.uploaded_at)}
                          </span>
                          <span className="flex items-center">
                            {getStatusIcon(statement.status)}
                            <span className="ml-1 capitalize">{statement.status}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => navigate(`/statement/${statement.upload_id}`)}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(statement.upload_id)}
                        disabled={deletingId === statement.upload_id}
                        className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
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

                  {/* Delete Confirmation Modal */}
                  {showDeleteConfirm === statement.upload_id && (
                    <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                      <div className="flex items-start space-x-3">
                        <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                        <div className="flex-1">
                          <h4 className="font-semibold text-red-900 mb-1">
                            Confirm Deletion
                          </h4>
                          <p className="text-sm text-red-800 mb-3">
                            Are you sure you want to delete "{statement.filename}"? This will permanently remove:
                          </p>
                          <ul className="text-sm text-red-800 mb-3 space-y-1 ml-4">
                            <li>• {statement.total_transactions} transactions from database</li>
                            <li>• All search vectors from Pinecone</li>
                            <li>• Statement metadata and insights</li>
                          </ul>
                          <p className="text-sm font-semibold text-red-900 mb-3">
                            This action cannot be undone!
                          </p>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleDeleteStatement(statement.upload_id, statement.filename)}
                              disabled={deletingId === statement.upload_id}
                              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium disabled:opacity-50"
                            >
                              {deletingId === statement.upload_id ? 'Deleting...' : 'Yes, Delete'}
                            </button>
                            <button
                              onClick={() => setShowDeleteConfirm(null)}
                              disabled={deletingId === statement.upload_id}
                              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors text-sm font-medium disabled:opacity-50"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Metadata Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">Bank</p>
                      <p className="font-semibold text-gray-900">{statement.bank_name || 'Unknown'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">Transactions</p>
                      <p className="font-semibold text-gray-900">{statement.total_transactions}</p>
                    </div>
                    {statement.page_count && statement.page_count > 0 && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Pages</p>
                        <p className="font-semibold text-gray-900">{statement.page_count}</p>
                      </div>
                    )}
                    {statement.processing_time_seconds && statement.processing_time_seconds > 0 && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1">Processing Time</p>
                        <p className="font-semibold text-gray-900">
                          {statement.processing_time_seconds.toFixed(2)}s
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Extraction Method Badge */}
                  {statement.extraction_method && (
                    <div className="flex items-center space-x-2 mb-4">
                      <span className="text-sm text-gray-600">Extraction Method:</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getMethodBadgeColor(statement.extraction_method)}`}>
                        {statement.extraction_method}
                      </span>
                    </div>
                  )}

                  {/* AI Insights */}
                  {statement.insights && statement.insights.length > 0 && (
                    <div className="mt-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
                      <div className="flex items-center space-x-2 mb-3">
                        <TrendingUp className="w-5 h-5 text-purple-600" />
                        <h4 className="font-semibold text-purple-900">AI Insights</h4>
                      </div>
                      <ul className="space-y-2">
                        {statement.insights.slice(0, 3).map((insight, idx) => (
                          <li key={idx} className="text-sm text-purple-800 flex items-start space-x-2">
                            <span className="text-purple-600 mt-0.5">•</span>
                            <span>{insight}</span>
                          </li>
                        ))}
                      </ul>
                      {statement.insights.length > 3 && (
                        <button
                          onClick={() => navigate(`/statement/${statement.upload_id}`)}
                          className="mt-2 text-sm text-purple-600 hover:text-purple-700 font-medium"
                        >
                          View all {statement.insights.length} insights →
                        </button>
                      )}
                    </div>
                  )}

                  {/* Background Task Status */}
                  {(!statement.db_save_completed || !statement.vector_index_completed) && (
                    <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="flex items-center space-x-2">
                        <Loader className="w-4 h-4 text-yellow-600 animate-spin" />
                        <span className="text-sm text-yellow-800">
                          Background tasks in progress... 
                          {!statement.db_save_completed && " Saving to database..."}
                          {!statement.vector_index_completed && " Creating search vectors..."}
                        </span>
                      </div>
                    </div>
                  )}
                  {statement.db_save_completed && statement.vector_index_completed && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span className="text-sm text-green-800">
                          ✅ Fully processed! Ready for Q&A and analysis.
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
