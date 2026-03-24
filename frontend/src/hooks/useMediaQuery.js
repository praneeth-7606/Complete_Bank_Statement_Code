import { useState, useEffect } from 'react';

/**
 * Custom hook for responsive behavior based on media queries
 * @param {string} query - Media query string (e.g., '(min-width: 768px)')
 * @returns {boolean} - Whether the media query matches
 */
export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);
  
  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    
    // Set initial value
    setMatches(mediaQuery.matches);
    
    // Create event listener
    const handler = (event) => setMatches(event.matches);
    
    // Add listener
    mediaQuery.addEventListener('change', handler);
    
    // Cleanup
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);
  
  return matches;
};

// Predefined breakpoint hooks for convenience
export const useIsMobile = () => useMediaQuery('(max-width: 639px)');
export const useIsTablet = () => useMediaQuery('(min-width: 640px) and (max-width: 1023px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)');
export const useIsLargeDesktop = () => useMediaQuery('(min-width: 1280px)');
