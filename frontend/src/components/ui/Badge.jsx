/**
 * Unified Badge Component - Design System v2.0
 * Used for status indicators, categories, tags
 * 
 * Variants match semantic colors from design system
 */
const Badge = ({
  variant = 'default',
  size = 'md',
  dot = false,
  className = '',
  children,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center font-medium rounded-full'
  
  const variantStyles = {
    default: 'bg-neutral-100 text-neutral-700',
    primary: 'bg-primary-100 text-primary-700',
    success: 'bg-success-100 text-success-700',
    danger: 'bg-danger-100 text-danger-700',
    warning: 'bg-warning-100 text-warning-700',
    ai: 'bg-ai-100 text-ai-700'
  }
  
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-3 py-1 text-sm gap-1.5',
    lg: 'px-4 py-1.5 text-base gap-2'
  }
  
  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5'
  }
  
  const badgeClasses = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`
  
  return (
    <span className={badgeClasses} {...props}>
      {dot && <span className={`${dotSizes[size]} rounded-full bg-current opacity-60`} />}
      {children}
    </span>
  )
}

export default Badge
