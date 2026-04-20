import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Upload, List, MessageSquare, BarChart3, Settings, Menu, X, DollarSign, Bell, User, LogOut, FileText, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuth()

  // Restore sidebar collapsed state from localStorage on mount
  useEffect(() => {
    const savedState = localStorage.getItem('sidebarCollapsed')
    if (savedState !== null) {
      setSidebarCollapsed(JSON.parse(savedState))
    }
  }, [])

  // Toggle sidebar collapsed state and persist to localStorage
  const handleToggleCollapse = () => {
    const newState = !sidebarCollapsed
    setSidebarCollapsed(newState)
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newState))
  }

  const navigation = [
    { name: 'Home', href: '/', icon: DollarSign },
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Statements', href: '/statements', icon: FileText },
    { name: 'Transactions', href: '/transactions', icon: List },
    { name: 'AI Assistant', href: '/chat', icon: MessageSquare },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    { name: 'Settings', href: '/corrections', icon: Settings },
  ]

  const isActive = (path) => location.pathname === path

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-primary-50/30 to-neutral-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/30 backdrop-blur-md z-40 lg:hidden transition-all duration-300"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed top-0 left-0 z-50 h-full bg-white border-r border-neutral-200 shadow-xl transition-all duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 ${sidebarCollapsed ? 'lg:w-16' : 'lg:w-64'} w-64`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className={`flex items-center gap-3 border-b border-neutral-200 bg-gradient-to-r from-primary-50 to-primary-100/50 transition-all duration-300 ${sidebarCollapsed ? 'px-2 py-4 justify-center' : 'px-6 py-6'}`}>
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            {!sidebarCollapsed && (
              <div className="overflow-hidden">
                <h1 className="text-xl font-bold bg-gradient-to-r from-primary-600 to-primary-700 bg-clip-text text-transparent whitespace-nowrap">FinanceAI</h1>
                <p className="text-xs text-primary-600 whitespace-nowrap">Smart Finance</p>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className={`flex-1 py-6 space-y-1 overflow-y-auto transition-all duration-300 ${sidebarCollapsed ? 'px-2' : 'px-4'}`}>
            {navigation.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center rounded-xl transition-all ${
                    sidebarCollapsed ? 'justify-center px-2 py-3' : 'gap-3 px-4 py-3'
                  } ${
                    active
                      ? 'bg-gradient-to-r from-primary-100 to-primary-50 text-primary-700 font-semibold shadow-sm'
                      : 'text-neutral-700 hover:bg-neutral-50'
                  }`}
                  title={sidebarCollapsed ? item.name : ''}
                >
                  <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-primary-600' : 'text-neutral-500'}`} />
                  {!sidebarCollapsed && <span className="whitespace-nowrap overflow-hidden">{item.name}</span>}
                </Link>
              )
            })}
          </nav>

          {/* Toggle Button - Desktop Only */}
          <div className={`hidden lg:block border-t border-neutral-200 transition-all duration-300 ${sidebarCollapsed ? 'px-2 py-3' : 'px-4 py-3'}`}>
            <button
              onClick={handleToggleCollapse}
              className={`w-full flex items-center rounded-xl transition-all hover:bg-primary-50 text-primary-600 ${sidebarCollapsed ? 'justify-center px-2 py-2' : 'gap-2 px-4 py-2'}`}
              title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
              aria-label={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="w-5 h-5 flex-shrink-0" />
              ) : (
                <>
                  <ChevronLeft className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm font-medium">Collapse</span>
                </>
              )}
            </button>
          </div>

          {/* User Profile & Logout */}
          <div className={`border-t border-neutral-200 transition-all duration-300 ${sidebarCollapsed ? 'px-2 py-4' : 'px-4 py-4'}`}>
            <div className={`flex items-center mb-3 ${sidebarCollapsed ? 'justify-center' : 'gap-3'}`}>
              {user?.profile_picture ? (
                <img src={user.profile_picture} alt={user.full_name} className="w-10 h-10 rounded-full flex-shrink-0" title={sidebarCollapsed ? user.full_name : ''} />
              ) : (
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center flex-shrink-0" title={sidebarCollapsed ? user?.full_name : ''}>
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
              {!sidebarCollapsed && (
                <div className="flex-1 min-w-0 overflow-hidden">
                  <p className="text-sm font-semibold text-neutral-900 truncate">{user?.full_name}</p>
                  <p className="text-xs text-neutral-500 truncate">{user?.email}</p>
                </div>
              )}
            </div>
            <button
              onClick={logout}
              className={`w-full flex items-center rounded-xl transition-colors text-red-600 hover:bg-red-50 ${sidebarCollapsed ? 'justify-center px-2 py-2' : 'gap-2 px-4 py-2'}`}
              title={sidebarCollapsed ? 'Logout' : ''}
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              {!sidebarCollapsed && <span className="text-sm">Logout</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'}`}>
        {/* Top bar */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-lg border-b border-neutral-200 px-4 lg:px-8 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-neutral-100"
            >
              {sidebarOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
            
            <div className="flex-1 lg:flex-none">
              <h2 className="text-xl font-semibold text-neutral-900">
                {navigation.find(item => item.href === location.pathname)?.name || 'Dashboard'}
              </h2>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden sm:block text-sm text-neutral-600">
                AI-Powered Analysis
              </div>
            </div>
          </div>
        </header>

        {/* Page content - PROPERLY CENTERED */}
        <main className="p-4 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
