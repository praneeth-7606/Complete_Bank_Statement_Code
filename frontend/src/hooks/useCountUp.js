import { useState, useEffect } from 'react';

/**
 * Custom hook for animated number counting
 * @param {number} end - The target number to count up to
 * @param {number} duration - Duration of the animation in milliseconds (default: 2000)
 * @param {boolean} start - Whether to start the animation (default: true)
 * @returns {number} - The current count value
 */
export const useCountUp = (end, duration = 2000, start = true) => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    if (!start) return;
    
    let startTime;
    let animationFrame;
    
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = timestamp - startTime;
      const percentage = Math.min(progress / duration, 1);
      
      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - percentage, 4);
      
      setCount(Math.floor(end * easeOutQuart));
      
      if (percentage < 1) {
        animationFrame = requestAnimationFrame(animate);
      } else {
        setCount(end);
      }
    };
    
    animationFrame = requestAnimationFrame(animate);
    
    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [end, duration, start]);
  
  return count;
};
