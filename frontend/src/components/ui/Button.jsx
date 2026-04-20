import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { designTokens } from '../../lib/design-tokens'

/**
 * Unified Button Component - Design System v2.0
 * Single button component used across ALL pages
 * 
 * Variants:
 * - primary: Main actions (blue gradient)
 * - secondary: Secondary actions (white with border)
 * - success: Positive actions (green)
 * - danger: Destructive actions (red)
 * - ghost: Minimal actions (transparent)
 * - ai: AI-specific actions (purple gradient)
 */
const Button = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  iconPosition = 'left',
  fullWidth = false,
  className = '',
  onClick,
  type = 'button',
  children,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variantStyles = {
    primary: 'bg-primary-600 hover:bg-primary-700 text-white shadow-md hover:shadow-lg focus:ring-primary-500',
    secondary: 'bg-white hover:bg-neutral-50 text-primary-600 border-2 border-primary-500 hover:border-primary-600 shadow-sm focus:ring-primary-500',
    success: 'bg-success-600 hover:bg-success-700 text-white shadow-md hover:shadow-lg focus:ring-success-500',
    danger: 'bg-danger-600 hover:bg-danger-700 text-white shadow-md hover:shadow-lg focus:ring-danger-500',
    ghost: 'bg-transparent hover:bg-neutral-100 text-neutral-700 focus:ring-neutral-400',
    ai: 'bg-gradient-to-r from-ai-600 to-ai-700 hover:from-ai-700 hover:to-ai-800 text-white shadow-md hover:shadow-lg focus:ring-ai-500'
  }
  
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm gap-1.5',
    md: 'px-6 py-2.5 text-base gap-2',
    lg: 'px-8 py-3.5 text-lg gap-2.5'
  }
  
  const iconSizes = { sm: 16, md: 20, lg: 24 }
  
  const isDisabled = disabled || loading
  const widthStyle = fullWidth ? 'w-full' : ''
  
  const buttonClasses = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthStyle} ${className}`
  
  const renderIcon = () => {
    if (loading) return <Loader2 size={iconSizes[size]} className="animate-spin" />
    if (Icon) return <Icon size={iconSizes[size]} />
    return null
  }
  
  return (
    <motion.button
      type={type}
      className={buttonClasses}
      onClick={onClick}
      disabled={isDisabled}
      whileHover={!isDisabled ? { scale: 1.02 } : undefined}
      whileTap={!isDisabled ? { scale: 0.98 } : undefined}
      {...props}
    >
      {iconPosition === 'left' && renderIcon()}
      {children}
      {iconPosition === 'right' && renderIcon()}
    </motion.button>
  )
}

export default Button
