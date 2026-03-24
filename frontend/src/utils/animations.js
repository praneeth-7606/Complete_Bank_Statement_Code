/**
 * Animation Utilities for FinanceAI
 * Reusable animation variants for Framer Motion
 */

// Page transition animations
export const pageTransition = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3, ease: "easeInOut" }
};

// Staggered container and item animations
export const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

export const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" }
  }
};

// Card hover animations
export const cardHover = {
  rest: { 
    scale: 1, 
    boxShadow: "0 4px 6px rgba(0,0,0,0.1)" 
  },
  hover: { 
    scale: 1.02, 
    boxShadow: "0 20px 40px rgba(0,0,0,0.15)",
    transition: { duration: 0.2 }
  }
};

// Button animations
export const buttonVariants = {
  hover: { 
    scale: 1.02, 
    boxShadow: "0 10px 20px rgba(0,0,0,0.15)" 
  },
  tap: { scale: 0.98 },
  disabled: { opacity: 0.5 }
};

// Modal animations
export const modalVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.9 
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.2, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    scale: 0.9,
    transition: { duration: 0.15, ease: "easeIn" }
  }
};

// Backdrop animations
export const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { duration: 0.2 }
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.15 }
  }
};

// Slide animations
export const slideInLeft = {
  hidden: { opacity: 0, x: -20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: "easeOut" }
  }
};

export const slideInRight = {
  hidden: { opacity: 0, x: 20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: "easeOut" }
  }
};

// Fade animations
export const fadeIn = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { duration: 0.3 }
  }
};

// Scale animations
export const scaleIn = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3, ease: "easeOut" }
  }
};

// Floating animation
export const floatingAnimation = {
  y: [0, -20, 0],
  transition: {
    duration: 3,
    repeat: Infinity,
    ease: "easeInOut"
  }
};

// Shake animation (for errors)
export const shakeAnimation = {
  x: [0, -10, 10, -10, 10, 0],
  transition: { duration: 0.5 }
};

// Success animation
export const successVariants = {
  initial: { scale: 0.8, opacity: 0 },
  animate: { 
    scale: 1, 
    opacity: 1,
    transition: { duration: 0.3, ease: "easeOut" }
  },
  exit: { 
    scale: 1.2, 
    opacity: 0,
    transition: { duration: 0.2 }
  }
};

// Confetti configuration
export const confettiConfig = {
  particleCount: 100,
  spread: 70,
  origin: { y: 0.6 },
  colors: ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444']
};

// Shimmer effect configuration
export const shimmerAnimation = {
  backgroundImage: "linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)",
  backgroundSize: "200% 100%",
  animation: "shimmer 1.5s infinite"
};

// Parallax effect
export const parallaxVariants = (scrollY, multiplier = 0.5) => ({
  initial: { y: 0 },
  animate: { y: scrollY * multiplier }
});

// Dropdown menu animations
export const dropdownVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95,
    y: -10
  },
  visible: { 
    opacity: 1, 
    scale: 1,
    y: 0,
    transition: { duration: 0.15, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    scale: 0.95,
    y: -10,
    transition: { duration: 0.1 }
  }
};

// Toast notification animations
export const toastVariants = {
  hidden: { 
    opacity: 0, 
    x: 100,
    scale: 0.8
  },
  visible: { 
    opacity: 1, 
    x: 0,
    scale: 1,
    transition: { duration: 0.3, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    x: 100,
    scale: 0.8,
    transition: { duration: 0.2 }
  }
};

// Skeleton loader shimmer
export const skeletonShimmer = {
  animate: {
    backgroundPosition: ["200% 0", "-200% 0"],
  },
  transition: {
    duration: 1.5,
    repeat: Infinity,
    ease: "linear"
  }
};

// Chart animation
export const chartVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: { 
      duration: 0.5, 
      ease: "easeOut",
      delay: 0.2
    }
  }
};

// List item stagger
export const listItemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i) => ({
    opacity: 1,
    x: 0,
    transition: {
      delay: i * 0.05,
      duration: 0.3,
      ease: "easeOut"
    }
  })
};

// Expand/Collapse animations
export const expandVariants = {
  collapsed: { 
    height: 0, 
    opacity: 0,
    transition: { duration: 0.2 }
  },
  expanded: { 
    height: "auto", 
    opacity: 1,
    transition: { duration: 0.3, ease: "easeOut" }
  }
};

// Progress bar animation
export const progressVariants = {
  initial: { width: 0 },
  animate: (progress) => ({
    width: `${progress}%`,
    transition: { duration: 0.5, ease: "easeOut" }
  })
};
