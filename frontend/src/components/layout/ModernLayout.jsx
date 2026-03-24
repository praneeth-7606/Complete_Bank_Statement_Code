import { motion } from 'framer-motion';
import Navbar from './Navbar';
import { pageTransition } from '../../utils/animations';

/**
 * ModernLayout Component
 * New modern layout with updated Navbar
 */
const ModernLayout = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* New Navbar */}
      <Navbar />
      
      {/* Main Content */}
      <motion.main
        className="pt-16 sm:pt-18 lg:pt-20 px-3 sm:px-4 md:px-6 lg:px-8 xl:px-12 pb-8 sm:pb-10 lg:pb-12"
        {...pageTransition}
      >
        <div className="max-w-7xl lg:max-w-6xl xl:max-w-7xl 2xl:max-w-full 2xl:px-32 mx-auto">
          {children}
        </div>
      </motion.main>
    </div>
  );
};

export default ModernLayout;
