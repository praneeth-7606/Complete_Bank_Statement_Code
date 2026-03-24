/**
 * Utility functions for formatting data in the FinanceAI application
 */

/**
 * Format file size from bytes to human-readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size (e.g., "1.23 MB", "456 KB")
 */
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

/**
 * Format processing time from seconds to human-readable format
 * @param {number} seconds - Processing time in seconds
 * @returns {string} Formatted time (e.g., "2.45s", "1m 30s", "500ms")
 */
export const formatProcessingTime = (seconds) => {
  if (!seconds || seconds === 0) return '0s';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = (seconds % 60).toFixed(0);
  return `${minutes}m ${remainingSeconds}s`;
};

/**
 * Format currency amount in Indian Rupees
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency (e.g., "₹1,234.56")
 */
export const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return '₹0.00';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

/**
 * Format currency amount without symbol
 * @param {number} amount - Amount to format
 * @returns {string} Formatted number (e.g., "1,234.56")
 */
export const formatNumber = (amount) => {
  if (amount === null || amount === undefined) return '0.00';
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

/**
 * Format date to localized string
 * @param {string|Date} dateString - Date to format
 * @param {string} format - Format type ('short', 'long', 'full')
 * @returns {string} Formatted date (e.g., "Nov 7, 2025")
 */
export const formatDate = (dateString, format = 'short') => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid Date';
  
  const options = {
    short: {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    },
    long: {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    },
    full: {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long',
      hour: '2-digit',
      minute: '2-digit'
    }
  };
  
  return date.toLocaleDateString('en-IN', options[format] || options.short);
};

/**
 * Format date to time string
 * @param {string|Date} dateString - Date to format
 * @returns {string} Formatted time (e.g., "02:30 PM")
 */
export const formatTime = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid Time';
  
  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

/**
 * Format date to relative time (e.g., "2 hours ago", "3 days ago")
 * @param {string|Date} dateString - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid Date';
  
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
  
  return formatDate(dateString);
};

/**
 * Format extraction method to display name
 * @param {string} method - Extraction method code
 * @returns {string} Display name
 */
export const formatExtractionMethod = (method) => {
  const methods = {
    'SMART_AUTO': 'Smart Auto',
    'TABLE_EXTRACTION': 'Table Extraction',
    'TEXT_BASED': 'Text Based',
    'HYBRID': 'Hybrid',
    'OCR': 'OCR',
    'AI_POWERED': 'AI Powered'
  };
  
  return methods[method] || method || 'Unknown';
};

/**
 * Format bank name from filename or code
 * @param {string} bankName - Bank name or code
 * @returns {string} Formatted bank name
 */
export const formatBankName = (bankName) => {
  if (!bankName) return 'Unknown Bank';
  
  // Common bank name mappings
  const bankMappings = {
    'HDFC': 'HDFC Bank',
    'ICICI': 'ICICI Bank',
    'SBI': 'State Bank of India',
    'AXIS': 'Axis Bank',
    'KOTAK': 'Kotak Mahindra Bank',
    'PNB': 'Punjab National Bank',
    'BOB': 'Bank of Baroda',
    'CANARA': 'Canara Bank',
    'UNION': 'Union Bank of India',
    'IDBI': 'IDBI Bank'
  };
  
  const upperName = bankName.toUpperCase();
  for (const [code, fullName] of Object.entries(bankMappings)) {
    if (upperName.includes(code)) {
      return fullName;
    }
  }
  
  return bankName;
};

/**
 * Format transaction category for display
 * @param {string} category - Category code or name
 * @returns {string} Formatted category name
 */
export const formatCategory = (category) => {
  if (!category) return 'Uncategorized';
  
  // Capitalize first letter of each word
  return category
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

/**
 * Truncate text to specified length with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength = 50) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Format percentage value
 * @param {number} value - Percentage value
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage (e.g., "12.5%")
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined) return '0%';
  return `${value.toFixed(decimals)}%`;
};
