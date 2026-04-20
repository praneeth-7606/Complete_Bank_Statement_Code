/**
 * Performance Utilities - Design System v2.0
 * React optimization patterns and helpers
 */

import { useCallback, useMemo, useRef, useEffect } from 'react'

/**
 * Debounce hook for expensive operations
 * Usage: const debouncedValue = useDebounce(value, 500)
 */
export const useDebounce = (value, delay = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

/**
 * Throttle hook for frequent events (scroll, resize)
 * Usage: const throttledValue = useThrottle(value, 200)
 */
export const useThrottle = (value, limit = 200) => {
  const [throttledValue, setThrottledValue] = useState(value)
  const lastRan = useRef(Date.now())

  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value)
        lastRan.current = Date.now()
      }
    }, limit - (Date.now() - lastRan.current))

    return () => clearTimeout(handler)
  }, [value, limit])

  return throttledValue
}

/**
 * Memoized callback that only changes when dependencies change
 * Prevents unnecessary re-renders in child components
 */
export const useStableCallback = (callback, deps) => {
  return useCallback(callback, deps)
}

/**
 * Memoized value that only recalculates when dependencies change
 * Use for expensive calculations
 */
export const useStableValue = (factory, deps) => {
  return useMemo(factory, deps)
}

/**
 * Previous value hook - useful for animations and comparisons
 */
export const usePrevious = (value) => {
  const ref = useRef()
  
  useEffect(() => {
    ref.current = value
  }, [value])
  
  return ref.current
}

/**
 * Intersection Observer hook for lazy loading
 * Usage: const [ref, isVisible] = useInView({ threshold: 0.1 })
 */
export const useInView = (options = {}) => {
  const [isVisible, setIsVisible] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry.isIntersecting)
    }, options)

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => {
      if (ref.current) {
        observer.unobserve(ref.current)
      }
    }
  }, [options])

  return [ref, isVisible]
}

/**
 * Batch state updates to reduce re-renders
 */
export const batchUpdates = (callback) => {
  // React 18+ automatically batches updates
  // This is a placeholder for future optimization
  callback()
}

/**
 * Format large numbers for display
 */
export const formatNumber = (num, decimals = 2) => {
  if (num === null || num === undefined) return '0'
  
  const absNum = Math.abs(num)
  
  if (absNum >= 10000000) { // 1 Crore
    return `₹${(num / 10000000).toFixed(decimals)}Cr`
  } else if (absNum >= 100000) { // 1 Lakh
    return `₹${(num / 100000).toFixed(decimals)}L`
  } else if (absNum >= 1000) { // 1 Thousand
    return `₹${(num / 1000).toFixed(decimals)}K`
  }
  
  return `₹${num.toFixed(decimals)}`
}

/**
 * Memoization helper for expensive calculations
 */
export const memoize = (fn) => {
  const cache = new Map()
  
  return (...args) => {
    const key = JSON.stringify(args)
    
    if (cache.has(key)) {
      return cache.get(key)
    }
    
    const result = fn(...args)
    cache.set(key, result)
    return result
  }
}

/**
 * Chunk array for virtual scrolling
 */
export const chunkArray = (array, size) => {
  const chunks = []
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size))
  }
  return chunks
}

/**
 * Lazy load component wrapper
 */
export const lazyWithPreload = (factory) => {
  const Component = lazy(factory)
  Component.preload = factory
  return Component
}

import { useState } from 'react'
import { lazy } from 'react'
