import { motion } from 'framer-motion';
import { cardHover, fadeIn } from '../../utils/animations';

/**
 * Card Component
 * Reusable card container with standard and glassmorphism variants
 * 
 * @param {string} variant - Card style: 'standard', 'glass'
 * @param {string} padding - Padding size: 'none', 'sm', 'md', 'lg'
 * @param {string} radius - Border radius: 'md', 'lg', 'xl', '2xl'
 * @param {boolean} hover - Enable hover animation
 * @param {boolean} animate - Enable entrance animation
 * @param {string} className - Additional CSS classes
 * @param {function} onClick - Click handler (makes card clickable)
 * @param {React.ReactNode} children - Card content
 */
const Card = ({
  variant = 'standard',
  padding = 'md',
  radius = 'xl',
  hover = true,
  animate = true,
  className = '',
  onClick,
  children,
  ...props
}) => {
  // Base styles
  const baseStyles = 'transition-all duration-300';
  
  // Variant styles
  const variantStyles = {
    standard: 'bg-white/90 backdrop-blur-sm shadow-lg border border-indigo-100 hover:shadow-xl',
    glass: 'bg-white/10 backdrop-blur-xl shadow-xl border border-white/20 hover:shadow-2xl glassmorphism'
  };
  
  // Padding styles
  const paddingStyles = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };
  
  // Border radius styles
  const radiusStyles = {
    md: 'rounded-lg',
    lg: 'rounded-xl',
    xl: 'rounded-2xl',
    '2xl': 'rounded-3xl'
  };
  
  // Clickable styles
  const clickableStyles = onClick ? 'cursor-pointer' : '';
  
  // Combine all styles
  const cardClasses = `${baseStyles} ${variantStyles[variant]} ${paddingStyles[padding]} ${radiusStyles[radius]} ${clickableStyles} ${className}`;
  
  // Animation variants
  const motionProps = {
    ...(animate && fadeIn),
    ...(hover && onClick && { whileHover: cardHover.hover, initial: cardHover.rest })
  };
  
  return (
    <motion.div
      className={cardClasses}
      onClick={onClick}
      {...motionProps}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export default Card;
