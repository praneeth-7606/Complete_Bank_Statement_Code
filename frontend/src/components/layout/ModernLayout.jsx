import { motion } from 'framer-motion';
import Navbar from './Navbar';
import { pageTransition } from '../../utils/animations';

/**
 * ModernLayout Component
 * New modern layout with updated Navbar
 */
const ModernLayout = ({ children }) => {
  return (
    <div className="min-h-screen text-[var(--text-primary)] transition-colors duration-300">
      {/* New Navbar */}
      <Navbar />

      {/* Main Content */}
      <motion.main
        className="pt-16 sm:pt-20 pb-8 sm:pb-12"
        {...pageTransition}
      >
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
          {children}
        </div>
      </motion.main>
    </div>
  );
};

export default ModernLayout;
