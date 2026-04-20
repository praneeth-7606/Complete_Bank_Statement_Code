import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Menu,
  X,
  LayoutDashboard,
  Upload,
  Receipt,
  BarChart3,
  MessageSquare,
  FileText,
  User,
  LogOut,
  Settings,
  TrendingUp,
  Sun,
  Moon
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';

/**
 * Navbar Component
 * Main navigation bar with scroll effects and user dropdown
 */
const Navbar = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Navigation links for authenticated users
  const navLinks = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/transactions', label: 'Transactions', icon: Receipt },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/chat', label: 'Chat', icon: MessageSquare },
    { path: '/investment', label: 'Investments', icon: TrendingUp },
    { path: '/statements', label: 'Statements', icon: FileText }
  ];

  // Check if link is active
  const isActive = (path) => location.pathname === path;

  // Handle logout
  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <motion.nav
      className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${isScrolled
        ? 'bg-[var(--nav-bg)] backdrop-blur-lg border-b border-[var(--border-subtle)]'
        : 'bg-transparent'
        }`}
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to={user ? '/dashboard' : '/'} className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-xl">F</span>
            </div>
            <span className="text-xl font-bold gradient-text">FinanceAI</span>
          </Link>

          {/* Desktop Navigation */}
          {user && (
            <div className="hidden md:flex items-center space-x-1">
              {navLinks.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    className={`relative px-4 py-2 rounded-lg transition-colors ${isActive(link.path)
                      ? 'text-indigo-400'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    <div className="flex items-center space-x-2">
                      <Icon size={18} />
                      <span className="font-medium">{link.label}</span>
                    </div>
                    {isActive(link.path) && (
                      <motion.div
                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-indigo-500 to-purple-600"
                        layoutId="navbar-indicator"
                        transition={{ duration: 0.3 }}
                      />
                    )}
                  </Link>
                );
              })}
            </div>
          )}

          {/* Right Side */}
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                {/* Theme Toggle */}
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-lg hover:bg-[var(--bg-card)] transition-colors text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
                >
                  {isDark ? <Sun size={20} /> : <Moon size={20} />}
                </button>

                {/* Profile Dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsProfileOpen(!isProfileOpen)}
                    className="flex items-center space-x-2 p-2 rounded-lg hover:bg-[var(--bg-card)] transition-colors"
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
                      <User size={16} className="text-white" />
                    </div>
                    <span className="hidden md:block text-sm font-medium text-[var(--text-primary)]">
                      {user.email?.split('@')[0]}
                    </span>
                  </button>

                  {/* Dropdown Menu */}
                  {isProfileOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -10 }}
                      className="absolute right-0 mt-2 w-48 bg-[var(--bg-surface)] rounded-xl shadow-2xl border border-[var(--border-subtle)] py-2 scrollbar-hide"
                    >
                      <div className="px-4 py-2 border-b border-[var(--border-subtle)]">
                        <p className="text-sm font-medium text-[var(--text-primary)]">{user.email}</p>
                      </div>
                      <button
                        onClick={() => navigate('/settings')}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-card)] transition-colors"
                      >
                        <Settings size={16} />
                        <span>Settings</span>
                      </button>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-rose-400 hover:bg-rose-500/10 transition-colors"
                      >
                        <LogOut size={16} />
                        <span>Logout</span>
                      </button>
                    </motion.div>
                  )}
                </div>

                {/* Mobile Menu Button */}
                <button
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                  className="md:hidden p-2 rounded-lg hover:bg-[var(--bg-card)] transition-colors text-[var(--text-primary)]"
                >
                  {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
              </>
            ) : (
              <div className="flex items-center space-x-4">
                <Link
                  to="/login"
                  className="text-gray-700 hover:text-indigo-600 font-medium transition-colors"
                >
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="btn-primary"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {user && isMobileMenuOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="md:hidden bg-[var(--bg-surface)] border-t border-[var(--border-subtle)]"
        >
          <div className="px-4 py-4 space-y-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${isActive(link.path)
                    ? 'bg-indigo-500/10 text-indigo-400'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-card)]'
                    }`}
                >
                  <Icon size={20} />
                  <span className="font-medium">{link.label}</span>
                </Link>
              );
            })}
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
};

export default Navbar;
