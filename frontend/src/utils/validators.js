/**
 * Validation utility functions for the FinanceAI application
 */

import { FILE_UPLOAD } from './constants';

// ============================================
// EMAIL VALIDATION
// ============================================

/**
 * Validate email address format
 * @param {string} email - Email address to validate
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateEmail = (email) => {
  if (!email) {
    return { isValid: false, error: 'Email is required' };
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return { isValid: false, error: 'Please enter a valid email address' };
  }
  
  return { isValid: true, error: null };
};

// ============================================
// PASSWORD VALIDATION
// ============================================

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @param {object} options - Validation options
 * @returns {object} { isValid: boolean, error: string, strength: string }
 */
export const validatePassword = (password, options = {}) => {
  const {
    minLength = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecialChars = false,
  } = options;
  
  if (!password) {
    return { isValid: false, error: 'Password is required', strength: 'none' };
  }
  
  if (password.length < minLength) {
    return {
      isValid: false,
      error: `Password must be at least ${minLength} characters long`,
      strength: 'weak',
    };
  }
  
  if (requireUppercase && !/[A-Z]/.test(password)) {
    return {
      isValid: false,
      error: 'Password must contain at least one uppercase letter',
      strength: 'weak',
    };
  }
  
  if (requireLowercase && !/[a-z]/.test(password)) {
    return {
      isValid: false,
      error: 'Password must contain at least one lowercase letter',
      strength: 'weak',
    };
  }
  
  if (requireNumbers && !/\d/.test(password)) {
    return {
      isValid: false,
      error: 'Password must contain at least one number',
      strength: 'medium',
    };
  }
  
  if (requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return {
      isValid: false,
      error: 'Password must contain at least one special character',
      strength: 'medium',
    };
  }
  
  // Calculate password strength
  let strength = 'weak';
  if (password.length >= 12 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password) && /[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    strength = 'strong';
  } else if (password.length >= 10 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password)) {
    strength = 'medium';
  }
  
  return { isValid: true, error: null, strength };
};

/**
 * Validate password confirmation
 * @param {string} password - Original password
 * @param {string} confirmPassword - Confirmation password
 * @returns {object} { isValid: boolean, error: string }
 */
export const validatePasswordConfirmation = (password, confirmPassword) => {
  if (!confirmPassword) {
    return { isValid: false, error: 'Please confirm your password' };
  }
  
  if (password !== confirmPassword) {
    return { isValid: false, error: 'Passwords do not match' };
  }
  
  return { isValid: true, error: null };
};

// ============================================
// FILE VALIDATION
// ============================================

/**
 * Validate file type
 * @param {File} file - File to validate
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateFileType = (file) => {
  if (!file) {
    return { isValid: false, error: 'No file provided' };
  }
  
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
  
  if (!FILE_UPLOAD.ACCEPTED_TYPES.includes(fileExtension)) {
    return {
      isValid: false,
      error: `Only ${FILE_UPLOAD.ACCEPTED_TYPES.join(', ')} files are allowed`,
    };
  }
  
  if (!FILE_UPLOAD.ACCEPTED_MIME_TYPES.includes(file.type)) {
    return {
      isValid: false,
      error: 'Invalid file type',
    };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate file size
 * @param {File} file - File to validate
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateFileSize = (file) => {
  if (!file) {
    return { isValid: false, error: 'No file provided' };
  }
  
  if (file.size > FILE_UPLOAD.MAX_FILE_SIZE) {
    const maxSizeMB = (FILE_UPLOAD.MAX_FILE_SIZE / (1024 * 1024)).toFixed(0);
    return {
      isValid: false,
      error: `File size must be less than ${maxSizeMB}MB`,
    };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate file (type and size)
 * @param {File} file - File to validate
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateFile = (file) => {
  const typeValidation = validateFileType(file);
  if (!typeValidation.isValid) {
    return typeValidation;
  }
  
  const sizeValidation = validateFileSize(file);
  if (!sizeValidation.isValid) {
    return sizeValidation;
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate multiple files
 * @param {File[]} files - Files to validate
 * @returns {object} { isValid: boolean, error: string, invalidFiles: File[] }
 */
