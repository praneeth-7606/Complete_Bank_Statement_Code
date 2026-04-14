import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  CheckCircle,
  ArrowRight,
  LayoutDashboard,
  List,
  Sparkles,
} from 'lucide-react';
import Confetti from 'react-confetti';
import { useState, useEffect } from 'react';
import CountUp from 'react-countup';
import MetadataGrid from '../common/MetadataGrid';
import { formatCurrency } from '../../utils/formatters';
import { ANIMATIONS } from '../../utils/constants';

/**
 * EnhancedResultsCard Component
 * Displays processing results with metadata, analysis, and action buttons
 * 
 * @param {object} results - Processing results from API
 * @param {object} metadata - Statement metadata
 * @param {function} onReset - Callback to reset the upload form
 */
const EnhancedResultsCard = ({ results, metadata, onReset }) => {
  const [showConfetti, setShowConfetti] = useState(true);
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    // Update window size for confetti
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);

    // Stop confetti after 5 seconds
    const timer = setTimeout(() => {
      setShowConfetti(false);
    }, 5000);

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timer);
    };
  }, []);

  const {
    total_transactions = 0,
    message = 'Processing complete',
    analysis: analysisProp = {},
  } = results || {};

  // Ensure analysis is never null even if result.analysis is explicitly null
  const analysis = analysisProp || {};
  const { summary = {}, insights = [] } = analysis;

  return (
    <>
      {/* Confetti Effect */}
      {showConfetti && (
        <Confetti
          width={windowSize.width}
          height={windowSize.height}
          recycle={false}
          numberOfPieces={200}
          gravity={0.3}
        />
      )}

      <motion.div
        variants={ANIMATIONS.slideUp}
        initial="initial"
        animate="animate"
        className="card"
      >
        {/* Success Header */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{
            type: 'spring',
            stiffness: 200,
            damping: 15,
            delay: 0.2,
          }}
          className="flex items-center gap-3 mb-6"
        >
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="w-7 h-7 text-green-600" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              Processing Complete!
              <Sparkles className="w-6 h-6 text-yellow-500" />
            </h3>
            <p className="text-sm text-gray-600">{message}</p>
          </div>
        </motion.div>

        {/* Transaction Count Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6"
        >
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-600 mb-1 font-medium">
              Total Transactions
            </p>
            <p className="text-3xl font-bold text-blue-900">
              <CountUp end={total_transactions} duration={2} />
            </p>
          </div>

          {summary.total_income !== undefined && (
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-600 mb-1 font-medium">
                Total Income
              </p>
              <p className="text-2xl font-bold text-green-900">
                {formatCurrency(summary.total_income)}
              </p>
            </div>
          )}

          {summary.total_expenses !== undefined && (
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-600 mb-1 font-medium">
                Total Expenses
              </p>
              <p className="text-2xl font-bold text-red-900">
                {formatCurrency(summary.total_expenses)}
              </p>
            </div>
          )}
        </motion.div>

        {/* Metadata Grid */}
        {metadata && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mb-6"
          >
            <h4 className="text-lg font-semibold text-gray-900 mb-4">
              Statement Details
            </h4>
            <MetadataGrid metadata={metadata} />
          </motion.div>
        )}

        {/* Insights */}
        {insights && insights.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mb-6 p-4 bg-purple-50 rounded-lg border border-purple-200"
          >
            <h4 className="text-lg font-semibold text-purple-900 mb-3 flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              AI Insights
            </h4>
            <ul className="space-y-2">
              {insights.slice(0, 3).map((insight, index) => (
                <li
                  key={index}
                  className="text-sm text-purple-800 flex items-start gap-2"
                >
                  <span className="text-purple-600 mt-0.5">•</span>
                  <span>{insight}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        )}

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="flex flex-col sm:flex-row gap-3 pt-6 border-t"
        >
          <Link to="/transactions" className="flex-1">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <List className="w-5 h-5" />
              View All Transactions
              <ArrowRight className="w-5 h-5" />
            </motion.button>
          </Link>

          <Link to="/" className="flex-1">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              <LayoutDashboard className="w-5 h-5" />
              Go to Dashboard
            </motion.button>
          </Link>

          {onReset && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onReset}
              className="btn-secondary sm:w-auto px-6"
            >
              Upload Another
            </motion.button>
          )}
        </motion.div>
      </motion.div>
    </>
  );
};

export default EnhancedResultsCard;
