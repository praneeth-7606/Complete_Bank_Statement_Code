import { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp, ArrowUpDown } from 'lucide-react';
import { CategoryBadge, EmptyState } from '../common';
import CategoryEditableCell from './CategoryEditableCell';
import { staggerContainer, staggerItem } from '../../utils/animations';

const TransactionTable = ({ transactions = [], onSort }) => {
  const [sortField, setSortField] = useState('date');
  const [sortDirection, setSortDirection] = useState('desc');
  const [expandedRow, setExpandedRow] = useState(null);

  const handleSort = (field) => {
    const newDirection = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc';
    setSortField(field);
    setSortDirection(newDirection);
    onSort?.(field, newDirection);
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ArrowUpDown size={16} className="text-gray-400" />;
    return sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />;
  };

  if (transactions.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
        <EmptyState
          title="No transactions found"
          message="Try adjusting your filters or upload a new statement"
        />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left">
                <button onClick={() => handleSort('date')} className="flex items-center gap-2 font-semibold text-gray-700 hover:text-indigo-600">
                  Date <SortIcon field="date" />
                </button>
              </th>
              <th className="px-6 py-4 text-left">
                <button onClick={() => handleSort('description')} className="flex items-center gap-2 font-semibold text-gray-700 hover:text-indigo-600">
                  Description <SortIcon field="description" />
                </button>
              </th>
              <th className="px-6 py-4 text-left">
                <span className="font-semibold text-gray-700">Category</span>
              </th>
              <th className="px-6 py-4 text-right">
                <button onClick={() => handleSort('amount')} className="flex items-center gap-2 font-semibold text-gray-700 hover:text-indigo-600 ml-auto">
                  Amount <SortIcon field="amount" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction, index) => (
              <motion.tr
                key={transaction.id || index}
                variants={staggerItem}
                className="border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                onClick={() => setExpandedRow(expandedRow === index ? null : index)}
              >
                <td className="px-6 py-4 text-sm text-gray-600">
                  {new Date(transaction.date || transaction.transaction_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <p className="font-medium text-gray-900">{transaction.description || transaction.narration}</p>
                  {expandedRow === index && transaction.reference && (
                    <p className="text-xs text-gray-500 mt-1">Ref: {transaction.reference}</p>
                  )}
                </td>
                <td className="px-6 py-4">
                  {transaction.category && (
                    <CategoryEditableCell
                      transactionId={transaction.id}
                      description={transaction.description || transaction.narration}
                      currentCategory={transaction.category}
                      allTransactions={transactions}
                      onUpdate={(newCategory) => {
                        // Update transaction in parent component if needed
                        transaction.category = newCategory
                      }}
                    />
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`font-semibold text-lg ${transaction.type === 'credit' || transaction.credit > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                    {transaction.type === 'credit' || transaction.credit > 0 ? '+' : '-'}
                    ₹{Math.abs(transaction.amount || transaction.credit || transaction.debit || 0).toLocaleString()}
                  </span>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <motion.div variants={staggerContainer} initial="hidden" animate="show" className="md:hidden divide-y divide-gray-100">
        {transactions.map((transaction, index) => (
          <motion.div key={transaction.id || index} variants={staggerItem} className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="font-medium text-gray-900">{transaction.description || transaction.narration}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(transaction.date || transaction.transaction_date).toLocaleDateString()}
                </p>
              </div>
              <span className={`font-semibold text-lg ${transaction.type === 'credit' || transaction.credit > 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                {transaction.type === 'credit' || transaction.credit > 0 ? '+' : '-'}
                ₹{Math.abs(transaction.amount || transaction.credit || transaction.debit || 0).toLocaleString()}
              </span>
            </div>
            <CategoryEditableCell
              transactionId={transaction.id}
              description={transaction.description || transaction.narration}
              currentCategory={transaction.category}
              allTransactions={transactions}
              onUpdate={(newCategory) => {
                // Update transaction in parent component if needed
                transaction.category = newCategory
              }}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

export default TransactionTable;
