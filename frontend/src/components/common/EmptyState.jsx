import { motion } from 'framer-motion';
import { fadeIn } from '../../utils/animations';
import Button from './Button';

/**
 * EmptyState Component
 * Displays a friendly empty state with icon, message, and optional action
 * 
 * @param {React.Component} icon - Icon component from lucide-react
 * @param {string} title - Main heading
 * @param {string} message - Descriptive message
 * @param {string} actionLabel - Button text
 * @param {function} onAction - Button click handler
 * @param {string} className - Additional CSS classes
 */
const EmptyState = ({
  icon: Icon,
  title,
  message,
  actionLabel,
  onAction,
  className = ''
}) => {
  return (
    <motion.div
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}
    >
      {/* Icon */}
      {Icon && (
        <div className="mb-6 p-6 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-full">
          <Icon size={64} className="text-indigo-400" strokeWidth={1.5} />
        </div>
      )}
      
      {/* Title */}
      {title && (
        <h3 className="text-2xl font-semibold text-gray-900 mb-3">
          {title}
        </h3>
      )}
      
      {/* Message */}
      {message && (
        <p className="text-gray-600 max-w-md mb-8">
          {message}
        </p>
      )}
      
      {/* Action Button */}
      {actionLabel && onAction && (
        <Button
          variant="primary"
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      )}
    </motion.div>
  );
};

export default EmptyState;
