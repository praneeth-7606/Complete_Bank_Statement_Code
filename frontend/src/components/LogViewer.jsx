// frontend/src/components/LogViewer.jsx - Beautiful real-time log viewer

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { 
  CheckCircle, 
  AlertCircle, 
  Info, 
  Loader, 
  AlertTriangle,
  Sparkles,
  Database,
  Search
} from 'lucide-react';
import ProcessingStages from './processing/ProcessingStages';
import notificationManager from '../utils/notifications';

const LogViewer = ({ uploadId, onComplete }) => {
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);
  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    if (!uploadId) return;

    // Connect to SSE endpoint
    const eventSource = new EventSource(
      `http://localhost:8080/stream-logs/${uploadId}`
    );
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const logEntry = JSON.parse(event.data);
        
        // Update logs
        setLogs((prevLogs) => [...prevLogs, logEntry]);
        
        // Update progress
        if (logEntry.progress !== null && logEntry.progress !== undefined) {
          setProgress(logEntry.progress);
        }
        
        // Show notifications for background task completion
        if (logEntry.message && logEntry.message.includes('Database save completed')) {
          toast.success('💾 Database save completed!', {
            icon: <Database className="w-5 h-5" />,
            duration: 4000,
          });
          notificationManager.backgroundTaskComplete('Database Save');
        }
        
        if (logEntry.message && logEntry.message.includes('Vector indexing completed')) {
          toast.success('🔍 Search vectors created! You can now ask questions.', {
            icon: <Search className="w-5 h-5" />,
            duration: 5000,
          });
          notificationManager.backgroundTaskComplete('Vector Indexing');
        }
        
        if (logEntry.message && logEntry.message.includes('All background tasks completed')) {
          toast.success('🎉 All done! Your statement is fully processed and ready for Q&A.', {
            icon: <Sparkles className="w-5 h-5" />,
            duration: 6000,
            style: { background: '#10b981', color: '#fff' },
          });
          notificationManager.success(
            '🎉 Processing Complete!',
            'Your statement is fully processed and ready for analysis'
          );
        }
        
        // ── COMPLETION DETECTION ────────────────────────────────────────────
        // Accept both the old 'complete' level AND progress >= 98 (new backend)
        // The backend sends level:'success' at 98% and level:'info' at 100%.
        const isProgressComplete = logEntry.progress !== undefined && logEntry.progress >= 98;
        if (logEntry.level === 'complete' || isProgressComplete) {
          setIsComplete(true);
          setProgress(100);
          eventSource.close();
          if (onComplete) {
            setTimeout(() => onComplete(), 800); // brief delay so user sees 100%
          }
        }
        
        // Check for backend errors
        if (logEntry.level === 'error') {
          setError(logEntry.message);
        }
      } catch (err) {
        console.error('Error parsing log:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
      
      if (eventSource.readyState === EventSource.CLOSED) {
        // If we already received logs, the stream closed normally (processing done)
        // Use functional state read via setTimeout to get latest logs value
        setTimeout(() => {
          setLogs((currentLogs) => {
            if (currentLogs.length > 0) {
              // Stream closed after getting logs — treat as complete
              setIsComplete(true);
              setProgress((p) => Math.max(p, 100));
              if (onComplete) onComplete();
            } else {
              setError('Waiting for processing to start...');
            }
            return currentLogs; // return unchanged
          });
        }, 2000);
        return;
      }
      
      // Only show error if we haven't received any logs yet
      if (logs.length === 0) {
        setTimeout(() => {
          if (logs.length === 0 && eventSource.readyState !== EventSource.OPEN) {
            setError('Waiting for processing to start...');
          }
        }, 2000);
      }
    };

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [uploadId, onComplete]);

  // Auto-scroll to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogIcon = (level) => {
    switch (level) {
      case 'success':
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'info':
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const getLogColor = (level) => {
    switch (level) {
      case 'success':
      case 'complete':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'error':
        return 'text-red-700 bg-red-50 border-red-200';
      case 'warning':
        return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'info':
      default:
        return 'text-blue-700 bg-blue-50 border-blue-200';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-5xl mx-auto"
    >
      {/* Header */}
      <div className="bg-white rounded-t-xl shadow-lg p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <motion.h2
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-2xl font-bold text-gray-900 flex items-center"
          >
            {isComplete ? (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1, rotate: 360 }}
                  transition={{ type: 'spring', stiffness: 200 }}
                >
                  <Sparkles className="w-6 h-6 text-green-500 mr-2" />
                </motion.div>
                Processing Complete!
              </>
            ) : (
              <>
                <Loader className="w-6 h-6 text-blue-500 animate-spin mr-2" />
                Processing Your Statement
              </>
            )}
          </motion.h2>
          <motion.span
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-sm font-semibold text-gray-600 bg-gray-100 px-3 py-1 rounded-full"
          >
            {progress}% Complete
          </motion.span>
        </div>

        {/* Processing Stages */}
        <ProcessingStages progress={progress} />

        {/* Enhanced Progress Bar */}
        <div className="relative w-full h-4 bg-gray-200 rounded-full overflow-hidden shadow-inner">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className={`absolute top-0 left-0 h-full ${
              isComplete
                ? 'bg-gradient-to-r from-green-400 via-green-500 to-green-600'
                : 'bg-gradient-to-r from-blue-400 via-purple-500 to-purple-600'
            }`}
          >
            {/* Shimmer Effect */}
            {!isComplete && (
              <motion.div
                animate={{
                  x: ['-100%', '200%'],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: 'linear',
                }}
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30"
                style={{ width: '50%' }}
              />
            )}
          </motion.div>
        </div>
      </div>

      {/* Logs Container */}
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-b-xl shadow-lg p-6 max-h-96 overflow-y-auto">
        <div className="space-y-2 font-mono text-sm">
          {logs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-gray-400 text-center py-8"
            >
              <Loader className="w-8 h-8 animate-spin mx-auto mb-2" />
              <p>Waiting for logs...</p>
            </motion.div>
          ) : (
            <AnimatePresence>
              {logs.map((log, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex items-start space-x-3 p-3 rounded-lg border transition-all duration-300 ${getLogColor(
                    log.level
                  )}`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {getLogIcon(log.level)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      {log.timestamp && (
                        <span className="text-xs opacity-70 font-semibold">
                          {log.timestamp}
                        </span>
                      )}
                      <span className="text-sm break-words">{log.message}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red-900">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Complete Actions */}
      <AnimatePresence>
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mt-6 flex items-center justify-center space-x-4"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => window.location.href = '/transactions'}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-300 shadow-lg hover:shadow-xl"
            >
              View Transactions
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => window.location.href = '/upload'}
              className="px-6 py-3 bg-white text-gray-700 rounded-lg hover:bg-gray-50 transition-all duration-300 shadow-lg border border-gray-200"
            >
              Upload Another
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default LogViewer;
