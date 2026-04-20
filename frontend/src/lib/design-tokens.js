/**
 * FinanceAI Design System
 * Unified design tokens for consistent UI across the application
 * 
 * Based on 60-30-10 Rule:
 * - 60% Primary (brand colors)
 * - 30% Neutral (backgrounds, text)
 * - 10% Accent (context-specific highlights)
 */

export const designTokens = {
  // Color System
  colors: {
    // Primary Brand (60%)
    primary: {
      main: '#0ea5e9',
      light: '#38bdf8',
      dark: '#0284c7',
      contrast: '#ffffff',
    },
    
    // Neutral (30%)
    background: {
      primary: '#fafafa',
      secondary: '#f5f5f5',
      tertiary: '#ffffff',
    },
    text: {
      primary: '#262626',
      secondary: '#525252',
      tertiary: '#737373',
      inverse: '#ffffff',
    },
    border: {
      light: '#e5e5e5',
      default: '#d4d4d4',
      dark: '#a3a3a3',
    },
    
    // Accent (10%) - Context-specific
    semantic: {
      success: '#10b981',
      danger: '#ef4444',
      warning: '#f59e0b',
      info: '#0ea5e9',
      ai: '#8b5cf6',
    },
    
    // Financial Context
    financial: {
      income: '#10b981',
      expense: '#ef4444',
      balance: '#0ea5e9',
      investment: '#8b5cf6',
    },
  },
  
  // Spacing System (8px grid)
  spacing: {
    xs: '0.25rem',    // 4px
    sm: '0.5rem',     // 8px
    md: '1rem',       // 16px
    lg: '1.5rem',     // 24px
    xl: '2rem',       // 32px
    '2xl': '3rem',    // 48px
    '3xl': '4rem',    // 64px
  },
  
  // Border Radius
  radius: {
    sm: '0.375rem',   // 6px
    md: '0.5rem',     // 8px
    lg: '0.75rem',    // 12px
    xl: '1rem',       // 16px
    '2xl': '1.5rem',  // 24px
    full: '9999px',
  },
  
  // Shadows
  shadows: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
  },
  
  // Typography
  typography: {
    fontFamily: {
      sans: 'Inter, system-ui, -apple-system, sans-serif',
      mono: 'JetBrains Mono, monospace',
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem',
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },
  
  // Transitions
  transitions: {
    fast: '150ms',
    base: '200ms',
    slow: '300ms',
    slower: '500ms',
  },
  
  // Z-Index Scale
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },
}

// Helper function to get color with opacity
export const withOpacity = (color, opacity) => {
  return `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`
}

// Gradient presets
export const gradients = {
  primary: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
  success: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  danger: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
  ai: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  sunset: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)',
}

export default designTokens
