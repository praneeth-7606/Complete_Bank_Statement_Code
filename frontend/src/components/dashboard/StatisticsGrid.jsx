import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Wallet, FileText } from 'lucide-react';
import { StatCard } from '../common';
import { staggerContainer } from '../../utils/animations';

/**
 * StatisticsGrid Component
 * Grid of statistic cards for dashboard
 */
const StatisticsGrid = ({ stats, onCardClick }) => {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
    >
      <StatCard
        title="Total Income"
        value={stats?.totalIncome || 0}
        prefix="₹"
        icon={TrendingUp}
        type="income"
        trend={stats?.incomeTrend}
        animate={true}
        onClick={() => onCardClick?.('income')}
      />
      <StatCard
        title="Total Expenses"
        value={stats?.totalExpenses || 0}
        prefix="₹"
        icon={TrendingDown}
        type="expense"
        trend={stats?.expenseTrend}
        animate={true}
        onClick={() => onCardClick?.('expense')}
      />
      <StatCard
        title="Net Savings"
        value={stats?.balance || 0}
        prefix="₹"
        icon={Wallet}
        type="savings"
        trend={stats?.savingsTrend}
        animate={true}
        onClick={() => onCardClick?.('savings')}
      />
      <StatCard
        title="Transactions"
        value={stats?.totalTransactions || 0}
        icon={FileText}
        type="transaction"
        animate={true}
        onClick={() => onCardClick?.('transactions')}
      />
    </motion.div>
  );
};

export default StatisticsGrid;
