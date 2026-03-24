import { motion } from 'framer-motion';
import { staggerItem } from '../../utils/animations';

/**
 * FeatureCard Component
 * Displays a feature with icon, title, and description
 */
const FeatureCard = ({ icon: Icon, title, description, delay = 0 }) => {
  return (
    <motion.div
      variants={staggerItem}
      whileHover={{ 
        scale: 1.05, 
        boxShadow: '0 20px 40px rgba(99, 102, 241, 0.2)',
        rotate: [0, 1, -1, 0]
      }}
      transition={{ duration: 0.3 }}
      className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100 hover:border-indigo-200"
    >
      {/* Icon */}
      <motion.div
        whileHover={{ rotate: 360 }}
        transition={{ duration: 0.6 }}
        className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 shadow-lg"
      >
        <Icon size={32} className="text-white" />
      </motion.div>
      
      {/* Title */}
      <h3 className="text-xl font-semibold text-gray-900 mb-3">
        {title}
      </h3>
      
      {/* Description */}
      <p className="text-gray-600 leading-relaxed">
        {description}
      </p>
    </motion.div>
  );
};

export default FeatureCard;
