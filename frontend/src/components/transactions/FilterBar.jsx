import { useState, useEffect } from 'react';
import { Search, Filter, X, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../common';
import { useDebounce } from '../../hooks/useDebounce';
import { TRANSACTION_CATEGORIES } from '../../utils/constants';

/**
 * FilterBar Component
 * Search and filter controls for transactions
 */
const FilterBar = ({ filters, onFilterChange, onSearchChange }) => {
  const { categories: selectedCategories = [], type: selectedType = 'all', search: externalSearch = '' } = filters || {};

  // Local state only for the search input to keep typing smooth
  const [searchTerm, setSearchTerm] = useState(externalSearch);

  // Sync local search term with external search (e.g. if cleared from outside)
  useEffect(() => {
    setSearchTerm(externalSearch);
  }, [externalSearch]);

  // Categories derived from constants
  const categoriesList = Object.values(TRANSACTION_CATEGORIES).map(cat => cat.label);

  // Debounce search logic
  const debouncedSearch = useDebounce(searchTerm, 500);

  // Effect for debounced search
  // Notify parent only when debounced search changes
  useEffect(() => {
    if (debouncedSearch !== externalSearch) {
      onSearchChange?.(debouncedSearch);
    }
  }, [debouncedSearch]);

  const [showFilters, setShowFilters] = useState(false);

  // Handle search
  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    // Note: onSearchChange is called by the useEffect above (debounced)
  };

  // Handle category toggle
  const toggleCategory = (category) => {
    let newCategories;
    if (selectedCategories.includes(category)) {
      newCategories = selectedCategories.filter(c => c !== category);
    } else {
      newCategories = [...selectedCategories, category];
    }
    onFilterChange?.({ categories: newCategories, type: selectedType });
  };

  // Handle type change
  const handleTypeChange = (type) => {
    const typeValue = type === 'All Types' ? 'all' : type.toLowerCase();
    onFilterChange?.({ categories: selectedCategories, type: typeValue });
  };

  // Clear all filters
  const clearFilters = () => {
    onSearchChange?.('');
    onFilterChange?.({ categories: [], type: 'all' });
  };

  const hasActiveFilters = searchTerm || selectedCategories.length > 0 || selectedType !== 'all';

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
            Filters {selectedCategories.length > 0 && `(${selectedCategories.length})`}
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
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-6 pt-4 border-t border-gray-200 overflow-hidden"
          >
            {/* Category Filter - Pill Style */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Categories (Select Multiple)
              </label>
              <div className="flex flex-wrap gap-2">
                {categoriesList.map((category) => {
                  const isSelected = selectedCategories.includes(category);
                  return (
                    <button
                      key={category}
                      onClick={() => toggleCategory(category)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${isSelected
                        ? 'bg-indigo-600 border-indigo-600 text-white shadow-md scale-105'
                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-indigo-300 hover:bg-indigo-50'
                        }`}
                    >
                      {category}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Type Filter */}
            <div className="max-w-xs">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Transaction Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => handleTypeChange(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all text-sm font-medium"
              >
                <option value="all">All Types</option>
                <option value="income">Income (Credit)</option>
                <option value="expense">Expense (Debit)</option>
              </select>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FilterBar;
