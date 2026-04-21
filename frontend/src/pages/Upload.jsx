import { useState, useEffect } from 'react'
import { Upload as UploadIcon, X, FileText, Lock, Loader2, Bell, BellOff, CheckCircle, AlertCircle, Zap, Database } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { statementAPI, statementsAPI } from '../services/api'
import LogViewer from '../components/LogViewer'
import EnhancedResultsCard from '../components/upload/EnhancedResultsCard'
import notificationManager from '../utils/notifications'
import { Button, Badge, Card, Skeleton } from '../components/ui'

const Upload = () => {
  const [files, setFiles] = useState([])
  const [passwords, setPasswords] = useState({})
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState(null)
  const [uploadId, setUploadId] = useState(null)
  const [showLogs, setShowLogs] = useState(false)
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  // Check notification permission on mount
  useEffect(() => {
    if ('Notification' in window) {
      setNotificationsEnabled(Notification.permission === 'granted')
    }
  }, [])

  const toggleNotifications = async () => {
    if (notificationsEnabled) {
      toast.info('Notifications are managed by your browser settings')
      return
    }

    const granted = await notificationManager.requestPermission()
    if (granted) {
      setNotificationsEnabled(true)
      toast.success('Notifications enabled!')
      notificationManager.info('🔔 Notifications Active', 'You\'ll be notified when processing completes')
    } else {
      toast.error('Notification permission denied')
    }
  }

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    const pdfFiles = selectedFiles.filter(file => file.type === 'application/pdf')

    if (pdfFiles.length !== selectedFiles.length) {
      toast.error('Only PDF files are allowed')
    }

    setFiles(prev => [...prev, ...pdfFiles])

    // Initialize passwords for new files
    const newPasswords = { ...passwords }
    pdfFiles.forEach(file => {
      if (!newPasswords[file.name]) {
        newPasswords[file.name] = ''
      }
    })
    setPasswords(newPasswords)
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    const pdfFiles = droppedFiles.filter(file => file.type === 'application/pdf')

    if (pdfFiles.length !== droppedFiles.length) {
      toast.error('Only PDF files are allowed')
    }

    setFiles(prev => [...prev, ...pdfFiles])

    // Initialize passwords for new files
    const newPasswords = { ...passwords }
    pdfFiles.forEach(file => {
      if (!newPasswords[file.name]) {
        newPasswords[file.name] = ''
      }
    })
    setPasswords(newPasswords)
  }

  const removeFile = (fileName) => {
    setFiles(files.filter(f => f.name !== fileName))
    const newPasswords = { ...passwords }
    delete newPasswords[fileName]
    setPasswords(newPasswords)
  }

  const handlePasswordChange = (fileName, password) => {
    setPasswords(prev => ({
      ...prev,
      [fileName]: password
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (files.length === 0) {
      toast.error('Please select at least one PDF file')
      return
    }

    // Check if all files have passwords
    const missingPasswords = files.filter(file => !passwords[file.name])
    if (missingPasswords.length > 0) {
      toast.error('Please provide passwords for all files')
      return
    }

    setProcessing(true)
    setResults(null)

    try {
      let response
      if (files.length === 1) {
        // Generate upload ID BEFORE API call for immediate log streaming
        const generatedUploadId = crypto.randomUUID ? crypto.randomUUID() : `upload-${Date.now()}`
        setUploadId(generatedUploadId)
        setShowLogs(true)

        // Show notification that processing started
        if (notificationsEnabled) {
          notificationManager.statementProcessing(files[0].name)
        }

        // Send the upload_id to backend so logs stream to the correct ID
        response = await statementAPI.processSingleStatement(
          files[0],
          passwords[files[0].name],
          generatedUploadId
        )

        // Show success notification
        if (notificationsEnabled && response.success) {
          notificationManager.statementComplete(
            files[0].name,
            response.transactions?.length || 0
          )
        }

        // HTTP response arrived with transactions — results are ready.
        // Ensure LogViewer closes and results display even if SSE never fires 'complete'.
        setTimeout(() => {
          setProcessing(false)
          setShowLogs(false)
        }, 1200)

      } else {
        // Multiple files upload - Generate upload ID for log streaming
        const generatedUploadId = crypto.randomUUID ? crypto.randomUUID() : `upload-${Date.now()}`
        setUploadId(generatedUploadId)
        setShowLogs(true)  // Show logs for multi-statement too!

        toast.loading(`Processing ${files.length} statements...`, { id: 'multi-upload', duration: Infinity })

        if (notificationsEnabled) {
          notificationManager.info(
            '📄 Processing Statements',
            `Processing ${files.length} statements...`
          )
        }

        const passwordArray = files.map(file => passwords[file.name])
        response = await statementAPI.processMultipleStatements(files, passwordArray, generatedUploadId)

        toast.dismiss('multi-upload')
        toast.success(`✅ Successfully processed ${files.length} statements!`)

        // Show success notification
        if (notificationsEnabled && response.status === 'success') {
          notificationManager.success(
            '✅ All Statements Processed!',
            `Successfully processed ${files.length} statements with ${response.total_transactions || 0} transactions`
          )
        }
      }

      setResults(response)

      // Extract transactions from response
      let allTransactions = []
      if (files.length === 1) {
        // Single file response
        allTransactions = response.transactions || []
      } else {
        // Multiple files response - backend returns "transactions" not "all_transactions"
        allTransactions = response.transactions || []
      }

      // Calculate stats
      const totalIncome = allTransactions.reduce((sum, t) => sum + (parseFloat(t.credit) || 0), 0)
      const totalExpenses = allTransactions.reduce((sum, t) => sum + (parseFloat(t.debit) || 0), 0)
      const balance = totalIncome - totalExpenses

      // Fetch fresh data from backend to ensure persistence
      try {
        const response = await statementsAPI.getAllStatements()
        const statements = response.statements || []
        let backendTransactions = []

        for (const statement of statements) {
          const details = await statementsAPI.getStatementDetails(statement.upload_id)
          if (details.transactions) {
            backendTransactions = [...backendTransactions, ...details.transactions]
          }
        }

        // Calculate stats from backend data
        const backendIncome = backendTransactions.reduce((sum, t) => sum + (parseFloat(t.credit) || 0), 0)
        const backendExpenses = backendTransactions.reduce((sum, t) => sum + (parseFloat(t.debit) || 0), 0)
        const backendBalance = backendIncome - backendExpenses

        // Save backend data to localStorage as cache
        const dashboardData = {
          stats: {
            totalTransactions: backendTransactions.length,
            totalIncome: backendIncome,
            totalExpenses: backendExpenses,
            balance: backendBalance,
          },
          allTransactions: backendTransactions.map(t => ({
            description: t.description || 'N/A',
            date: t.date || 'N/A',
            amount: parseFloat(t.credit || t.debit || 0),
            credit: parseFloat(t.credit || 0),
            debit: parseFloat(t.debit || 0),
            type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
            category: t.category || 'Uncategorized',
            balance: parseFloat(t.balance || 0)
          })),
          recentTransactions: backendTransactions.slice(0, 10).map(t => ({
            description: t.description || 'N/A',
            date: t.date || 'N/A',
            amount: parseFloat(t.credit || t.debit || 0),
            type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
            category: t.category || 'Uncategorized'
          }))
        }
        localStorage.setItem('dashboardData', JSON.stringify(dashboardData))

        console.log('✅ Saved backend data to localStorage:', {
          totalTransactions: backendTransactions.length,
          sampleTransaction: backendTransactions[0]
        })
      } catch (error) {
        console.error('Error fetching backend data:', error)
        // Fallback: save current upload data
        const dashboardData = {
          stats: {
            totalTransactions: allTransactions.length,
            totalIncome: totalIncome,
            totalExpenses: totalExpenses,
            balance: balance,
          },
          allTransactions: allTransactions.map(t => ({
            description: t.description || 'N/A',
            date: t.date || 'N/A',
            amount: parseFloat(t.credit || t.debit || 0),
            credit: parseFloat(t.credit || 0),
            debit: parseFloat(t.debit || 0),
            type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
            category: t.category || 'Uncategorized',
            balance: parseFloat(t.balance || 0)
          })),
          recentTransactions: allTransactions.slice(0, 10).map(t => ({
            description: t.description || 'N/A',
            date: t.date || 'N/A',
            amount: parseFloat(t.credit || t.debit || 0),
            type: parseFloat(t.credit || 0) > 0 ? 'credit' : 'debit',
            category: t.category || 'Uncategorized'
          }))
        }
        localStorage.setItem('dashboardData', JSON.stringify(dashboardData))
      }

      // Start polling for background task completion
      if (response.background_tasks_running && response.statement_details) {
        const uploadIds = response.statement_details.map(s => s.upload_id).filter(Boolean)
        if (uploadIds.length > 0) {
          pollBackgroundTasks(uploadIds)
        }
      }

      if (!showLogs) {
        toast.success(`Successfully processed ${allTransactions.length} transactions!`)
        if (response.background_tasks_running) {
          toast.info('💾 Saving to database and creating search vectors in background...', {
            duration: 5000
          })
        }
      }
    } catch (error) {
      console.error('Upload error:', error)
      toast.dismiss('multi-upload') // Dismiss loading toast if it exists
      toast.error(error.response?.data?.detail || 'Failed to process statement(s)')
      setShowLogs(false)
      setProcessing(false) // Always reset processing state on error
    } finally {
      // For multiple files, always reset processing state
      // For single file, it's handled by LogViewer's onComplete
      if (files.length > 1) {
        setProcessing(false)
        console.log('✅ Processing complete for multiple files')
      }
    }
  }

  const handleLogComplete = () => {
    setProcessing(false)
    setShowLogs(false)
    if (results) {
      toast.success(`Successfully processed ${results.total_transactions} transactions!`)
    }
  }

  const handleReset = () => {
    setFiles([])
    setPasswords({})
    setResults(null)
    setUploadId(null)
    setShowLogs(false)
    setProcessing(false)
  }

  const pollBackgroundTasks = async (uploadIds) => {
    /**
     * Poll backend to check when background tasks complete
     * Shows notification when all tasks are done
     */
    const checkStatus = async () => {
      try {
        const statusChecks = await Promise.all(
          uploadIds.map(id => statementsAPI.getBackgroundStatus(id))
        )

        const allCompleted = statusChecks.every(status => status.all_tasks_completed)

        if (allCompleted) {
          // All background tasks completed!
          toast.success('🎉 All background tasks completed! Your data is fully processed and ready for analysis.', {
            duration: 6000,
            style: {
              background: '#10b981',
              color: '#fff',
            },
          })

          // Show browser notification if enabled
          if (notificationsEnabled) {
            notificationManager.success(
              '🎉 Processing Complete!',
              'All background tasks finished. Your statements are ready for Q&A!'
            )
          }

          return true // Stop polling
        }

        return false // Continue polling
      } catch (error) {
        console.error('Error checking background status:', error)
        return true // Stop polling on error
      }
    }

    // Poll every 3 seconds for up to 2 minutes
    let attempts = 0
    const maxAttempts = 40 // 40 * 3s = 2 minutes

    const pollInterval = setInterval(async () => {
      attempts++
      const shouldStop = await checkStatus()

      if (shouldStop || attempts >= maxAttempts) {
        clearInterval(pollInterval)
        if (attempts >= maxAttempts) {
          console.log('Background task polling timed out')
        }
      }
    }, 3000) // Check every 3 seconds
  }

  return (
    <div className="space-y-6">
      {/* Show LogViewer when processing single file */}
      {showLogs && uploadId ? (
        <LogViewer uploadId={uploadId} onComplete={handleLogComplete} />
      ) : (
        <>
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary-600 via-primary-700 to-primary-800 p-8 border border-primary-500/20 shadow-2xl"
          >
            <div className="absolute inset-0 opacity-10">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full mix-blend-overlay filter blur-3xl animate-pulse"></div>
            </div>
            <div className="relative flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                  <UploadIcon className="w-10 h-10" />
                  Upload Statements
                </h1>
                <p className="text-white/95 text-lg font-medium">Upload single or multiple bank statements here</p>
              </div>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleNotifications}
                className={`hidden md:flex items-center gap-2 px-6 py-3 rounded-xl font-semibold border-2 transition-all shadow-lg ${notificationsEnabled
                  ? 'bg-green-500 border-green-400 text-white hover:bg-green-600'
                  : 'bg-white border-white text-primary-700 hover:bg-neutral-50'
                  }`}
              >
                {notificationsEnabled ? (
                  <>
                    <Bell className="w-5 h-5" />
                    Notifications On
                  </>
                ) : (
                  <>
                    <BellOff className="w-5 h-5" />
                    Enable Notifications
                  </>
                )}
              </motion.button>
            </div>
          </motion.div>

          {/* Upload Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Drop Zone - Modern Glassmorphism */}
              <motion.div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                whileHover={{ scale: 1.01 }}
                className={`relative overflow-hidden rounded-3xl border-2 border-dashed transition-all shadow-lg ${dragActive
                  ? 'border-primary-500 bg-primary-50 shadow-2xl'
                  : 'border-neutral-300 bg-white/80 backdrop-blur-sm hover:border-primary-400 hover:bg-white'
                  }`}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-primary-50/30 to-transparent"></div>
                <div className="relative p-12 text-center">
                  <input
                    type="file"
                    id="file-upload"
                    multiple
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                    disabled={processing}
                  />
                  <label htmlFor="file-upload" className="cursor-pointer block">
                    <motion.div
                      animate={{ y: dragActive ? -5 : 0 }}
                      className="w-20 h-20 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg"
                    >
                      <FileText className="w-10 h-10 text-white" />
                    </motion.div>
                    <p className="text-2xl font-bold text-neutral-900 mb-2">
                      {dragActive ? 'Drop files here' : 'Click to upload or drag and drop'}
                    </p>
                    <p className="text-neutral-600 mb-4">
                      PDF files only • Multiple files supported • Max 50MB per file
                    </p>
                    <div className="flex items-center justify-center gap-4 text-sm text-neutral-500">
                      <div className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        Bank Statements
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        Credit Cards
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        EMI & Policies
                      </div>
                    </div>
                  </label>
                </div>
              </motion.div>

              {/* File List - Modern Cards */}
              <AnimatePresence>
                {files.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-4"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-neutral-900">Selected Files ({files.length})</h3>
                      <span className="text-sm text-neutral-600 font-medium">
                        {(files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(2)} MB total
                      </span>
                    </div>

                    <div className="space-y-3">
                      {files.map((file, index) => (
                        <motion.div
                          key={file.name}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.05 }}
                          whileHover={{ x: 5 }}
                          className="group relative overflow-hidden rounded-2xl bg-white/90 backdrop-blur-sm border border-neutral-200 p-4 shadow-lg hover:shadow-xl transition-all"
                        >
                          <div className="absolute inset-0 bg-gradient-to-r from-primary-50/0 to-primary-100/0 group-hover:from-primary-50/50 group-hover:to-primary-100/50 transition-all"></div>
                          <div className="relative flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                              <FileText className="w-6 h-6 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-neutral-900 truncate">{file.name}</p>
                              <p className="text-sm text-neutral-600 font-medium">
                                {(file.size / 1024).toFixed(2)} KB
                              </p>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0">
                              <div className="relative">
                                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
                                <input
                                  type="password"
                                  placeholder="Password (if needed)"
                                  value={passwords[file.name] || ''}
                                  onChange={(e) => handlePasswordChange(file.name, e.target.value)}
                                  className="pl-10 pr-4 py-2 bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-lg focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent outline-none w-48 text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)]"
                                  disabled={processing}
                                />
                              </div>
                              <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                type="button"
                                onClick={() => removeFile(file.name)}
                                className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                                disabled={processing}
                              >
                                <X className="w-5 h-5 text-red-500" />
                              </motion.button>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Action Buttons */}
              {files.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-4 pt-4"
                >
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    loading={processing}
                    icon={Zap}
                    iconPosition="left"
                    fullWidth
                    className="flex-1"
                  >
                    Process {files.length} {files.length === 1 ? 'Statement' : 'Statements'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="lg"
                    onClick={handleReset}
                    disabled={processing}
                    className="px-8"
                  >
                    Reset
                  </Button>
                </motion.div>
              )}
            </form>

            {/* Info Cards */}
            {files.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid md:grid-cols-3 gap-4"
              >
                <div className="rounded-2xl bg-white/90 backdrop-blur-sm border border-neutral-200 p-6 shadow-lg">
                  <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center mb-4">
                    <Zap className="w-6 h-6 text-blue-600" />
                  </div>
                  <h4 className="font-bold text-neutral-900 mb-2">Fast Processing</h4>
                  <p className="text-sm text-neutral-600 font-medium">Process statements in under 2 seconds with AI-powered extraction</p>
                </div>
                <div className="rounded-2xl bg-white/90 backdrop-blur-sm border border-neutral-200 p-6 shadow-lg">
                  <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center mb-4">
                    <Database className="w-6 h-6 text-purple-600" />
                  </div>
                  <h4 className="font-bold text-neutral-900 mb-2">Secure Storage</h4>
                  <p className="text-sm text-neutral-600 font-medium">Bank-level encryption for all your financial data</p>
                </div>
                <div className="rounded-2xl bg-white/90 backdrop-blur-sm border border-neutral-200 p-6 shadow-lg">
                  <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center mb-4">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <h4 className="font-bold text-neutral-900 mb-2">99.9% Accuracy</h4>
                  <p className="text-sm text-neutral-600 font-medium">Advanced AI ensures accurate transaction categorization</p>
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* Results - Enhanced Results Card */}
          <AnimatePresence>
            {results && (
              <EnhancedResultsCard
                results={results}
                metadata={results.metadata}
                onReset={handleReset}
              />
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  )
}

export default Upload
