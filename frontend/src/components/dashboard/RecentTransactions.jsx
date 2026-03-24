import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { staggerContainer, staggerItem } from '../../utils/animations';
import { Card, CategoryBadge, EmptyState } from '../common';

/**
 * RecentTransactions Component
 * Displays recent transactions with animations
 */
const RecentTransactions = ({ transactions = [], limit = 5, showViewAll = true }) => {
  const displayTransactions = transactions.slice(0, limit);
  
  if (transactions.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Transactions</h3>
        <EmptyState
          icon={TrendingUp}
          title="No transactions yet"
          message="Upload a bank statement to see your transactions here"
        />
      </Card>
    );
  }
  
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Recent Transactions</h3>
        {showViewAll && (
          <Link 
            to="/transactions"
            className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
          >
            View All
            <ArrowRight size={16} />
          </Link>
        )}
      </div>
      
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="space-y-3"
      >
        {displayTransactions.map((transaction, index) => (
          <motion.div
            key={transaction.id || index}
            variants={staggerItem}
            className="flex items-center justify-between p-4 rounded-lg hover:bg-gray-50 transition-colors border border-gray-100"
          >
            {/* Left Side */}
            <div className="flex items-center gap-4 flex-1 min-w-0">
              {/* Icon */}
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                transaction.type === 'credit' || transaction.amount > 0
                  ? 'bg-green-100'
                  : 'bg-red-100'
              }`}>
                {transaction.type === 'credit' || transaction.amount > 0 ? (
                  <TrendingUp className="w-5 h-5 text-green-600" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-red-600" />
                )}
              </div>
              
              {/* Details */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {transaction.description || transaction.narration || 'Transaction'}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-xs text-gray-500">
                    {transaction.date || new Date(transaction.transaction_date).toLocaleDateString()}
                  </p>
                  {transaction.category && (
                    <CategoryBadge category={transaction.category} size="sm" />
                  )}
                </div>
              </div>
            </div>
            
            {/* Amount */}
            <div className={`font-semibold text-lg flex-shrink-0 ${
              transaction.type === 'credit' || transaction.amount > 0
                ? 'text-green-600'
                : 'text-red-600'
            }`}>
              {transaction.type === 'credit' || transaction.amount > 0 ? '+' : '-'}
              ₹{Math.abs(transaction.amount || transaction.credit || transaction.debit || 0).toLocaleString()}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </Card>
  );
};

export default RecentTransactions;
