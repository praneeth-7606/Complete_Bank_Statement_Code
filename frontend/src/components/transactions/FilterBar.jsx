import { useState } from 'react';
import { Search, Filter, X, Calendar } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../common';
import { useDebounce } from '../../hooks/useDebounce';

/**
 * FilterBar Component
 * Search and filter controls for transactions
 */
const FilterBar = ({ onFilterChange, onSearchChange }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  
  // Debounce search
  const debouncedSearch = useDebounce(searchTerm, 300);
  
  // Categories
  const categories = [
    'All Categories',
    'Food & Dining',
    'Shopping',
    'Transport',
    'Bills & Utilities',
    'Entertainment',
    'Income',
    'Healthcare',
    'Education',
    'Investments',
    'Personal Transfer',
    'Others'
  ];
  
  // Handle search
  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    onSearchChange?.(value);
  };
  
  // Handle category change
  const handleCategoryChange = (category) => {
    const categoryValue = category === 'All Categories' ? 'all' : category;
    setSelectedCategory(categoryValue);
    onFilterChange?.({ category: categoryValue, type: selectedType });
  };
  
  // Handle type change
  const handleTypeChange = (type) => {
    const typeValue = type === 'All Types' ? 'all' : type.toLowerCase();
    setSelectedType(typeValue);
    onFilterChange?.({ category: selectedCategory, type: typeValue });
  };
  
  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setSelectedCategory('all');
    setSelectedType('all');
    onSearchChange?.('');
    onFilterChange?.({ category: 'all', type: 'all' });
  };
  
  const hasActiveFilters = searchTerm || selectedCategory !== 'all' || selectedType !== 'all';
  
  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 space-y-4">
      {/* Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchChange}
            placeholder="Search transactions..."
            className="w-full pl-12 pr-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
          />
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="secondary"
            icon={Filter}
            iconPosition="left"
            onClick={() => setShowFilters(!showFilters)}
            className={showFilters ? 'bg-indigo-50 border-indigo-300' : ''}
          >
            Filters
          </Button>
          
          {hasActiveFilters && (
            <Button
              variant="ghost"
              icon={X}
              iconPosition="left"
              onClick={clearFilters}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
      
      {/* Filter Options */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200"
        >
          {/* Category Filter */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="all">All Categories</option>
              {categories.slice(1).map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
          
          {/* Type Filter */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Transaction Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => handleTypeChange(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
            >
              <option value="all">All Types</option>
              <option value="income">Income (Credit)</option>
              <option value="expense">Expense (Debit)</option>
            </select>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default FilterBar;
