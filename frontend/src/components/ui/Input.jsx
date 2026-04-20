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
  const baseStyles = 'px-4 py-2.5 rounded-xl border-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1'
  const stateStyles = error
    ? 'border-danger-500 focus:border-danger-600 focus:ring-danger-500/20'
    : 'border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20'
  
  const widthStyle = fullWidth ? 'w-full' : ''
  const iconPadding = Icon ? (iconPosition === 'left' ? 'pl-11' : 'pr-11') : ''
  
  const inputClasses = `${baseStyles} ${stateStyles} ${widthStyle} ${iconPadding} ${className}`
  
  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label className="block text-sm font-semibold text-neutral-700 mb-2">
          {label}
        </label>
      )}
      
      <div className="relative">
        {Icon && iconPosition === 'left' && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
            <Icon size={20} />
          </div>
        )}
        
        <input
          ref={ref}
          className={inputClasses}
          {...props}
        />
        
        {Icon && iconPosition === 'right' && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
            <Icon size={20} />
          </div>
        )}
      </div>
      
      {error && (
        <p className="mt-1.5 text-sm text-danger-600 font-medium">{error}</p>
      )}
      
      {helperText && !error && (
        <p className="mt-1.5 text-sm text-neutral-500">{helperText}</p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

export default Input
