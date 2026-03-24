import { useState, useCallback } from 'react';

/**
 * Custom hook for managing complex animation states
 * @returns {Object} - Animation state and control functions
 */
export const useAnimation = () => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [animationState, setAnimationState] = useState('idle');
  
  const startAnimation = useCallback((stateName = 'animating') => {
    setIsAnimating(true);
    setAnimationState(stateName);
  }, []);
  
  const stopAnimation = useCallback(() => {
    setIsAnimating(false);
    setAnimationState('idle');
  }, []);
  
  const setCustomState = useCallback((stateName) => {
    setAnimationState(stateName);
  }, []);
  
  const resetAnimation = useCallback(() => {
    setIsAnimating(false);
    setAnimationState('idle');
  }, []);
  
  return {
    isAnimating,
    animationState,
    startAnimation,
    stopAnimation,
    setCustomState,
    resetAnimation
  };
};

/**
 * Custom hook for managing hover state with animation
 * @returns {Object} - Hover state and handlers
 */
export const useHoverAnimation = () => {
  const [isHovered, setIsHovered] = useState(false);
  
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
  }, []);
  
  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
  }, []);
  
  return {
    isHovered,
    handleMouseEnter,
    handleMouseLeave,
    hoverProps: {
      onMouseEnter: handleMouseEnter,
      onMouseLeave: handleMouseLeave
    }
  };
};

/**
 * Custom hook for managing focus state with animation
 * @returns {Object} - Focus state and handlers
 */
export const useFocusAnimation = () => {
  const [isFocused, setIsFocused] = useState(false);
  
  const handleFocus = useCallback(() => {
    setIsFocused(true);
  }, []);
  
  const handleBlur = useCallback(() => {
    setIsFocused(false);
  }, []);
  
  return {
    isFocused,
    handleFocus,
    handleBlur,
    focusProps: {
      onFocus: handleFocus,
      onBlur: handleBlur
    }
  };
};
