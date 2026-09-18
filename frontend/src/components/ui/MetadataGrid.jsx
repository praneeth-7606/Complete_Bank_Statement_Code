import { motion } from 'framer-motion';
import {
  Building2,
  FileText,
  Clock,
  Zap,
  HardDrive,
  Hash,
} from 'lucide-react';
import {
  formatFileSize,
  formatProcessingTime,
  formatBankName,
  formatExtractionMethod,
} from '../../utils/formatters';
import { ANIMATIONS } from '../../utils/constants';

/**
 * MetadataGrid Component
 * Displays statement metadata in a responsive grid layout with icons
 * 
 * @param {object} metadata - Metadata object containing statement information
 * @param {string} metadata.bankName - Bank name
 * @param {number} metadata.pageCount - Number of pages
 * @param {number} metadata.processingTime - Processing time in seconds
 * @param {string} metadata.extractionMethod - Extraction method used
 * @param {number} metadata.fileSize - File size in bytes
 * @param {number} metadata.totalTransactions - Total number of transactions
 */
const MetadataGrid = ({ metadata = {} }) => {
  const {
    bankName,
    pageCount,
    processingTime,
    extractionMethod,
    fileSize,
    totalTransactions,
  } = metadata;

  // Filter out items with N/A or missing values
  const allMetadataItems = [
    {
      icon: Building2,
      label: 'Bank',
      value: formatBankName(bankName),
      color: 'blue',
      tooltip: 'Bank name extracted from statement',
      show: !!bankName,
    },
    {
      icon: FileText,
      label: 'Pages',
      value: pageCount,
      color: 'green',
      tooltip: 'Total number of pages in PDF',
      show: !!pageCount && pageCount > 0,
    },
    {
      icon: Clock,
      label: 'Processing Time',
      value: processingTime ? formatProcessingTime(processingTime) : null,
      color: 'purple',
      tooltip: 'Time taken to process the statement',
      show: !!processingTime && processingTime > 0,
    },
    {
      icon: Zap,
      label: 'Method',
      value: formatExtractionMethod(extractionMethod),
      color: 'yellow',
      tooltip: 'Extraction method used',
      show: !!extractionMethod,
    },
    {
      icon: HardDrive,
      label: 'File Size',
      value: fileSize ? formatFileSize(fileSize) : null,
      color: 'indigo',
      tooltip: 'Size of the uploaded PDF file',
      show: !!fileSize && fileSize > 0,
    },
    {
      icon: Hash,
      label: 'Transactions',
      value: totalTransactions,
      color: 'pink',
      tooltip: 'Total transactions extracted',
      show: !!totalTransactions && totalTransactions > 0,
    },
  ];

  // Only show items that have valid values
  const metadataItems = allMetadataItems.filter(item => item.show);

  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      icon: 'text-blue-600',
      border: 'border-blue-200',
    },
    green: {
      bg: 'bg-green-50',
      icon: 'text-green-600',
      border: 'border-green-200',
    },
    purple: {
      bg: 'bg-purple-50',
      icon: 'text-purple-600',
      border: 'border-purple-200',
    },
    yellow: {
      bg: 'bg-yellow-50',
      icon: 'text-yellow-600',
      border: 'border-yellow-200',
    },
    indigo: {
      bg: 'bg-indigo-50',
      icon: 'text-indigo-600',
      border: 'border-indigo-200',
    },
    pink: {
      bg: 'bg-pink-50',
      icon: 'text-pink-600',
      border: 'border-pink-200',
    },
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {metadataItems.map((item, index) => {
        const Icon = item.icon;
        const colors = colorClasses[item.color];

        return (
          <motion.div
            key={item.label}
            variants={ANIMATIONS.slideUp}
            initial="initial"
            animate="animate"
            transition={{ delay: index * 0.1 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className={`
              relative p-4 rounded-lg border ${colors.border} ${colors.bg}
              hover:shadow-md transition-all duration-200 cursor-default
              group
            `}
            title={item.tooltip}
          >
            {/* Icon */}
            <div className={`
              w-10 h-10 rounded-lg ${colors.bg} flex items-center justify-center mb-3
              border ${colors.border}
            `}>
              <Icon className={`w-5 h-5 ${colors.icon}`} />
            </div>

            {/* Label */}
            <p className="text-xs font-medium text-gray-600 mb-1">
              {item.label}
            </p>

            {/* Value */}
            <p className="text-lg font-bold text-gray-900 truncate">
              {item.value}
            </p>

            {/* Tooltip on hover */}
            <div className="
              absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2
              px-3 py-1 bg-gray-900 text-white text-xs rounded-lg
              opacity-0 group-hover:opacity-100 transition-opacity duration-200
              pointer-events-none whitespace-nowrap z-10
            ">
              {item.tooltip}
              <div className="
                absolute top-full left-1/2 transform -translate-x-1/2
                border-4 border-transparent border-t-gray-900
              " />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};

export default MetadataGrid;
