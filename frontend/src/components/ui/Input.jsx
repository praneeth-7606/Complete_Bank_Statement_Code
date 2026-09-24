import { forwardRef } from 'react'

/**
 * Unified Input Component - Design System v2.0
 * Form inputs with consistent styling
 */
const Input = forwardRef(({
  label,
  error,
  helperText,
  icon: Icon,
  iconPosition = 'left',
  fullWidth = false,
  className = '',
  ...props
}, ref) => {
  const baseStyles = 'px-4 py-2.5 rounded-xl border-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 text-gray-900 placeholder-gray-400 bg-white'
  const stateStyles = error
    ? 'border-danger-500 focus:border-danger-600 focus:ring-danger-500/20 hover:border-danger-400'
    : 'border-[var(--border-subtle)] focus:border-primary-500 focus:ring-primary-500/20 hover:border-[var(--accent-primary)]'
  
  const widthStyle = fullWidth ? 'w-full' : ''
  const iconPadding = Icon ? (iconPosition === 'left' ? 'pl-11' : 'pr-11') : ''
  
  const inputClasses = `${baseStyles} ${stateStyles} ${widthStyle} ${iconPadding} bg-[var(--bg-card)] text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] ${className}`
  
  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label className="block text-sm font-semibold text-[var(--text-primary)] mb-2">
          {label}
        </label>
      )}
      
      <div className="relative">
        {Icon && iconPosition === 'left' && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
            <Icon size={20} className="text-[var(--text-secondary)]" />
          </div>
        )}
        
        <input
          ref={ref}
          className={inputClasses}
          {...props}
        />
        
        {Icon && iconPosition === 'right' && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
            <Icon size={20} className="text-[var(--text-secondary)]" />
          </div>
        )}
      </div>
      
      {error && (
        <p className="mt-1.5 text-sm text-danger-600 font-medium" role="alert">{error}</p>
      )}
      
      {helperText && !error && (
        <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{helperText}</p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

export default Input
