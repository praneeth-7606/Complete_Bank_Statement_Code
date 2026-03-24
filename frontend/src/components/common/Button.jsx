import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { buttonVariants } from '../../utils/animations';

/**
 * Button Component
 * Reusable button with multiple variants, states, and animations
 * 
 * @param {string} variant - Button style variant: 'primary', 'secondary', 'danger', 'ghost'
 * @param {string} size - Button size: 'sm', 'md', 'lg'
 * @param {boolean} loading - Show loading spinner
 * @param {boolean} disabled - Disable button
 * @param {React.ReactNode} icon - Icon component (from lucide-react)
 * @param {string} iconPosition - Icon position: 'left', 'right', 'only'
 * @param {string} className - Additional CSS classes
 * @param {function} onClick - Click handler
 * @param {string} type - Button type: 'button', 'submit', 'reset'
 * @param {React.ReactNode} children - Button text/content
 */
const Button = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon: Icon,
  iconPosition = 'left',
  className = '',
  onClick,
  type = 'button',
  children,
  ...props
}) => {
  // Base styles
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  // Variant styles
  const variantStyles = {
    primary: 'bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg hover:shadow-xl focus:ring-purple-500',
    secondary: 'bg-white hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 text-indigo-600 border-2 border-indigo-400 hover:border-indigo-500 shadow-md focus:ring-indigo-500',
    danger: 'bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white shadow-lg hover:shadow-xl focus:ring-red-500',
    ghost: 'bg-transparent hover:bg-gray-100 text-gray-700 focus:ring-gray-400'
  };
  
  // Size styles
  const sizeStyles = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-8 py-3 text-base',
    lg: 'px-10 py-4 text-lg'
  };
  
  // Icon size mapping
  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 24
  };
  
  // Disabled/loading state
  const isDisabled = disabled || loading;
  const disabledStyles = isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';
  
  // Combine all styles
  const buttonClasses = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${disabledStyles} ${className}`;
  
  // Icon rendering
  const renderIcon = () => {
    if (loading) {
      return <Loader2 size={iconSizes[size]} className="animate-spin" />;
    }
    if (Icon) {
      return <Icon size={iconSizes[size]} />;
    }
    return null;
  };
  
  // Icon-only button
  if (iconPosition === 'only') {
    return (
      <motion.button
        type={type}
        className={buttonClasses}
        onClick={onClick}
        disabled={isDisabled}
        variants={buttonVariants}
        whileHover={!isDisabled ? "hover" : undefined}
        whileTap={!isDisabled ? "tap" : undefined}
        aria-label={props['aria-label'] || 'Button'}
        {...props}
      >
        {renderIcon()}
      </motion.button>
    );
  }
  
  return (
    <motion.button
      type={type}
      className={buttonClasses}
      onClick={onClick}
      disabled={isDisabled}
      variants={buttonVariants}
      whileHover={!isDisabled ? "hover" : undefined}
      whileTap={!isDisabled ? "tap" : undefined}
      {...props}
    >
      {iconPosition === 'left' && renderIcon() && (
        <span className={children ? 'mr-2' : ''}>{renderIcon()}</span>
      )}
      {children}
      {iconPosition === 'right' && renderIcon() && (
        <span className={children ? 'ml-2' : ''}>{renderIcon()}</span>
      )}
    </motion.button>
  );
};

export default Button;
