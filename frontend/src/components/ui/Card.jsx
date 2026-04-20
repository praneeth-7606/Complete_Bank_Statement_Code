import { motion } from 'framer-motion'

/**
 * Unified Card Component - Design System v2.0
 * Single card component used across ALL pages
 * 
 * Variants:
 * - default: Standard white card with subtle shadow
 * - elevated: Card with more prominent shadow
 * - bordered: Card with border instead of shadow
 * - glass: Glassmorphism effect (for special sections)
 */
const Card = ({
  variant = 'default',
  padding = 'md',
  hover = false,
  clickable = false,
  className = '',
  onClick,
  children,
  ...props
}) => {
  const baseStyles = 'rounded-2xl transition-all duration-200'
  
  const variantStyles = {
    default: 'bg-white shadow-md',
    elevated: 'bg-white shadow-lg hover:shadow-xl',
    bordered: 'bg-white border-2 border-neutral-200',
    glass: 'bg-white/80 backdrop-blur-lg shadow-xl border border-white/20'
  }
  
  const paddingStyles = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }
  
  const interactiveStyles = (clickable || onClick) ? 'cursor-pointer' : ''
  const hoverStyles = hover ? 'hover:shadow-xl hover:-translate-y-1' : ''
  
  const cardClasses = `${baseStyles} ${variantStyles[variant]} ${paddingStyles[padding]} ${interactiveStyles} ${hoverStyles} ${className}`
  
  if (hover || clickable) {
    return (
      <motion.div
        className={cardClasses}
        onClick={onClick}
        whileHover={{ y: -4 }}
        transition={{ type: 'spring', stiffness: 300 }}
        {...props}
      >
        {children}
      </motion.div>
    )
  }
  
  return (
    <div className={cardClasses} onClick={onClick} {...props}>
      {children}
    </div>
  )
}

export default Card
