import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for detecting when an element enters the viewport
 * Useful for triggering scroll-based animations
 * @param {Object} options - IntersectionObserver options
 * @returns {Array} - [ref, isIntersecting]
 */
export const useIntersectionObserver = (options = {}) => {
  const [isIntersecting, setIsIntersecting] = useState(false);
  const [hasIntersected, setHasIntersected] = useState(false);
  const ref = useRef(null);
  
  const defaultOptions = {
    threshold: 0.1,
    triggerOnce: true,
    ...options
  };
  
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        const isElementIntersecting = entry.isIntersecting;
        setIsIntersecting(isElementIntersecting);
        
        if (isElementIntersecting && !hasIntersected) {
          setHasIntersected(true);
          
          // If triggerOnce is true, disconnect after first intersection
          if (defaultOptions.triggerOnce) {
            observer.disconnect();
          }
        }
      },
      {
        threshold: defaultOptions.threshold,
        rootMargin: defaultOptions.rootMargin || '0px'
      }
    );
    
    observer.observe(element);
    
    return () => {
      if (element) {
        observer.unobserve(element);
      }
    };
  }, [defaultOptions.threshold, defaultOptions.rootMargin, defaultOptions.triggerOnce, hasIntersected]);
  
  return [ref, isIntersecting || hasIntersected];
};
