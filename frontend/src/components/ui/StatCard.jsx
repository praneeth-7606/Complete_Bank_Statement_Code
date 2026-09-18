import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useCountUp } from '../../hooks/useCountUp';
import { staggerItem } from '../../utils/animations';

/**
 * StatCard Component
 * Displays a statistic with animated count-up, icon, and optional trend indicator
 * 
 * @param {string} title - Card title (e.g., "Total Income")
 * @param {number} value - Numeric value to display
 * @param {string} prefix - Prefix for value (e.g., "$")
 * @param {string} suffix - Suffix for value (e.g., "K")
 * @param {React.Component} icon - Icon component from lucide-react
 * @param {string} type - Stat type: 'income', 'expense', 'savings', 'transaction'
 * @param {object} trend - Trend data: { value: number, isPositive: boolean }
 * @param {boolean} animate - Enable count-up animation
 * @param {function} onClick - Click handler
 * @param {string} className - Additional CSS classes
 */
const StatCard = ({
  title,
  value,
  prefix = '',
  suffix = '',
  icon: Icon,
  type = 'transaction',
  trend,
  animate = true,
  onClick,
  className = ''
}) => {
  // Use count-up animation
  const animatedValue = useCountUp(value, 2000, animate);
  const displayValue = animate ? animatedValue : value;
  
  // Type-based gradient styles
  const gradientStyles = {
    income: 'income-gradient',
    expense: 'expense-gradient',
    savings: 'savings-gradient',
    transaction: 'transaction-gradient'
  };
  
  // Type-based icon background colors
  const iconBgColors = {
    income: 'bg-green-100',
    expense: 'bg-red-100',
    savings: 'bg-blue-100',
    transaction: 'bg-purple-100'
  };
  
  // Type-based icon colors
  const iconColors = {
    income: 'text-green-600',
    expense: 'text-red-600',
    savings: 'text-blue-600',
    transaction: 'text-purple-600'
  };
  
  // Format number with commas
  const formatNumber = (num) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };
  
  return (
    <motion.div
      variants={staggerItem}
      className={`stat-card ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
      whileHover={onClick ? { scale: 1.02, boxShadow: '0 20px 40px rgba(0,0,0,0.1)' } : undefined}
    >
      {/* Icon */}
      <div className="flex items-start justify-between mb-4">
        <div className={`${iconBgColors[type]} ${iconColors[type]} p-3 rounded-full`}>
          {Icon && <Icon size={24} />}
        </div>
        
        {/* Trend Indicator */}
        {trend && (
          <div className={`flex items-center text-sm font-semibold ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {trend.isPositive ? (
              <TrendingUp size={16} className="mr-1" />
            ) : (
              <TrendingDown size={16} className="mr-1" />
            )}
            <span>{Math.abs(trend.value)}%</span>
          </div>
        )}
      </div>
      
      {/* Title */}
      <h3 className="text-gray-600 text-sm font-medium mb-2">{title}</h3>
      
      {/* Value */}
      <div className="text-3xl font-bold text-gray-900">
        {prefix}{formatNumber(displayValue)}{suffix}
      </div>
    </motion.div>
  );
};

export default StatCard;
