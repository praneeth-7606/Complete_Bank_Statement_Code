import { 
  Utensils, 
  ShoppingBag, 
  Car, 
  FileText, 
  Film, 
  TrendingUp, 
  Heart, 
  BookOpen, 
  PieChart, 
  ArrowRightLeft, 
  MoreHorizontal 
} from 'lucide-react';

/**
 * CategoryBadge Component
 * Displays a category badge with icon and color coding
 * 
 * @param {string} category - Category name
 * @param {string} size - Badge size: 'sm', 'md', 'lg'
 * @param {boolean} showIcon - Show category icon
 * @param {string} className - Additional CSS classes
 */
const CategoryBadge = ({
  category,
  size = 'sm',
  showIcon = true,
  className = ''
}) => {
  // Category configuration with colors and icons
  const categoryConfig = {
    'Food & Dining': { 
      bg: 'bg-orange-100', 
      text: 'text-orange-700', 
      icon: Utensils 
    },
    'Shopping': { 
      bg: 'bg-purple-100', 
      text: 'text-purple-700', 
      icon: ShoppingBag 
    },
    'Transport': { 
      bg: 'bg-blue-100', 
      text: 'text-blue-700', 
      icon: Car 
    },
    'Bills & Utilities': { 
      bg: 'bg-yellow-100', 
      text: 'text-yellow-700', 
      icon: FileText 
    },
    'Entertainment': { 
      bg: 'bg-pink-100', 
      text: 'text-pink-700', 
      icon: Film 
    },
    'Income': { 
      bg: 'bg-green-100', 
      text: 'text-green-700', 
      icon: TrendingUp 
    },
    'Healthcare': { 
      bg: 'bg-red-100', 
      text: 'text-red-700', 
      icon: Heart 
    },
    'Education': { 
      bg: 'bg-indigo-100', 
      text: 'text-indigo-700', 
      icon: BookOpen 
    },
    'Investments': { 
      bg: 'bg-emerald-100', 
      text: 'text-emerald-700', 
      icon: PieChart 
    },
    'Personal Transfer': { 
      bg: 'bg-cyan-100', 
      text: 'text-cyan-700', 
      icon: ArrowRightLeft 
    },
    'Others': { 
      bg: 'bg-gray-100', 
      text: 'text-gray-700', 
      icon: MoreHorizontal 
    }
  };
  
  // Get category config or default to 'Others'
  const config = categoryConfig[category] || categoryConfig['Others'];
  const Icon = config.icon;
  
  // Size styles
  const sizeStyles = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  };
  
  // Icon sizes
  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16
  };
  
  return (
    <span 
      className={`category-badge ${config.bg} ${config.text} ${sizeStyles[size]} ${className}`}
    >
      {showIcon && <Icon size={iconSizes[size]} />}
      <span>{category}</span>
    </span>
  );
};

export default CategoryBadge;
