import { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import ModernLayout from './components/layout/ModernLayout'

// Route-level code splitting: each page loads on demand
const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/Signup'))
const Home = lazy(() => import('./pages/Home'))
const FinancialDashboard = lazy(() => import('./pages/FinancialDashboard'))
const Upload = lazy(() => import('./pages/Upload'))
const Transactions = lazy(() => import('./pages/Transactions'))
const Chat = lazy(() => import('./pages/Chat'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Corrections = lazy(() => import('./pages/Corrections'))
const Statements = lazy(() => import('./pages/Statements'))
const StatementDetails = lazy(() => import('./pages/StatementDetails'))
const InvestmentChat = lazy(() => import('./pages/InvestmentChat'))
const Observability = lazy(() => import('./pages/Observability'))

function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" role="status" aria-label="Loading page" />
    </div>
  )
}

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ThemeProvider>
        <AuthProvider>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  duration: 3000,
                  iconTheme: {
                    primary: '#10b981',
                    secondary: '#fff',
                  },
                },
                error: {
                  duration: 4000,
                  iconTheme: {
                    primary: '#ef4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
            <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              <Route path="/" element={
                <ProtectedRoute>
                  <ModernLayout><Home /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/dashboard" element={
                <ProtectedRoute>
                  <ModernLayout><FinancialDashboard /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/upload" element={
                <ProtectedRoute>
                  <ModernLayout><Upload /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/transactions" element={
                <ProtectedRoute>
                  <ModernLayout><Transactions /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/chat" element={
                <ProtectedRoute>
                  <ModernLayout><Chat /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/analytics" element={
                <ProtectedRoute>
                  <ModernLayout><Analytics /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/corrections" element={
                <ProtectedRoute>
                  <ModernLayout><Corrections /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/statements" element={
                <ProtectedRoute>
                  <ModernLayout><Statements /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/statement/:uploadId" element={
                <ProtectedRoute>
                  <ModernLayout><StatementDetails /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/investment" element={
                <ProtectedRoute>
                  <ModernLayout><InvestmentChat /></ModernLayout>
                </ProtectedRoute>
              } />
              <Route path="/observability" element={
                <ProtectedRoute>
                  <ModernLayout><Observability /></ModernLayout>
                </ProtectedRoute>
              } />
            </Routes>
            </Suspense>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  )
}

export default App
