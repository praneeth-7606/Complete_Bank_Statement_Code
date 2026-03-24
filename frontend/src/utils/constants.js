/**
 * Constants and configuration values for the FinanceAI application
 */

// ============================================
// COLOR PALETTE
// ============================================

export const COLORS = {
  // Primary Colors
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  
  // Success Colors
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },
  
  // Danger Colors
  danger: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },
  
  // Warning Colors
  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },
  
  // Info Colors
  info: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  },
  
  // Neutral Colors
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
};

// ============================================
// SPACING SCALE
// ============================================

export const SPACING = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
};

// ============================================
// BORDER RADIUS
// ============================================

export const RADIUS = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
};

// ============================================
// SHADOWS
// ============================================

export const SHADOWS = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
};

// ============================================
// BREAKPOINTS
// ============================================

export const BREAKPOINTS = {
  sm: '640px',   // Small tablets
  md: '768px',   // Tablets
  lg: '1024px',  // Laptops
  xl: '1280px',  // Desktops
  '2xl': '1536px', // Large desktops
};

// ============================================
// ANIMATION CONFIGURATIONS
// ============================================

export const ANIMATIONS = {
  // Duration
  duration: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
  
  // Easing
  easing: {
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },
  
  // Framer Motion variants
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  },
  
  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
  },
  
  slideLeft: {
    initial: { opacity: 0, x: 20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  },
  
  slideRight: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
  },
  
  scale: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.9 },
  },
  
  stagger: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  },
};

// ============================================
// TRANSACTION CATEGORIES
// ============================================

export const TRANSACTION_CATEGORIES = {
  FOOD: { label: 'Food & Dining', color: COLORS.warning[500], icon: '🍔' },
  TRANSPORT: { label: 'Transportation', color: COLORS.info[500], icon: '🚗' },
  SHOPPING: { label: 'Shopping', color: COLORS.primary[500], icon: '🛍️' },
  ENTERTAINMENT: { label: 'Entertainment', color: COLORS.danger[500], icon: '🎬' },
  BILLS: { label: 'Bills & Utilities', color: COLORS.gray[500], icon: '📄' },
  HEALTHCARE: { label: 'Healthcare', color: COLORS.success[500], icon: '🏥' },
  EDUCATION: { label: 'Education', color: COLORS.primary[600], icon: '📚' },
  TRAVEL: { label: 'Travel', color: COLORS.info[600], icon: '✈️' },
  INVESTMENT: { label: 'Investment', color: COLORS.success[600], icon: '📈' },
  SALARY: { label: 'Salary', color: COLORS.success[700], icon: '💰' },
  TRANSFER: { label: 'Transfer', color: COLORS.gray[600], icon: '↔️' },
  OTHER: { label: 'Other', color: COLORS.gray[400], icon: '📌' },
};

// ============================================
// PROCESSING STAGES
// ============================================

export const PROCESSING_STAGES = [
  {
    name: 'Extracting',
    description: 'Extracting PDF content',
    range: [0, 20],
    icon: 'FileText',
  },
  {
    name: 'Analyzing',
    description: 'Analyzing transactions',
    range: [20, 40],
    icon: 'Brain',
  },
  {
    name: 'Categorizing',
    description: 'Categorizing transactions',
    range: [40, 60],
    icon: 'Tags',
  },
  {
    name: 'Insights',
    description: 'Generating insights',
    range: [60, 80],
    icon: 'Lightbulb',
  },
  {
    name: 'Finalizing',
    description: 'Finalizing results',
    range: [80, 100],
    icon: 'CheckCircle',
  },
];

// ============================================
// LOG LEVELS
// ============================================

export const LOG_LEVELS = {
  INFO: {
    label: 'Info',
    color: COLORS.info[600],
    bgColor: COLORS.info[50],
    borderColor: COLORS.info[200],
    icon: 'Info',
  },
  SUCCESS: {
    label: 'Success',
    color: COLORS.success[700],
    bgColor: COLORS.success[50],
    borderColor: COLORS.success[200],
    icon: 'CheckCircle',
  },
  WARNING: {
    label: 'Warning',
    color: COLORS.warning[700],
    bgColor: COLORS.warning[50],
    borderColor: COLORS.warning[200],
    icon: 'AlertTriangle',
  },
  ERROR: {
    label: 'Error',
    color: COLORS.danger[700],
    bgColor: COLORS.danger[50],
    borderColor: COLORS.danger[200],
    icon: 'AlertCircle',
  },
  COMPLETE: {
    label: 'Complete',
    color: COLORS.success[700],
    bgColor: COLORS.success[50],
    borderColor: COLORS.success[200],
    icon: 'Sparkles',
  },
};

// ============================================
// CHART COLORS
// ============================================

export const CHART_COLORS = [
  COLORS.primary[500],
  COLORS.success[500],
  COLORS.warning[500],
  COLORS.danger[500],
  COLORS.info[500],
  COLORS.primary[600],
  COLORS.success[600],
  COLORS.warning[600],
  COLORS.danger[600],
  COLORS.info[600],
];

// ============================================
// API ENDPOINTS
// ============================================

export const API_ENDPOINTS = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8080',
  AUTH: {
    LOGIN: '/auth/login',
    SIGNUP: '/auth/signup',
    LOGOUT: '/auth/logout',
    ME: '/auth/me',
    GOOGLE: '/auth/google',
  },
  STATEMENTS: {
    UPLOAD_SINGLE: '/process-statement',
    UPLOAD_MULTIPLE: '/process-multiple-statements',
    LIST: '/statements',
    DETAILS: '/statement',
  },
  TRANSACTIONS: {
    LIST: '/transactions',
    SEARCH: '/search-transactions',
  },
  CHAT: {
    SEND: '/chat',
  },
  LOGS: {
    STREAM: '/stream-logs',
  },
};

// ============================================
// FILE UPLOAD
// ============================================

export const FILE_UPLOAD = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ACCEPTED_TYPES: ['.pdf'],
  ACCEPTED_MIME_TYPES: ['application/pdf'],
  MAX_FILES: 10,
};

// ============================================
// PAGINATION
// ============================================

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [10, 25, 50, 100],
};

// ============================================
// DATE FORMATS
// ============================================

export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',
  LONG: 'MMMM d, yyyy',
  FULL: 'EEEE, MMMM d, yyyy',
  TIME: 'h:mm a',
  DATETIME: 'MMM d, yyyy h:mm a',
};

// ============================================
// TOAST CONFIGURATION
// ============================================

export const TOAST_CONFIG = {
  duration: 4000,
  position: 'top-right',
  style: {
    borderRadius: RADIUS.lg,
    padding: SPACING[4],
  },
  success: {
    iconTheme: {
      primary: COLORS.success[600],
      secondary: '#fff',
    },
  },
  error: {
    iconTheme: {
      primary: COLORS.danger[600],
      secondary: '#fff',
    },
  },
};

// ============================================
// ACCESSIBILITY
// ============================================

export const A11Y = {
  MIN_TOUCH_TARGET: 44, // pixels
  MIN_TEXT_SIZE: 14, // pixels
  FOCUS_RING_WIDTH: 2, // pixels
  FOCUS_RING_COLOR: COLORS.primary[500],
};
