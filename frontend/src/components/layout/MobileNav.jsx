import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Upload, 
  Receipt, 
  BarChart3, 
  MessageSquare 
} from 'lucide-react';

/**
 * MobileNav Component
 * Bottom navigation bar for mobile devices
 */
const MobileNav = () => {
  const location = useLocation();
  
  const navLinks = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/transactions', label: 'Transactions', icon: Receipt },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/chat', label: 'Chat', icon: MessageSquare }
  ];
  
  const isActive = (path) => location.pathname === path;
  
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-40 safe-area-bottom">
      <div className="flex items-center justify-around px-2 py-2">
        {navLinks.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.path);
          
          return (
            <Link
              key={link.path}
              to={link.path}
              className="flex flex-col items-center justify-center min-w-[60px] py-2 px-3 rounded-lg transition-colors"
            >
              <motion.div
                whileTap={{ scale: 0.9 }}
                className={`flex flex-col items-center ${
                  active ? 'text-indigo-600' : 'text-gray-600'
                }`}
              >
                <Icon size={24} className="mb-1" />
                <span className="text-xs font-medium">{link.label}</span>
              </motion.div>
              {active && (
                <motion.div
                  className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-12 h-1 bg-indigo-600 rounded-t-full"
                  layoutId="mobile-nav-indicator"
                  transition={{ duration: 0.3 }}
                />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
};

export default MobileNav;
