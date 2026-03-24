import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * LoadingSpinner Component
 * Displays an animated loading spinner
 * 
 * @param {string} size - Size of the spinner ('sm', 'md', 'lg', 'xl')
 * @param {string} color - Color of the spinner ('primary', 'white', 'gray')
 * @param {string} text - Optional loading text to display
 * @param {boolean} fullScreen - Whether to display as full screen overlay
 */
const LoadingSpinner = ({
  size = 'md',
  color = 'primary',
  text = '',
  fullScreen = false,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  };

  const colorClasses = {
    primary: 'text-blue-600',
    white: 'text-white',
    gray: 'text-gray-600',
    success: 'text-green-600',
    danger: 'text-red-600',
  };

  const spinner = (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2
        className={`${sizeClasses[size]} ${colorClasses[color]} animate-spin`}
      />
      {text && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`text-sm font-medium ${
            color === 'white' ? 'text-white' : 'text-gray-600'
          }`}
        >
          {text}
        </motion.p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50"
      >
        {spinner}
      </motion.div>
    );
  }

  return spinner;
};

export default LoadingSpinner;
