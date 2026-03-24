import { motion } from 'framer-motion';
import { useCountUp } from '../../hooks/useCountUp';
import { useIntersectionObserver } from '../../hooks/useIntersectionObserver';

/**
 * StatsCounter Component
 * Animated statistics counter triggered on scroll
 */
const StatsCounter = ({ stats }) => {
  const [ref, isVisible] = useIntersectionObserver({ threshold: 0.3 });
  
  return (
    <section ref={ref} className="py-20 bg-gradient-to-r from-indigo-600 to-purple-600">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          {stats.map((stat, index) => (
            <StatItem
              key={index}
              {...stat}
              isVisible={isVisible}
              delay={index * 0.2}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

const StatItem = ({ icon: Icon, value, suffix = '', label, isVisible, delay }) => {
  const animatedValue = useCountUp(value, 2000, isVisible);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={isVisible ? { opacity: 1, y: 0 } : {}}
      transition={{ delay, duration: 0.6 }}
      className="text-center text-white"
    >
      {/* Icon */}
      <motion.div
        animate={isVisible ? { scale: [1, 1.2, 1] } : {}}
        transition={{ delay: delay + 0.3, duration: 0.5 }}
        className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4"
      >
        <Icon size={32} className="animate-pulse-glow" />
      </motion.div>
      
      {/* Value */}
      <div className="text-5xl font-bold mb-2">
        {animatedValue.toLocaleString()}{suffix}
      </div>
      
      {/* Label */}
      <div className="text-lg text-indigo-100">
        {label}
      </div>
    </motion.div>
  );
};

export default StatsCounter;
