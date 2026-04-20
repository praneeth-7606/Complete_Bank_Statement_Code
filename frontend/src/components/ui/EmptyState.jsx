import { motion } from 'framer-motion'
import Button from './Button'

/**
 * Unified Empty State Component - Design System v2.0
 * Consistent empty states across all pages
 */
const EmptyState = ({
  icon: Icon,
  title,
  description,
  action,
  actionLabel,
  className = '',
  ...props
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}
      {...props}
    >
      {Icon && (
        <div className="w-16 h-16 mb-4 rounded-2xl bg-neutral-100 flex items-center justify-center">
          <Icon className="w-8 h-8 text-neutral-400" />
        </div>
      )}
      
      {title && (
        <h3 className="text-xl font-bold text-neutral-900 mb-2">
          {title}
        </h3>
      )}
      
      {description && (
        <p className="text-neutral-600 mb-6 max-w-md">
          {description}
        </p>
      )}
      
      {action && actionLabel && (
        <Button onClick={action} variant="primary">
          {actionLabel}
        </Button>
      )}
    </motion.div>
  )
}

export default EmptyState