export const validateFiles = (files) => {
  if (!files || files.length === 0) {
    return { isValid: false, error: 'No files provided', invalidFiles: [] };
  }
  
  if (files.length > FILE_UPLOAD.MAX_FILES) {
    return {
      isValid: false,
      error: `Maximum ${FILE_UPLOAD.MAX_FILES} files allowed`,
      invalidFiles: [],
    };
  }
  
  const invalidFiles = [];
  for (const file of files) {
    const validation = validateFile(file);
    if (!validation.isValid) {
      invalidFiles.push({ file, error: validation.error });
    }
  }
  
  if (invalidFiles.length > 0) {
    return {
      isValid: false,
      error: `${invalidFiles.length} file(s) are invalid`,
      invalidFiles,
    };
  }
  
  return { isValid: true, error: null, invalidFiles: [] };
};

// ============================================
// FORM VALIDATION
// ============================================

/**
 * Validate required field
 * @param {any} value - Value to validate
 * @param {string} fieldName - Field name for error message
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateRequired = (value, fieldName = 'This field') => {
  if (value === null || value === undefined || value === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }
  
  if (typeof value === 'string' && value.trim() === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate minimum length
 * @param {string} value - Value to validate
 * @param {number} minLength - Minimum length
 * @param {string} fieldName - Field name for error message
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateMinLength = (value, minLength, fieldName = 'This field') => {
  if (!value || value.length < minLength) {
    return {
      isValid: false,
      error: `${fieldName} must be at least ${minLength} characters`,
    };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate maximum length
 * @param {string} value - Value to validate
 * @param {number} maxLength - Maximum length
 * @param {string} fieldName - Field name for error message
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateMaxLength = (value, maxLength, fieldName = 'This field') => {
  if (value && value.length > maxLength) {
    return {
      isValid: false,
      error: `${fieldName} must be less than ${maxLength} characters`,
    };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate number range
 * @param {number} value - Value to validate
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @param {string} fieldName - Field name for error message
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateRange = (value, min, max, fieldName = 'This field') => {
  if (value === null || value === undefined) {
    return { isValid: false, error: `${fieldName} is required` };
  }
  
  const numValue = Number(value);
  if (isNaN(numValue)) {
    return { isValid: false, error: `${fieldName} must be a number` };
  }
  
  if (numValue < min || numValue > max) {
    return {
      isValid: false,
      error: `${fieldName} must be between ${min} and ${max}`,
    };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate phone number (Indian format)
 * @param {string} phone - Phone number to validate
 * @returns {object} { isValid: boolean, error: string }
 */
export const validatePhone = (phone) => {
  if (!phone) {
    return { isValid: false, error: 'Phone number is required' };
  }
  
  // Remove spaces, dashes, and parentheses
  const cleanPhone = phone.replace(/[\s\-()]/g, '');
  
  // Indian phone number: 10 digits, optionally starting with +91 or 91
  const phoneRegex = /^(\+91|91)?[6-9]\d{9}$/;
  
  if (!phoneRegex.test(cleanPhone)) {
    return { isValid: false, error: 'Please enter a valid phone number' };
  }
  
  return { isValid: true, error: null };
};

/**
 * Validate date
 * @param {string|Date} date - Date to validate
 * @param {object} options - Validation options
 * @returns {object} { isValid: boolean, error: string }
 */
export const validateDate = (date, options = {}) => {
  const { minDate, maxDate, fieldName = 'Date' } = options;
  
  if (!date) {
    return { isValid: false, error: `${fieldName} is required` };
  }
  
  const dateObj = new Date(date);
  if (isNaN(dateObj.getTime())) {
    return { isValid: false, error: `${fieldName} is invalid` };
  }
  
  if (minDate) {
    const minDateObj = new Date(minDate);
    if (dateObj < minDateObj) {
      return {
        isValid: false,
        error: `${fieldName} must be after ${minDateObj.toLocaleDateString()}`,
      };
    }
  }
  
  if (maxDate) {
    const maxDateObj = new Date(maxDate);
    if (dateObj > maxDateObj) {
      return {
        isValid: false,
        error: `${fieldName} must be before ${maxDateObj.toLocaleDateString()}`,
      };
    }
  }
  
  return { isValid: true, error: null };
};

// ============================================
// FORM VALIDATION HELPER
// ============================================

/**
 * Validate entire form
 * @param {object} formData - Form data to validate
 * @param {object} validationRules - Validation rules for each field
 * @returns {object} { isValid: boolean, errors: object }
 */
export const validateForm = (formData, validationRules) => {
  const errors = {};
  let isValid = true;
  
  for (const [field, rules] of Object.entries(validationRules)) {
    const value = formData[field];
    
    for (const rule of rules) {
      const validation = rule(value);
      if (!validation.isValid) {
        errors[field] = validation.error;
        isValid = false;
        break; // Stop at first error for this field
      }
    }
  }
  
  return { isValid, errors };
};
