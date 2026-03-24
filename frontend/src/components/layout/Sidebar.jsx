import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Upload, 
  Receipt, 
  BarChart3, 
  MessageSquare, 
  FileText,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

/**
 * Sidebar Component
 * Desktop sidebar navigation with collapsible behavior
 */
const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const location = useLocation();
  
  const navLinks = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/transactions', label: 'Transactions', icon: Receipt },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/chat', label: 'Chat', icon: MessageSquare },
    { path: '/statements', label: 'Statements', icon: FileText }
  ];
  
  const isActive = (path) => location.pathname === path;
  
  return (
    <motion.aside
      className={`hidden lg:flex fixed left-0 top-16 bottom-0 bg-white border-r border-gray-200 flex-col transition-all duration-300 ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
      initial={{ x: -100 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Navigation Links */}
      <nav className="flex-1 py-6 px-3 space-y-2 overflow-y-auto">
        {navLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.path);
          
          return (
            <Link
              key={link.path}
              to={link.path}
              className={`relative flex items-center rounded-lg transition-all duration-200 ${
                isCollapsed ? 'justify-center px-3 py-3' : 'px-4 py-3 space-x-3'
              } ${
                active
                  ? 'bg-indigo-50 text-indigo-600'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
              title={isCollapsed ? link.label : ''}
            >
              <Icon size={20} className="flex-shrink-0" />
              {!isCollapsed && (
                <span className="font-medium">{link.label}</span>
              )}
              {active && !isCollapsed && (
                <motion.div
                  className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-600 rounded-r"
                  layoutId="sidebar-indicator"
                  transition={{ duration: 0.3 }}
                />
              )}
            </Link>
          );
        })}
      </nav>
      
      {/* Collapse Toggle */}
      <div className="p-3 border-t border-gray-200">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`w-full flex items-center rounded-lg px-4 py-3 text-gray-600 hover:bg-gray-100 transition-colors ${
            isCollapsed ? 'justify-center' : 'space-x-3'
          }`}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight size={20} />
          ) : (
            <>
              <ChevronLeft size={20} />
              <span className="text-sm font-medium">Collapse</span>
            </>
          )}
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
