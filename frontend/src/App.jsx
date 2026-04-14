import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import ModernLayout from './components/layout/ModernLayout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Home from './pages/Home'
import FinancialDashboard from './pages/FinancialDashboard'
import Upload from './pages/Upload'
import Transactions from './pages/Transactions'
import Chat from './pages/Chat'
import Analytics from './pages/Analytics'
import Corrections from './pages/Corrections'
import Statements from './pages/Statements'
import StatementDetails from './pages/StatementDetails'
import InvestmentChat from './pages/InvestmentChat'

// Replace with your actual Google Client ID
// Leave empty to disable Google OAuth (email/password will still work)
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Protected Routes - Using NEW ModernLayout */}
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
          </Routes>
        </AuthProvider>
      </Router>
    </GoogleOAuthProvider>
  )
}

export default App
