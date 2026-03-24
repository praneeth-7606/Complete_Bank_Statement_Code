import { motion } from 'framer-motion';
import { ArrowRight, Play, TrendingUp, DollarSign, PieChart, BarChart } from 'lucide-react';
import { floatingAnimation } from '../../utils/animations';
import Button from '../common/Button';

/**
 * HeroSection Component
 * Landing page hero with animated gradient and floating icons
 */
const HeroSection = ({ onGetStarted, onWatchDemo }) => {
  const floatingIcons = [
    { Icon: TrendingUp, delay: 0, x: '10%', y: '20%' },
    { Icon: DollarSign, delay: 0.2, x: '80%', y: '30%' },
    { Icon: PieChart, delay: 0.4, x: '15%', y: '70%' },
    { Icon: BarChart, delay: 0.6, x: '85%', y: '65%' }
  ];
  
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-900 via-purple-900 to-indigo-800 animate-gradient-x">
      {/* Floating Icons */}
      {floatingIcons.map(({ Icon, delay, x, y }, index) => (
        <motion.div
          key={index}
          className="absolute text-white/10"
          style={{ left: x, top: y }}
          animate={floatingAnimation}
          transition={{ delay, duration: 3, repeat: Infinity }}
        >
          <Icon size={80} />
        </motion.div>
      ))}
      
      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center px-4 py-2 bg-white/10 backdrop-blur-md rounded-full text-white text-sm font-medium mb-8"
          >
            <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse" />
            AI-Powered Financial Analysis
          </motion.div>
          
          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight"
          >
            Transform Your
            <span className="block bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Financial Data
            </span>
            Into Insights
          </motion.h1>
          
          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="text-xl md:text-2xl text-indigo-200 mb-12 max-w-3xl mx-auto"
          >
            Upload your bank statements and let AI analyze, categorize, and provide intelligent insights about your spending patterns.
          </motion.p>
          
          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.8 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Button
              variant="primary"
              size="lg"
              icon={ArrowRight}
              iconPosition="right"
              onClick={onGetStarted}
              className="bg-white text-indigo-600 hover:bg-gray-100 shadow-2xl"
            >
              Get Started Free
            </Button>
            <Button
              variant="ghost"
              size="lg"
              icon={Play}
              iconPosition="left"
              onClick={onWatchDemo}
              className="text-white border-2 border-white/30 hover:bg-white/10"
            >
              Watch Demo
            </Button>
          </motion.div>
          
          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9, duration: 0.8 }}
            className="mt-16 grid grid-cols-3 gap-8 max-w-2xl mx-auto"
          >
            {[
              { value: '10,000+', label: 'Statements Processed' },
              { value: '98%', label: 'Accuracy Rate' },
              { value: '5,000+', label: 'Happy Users' }
            ].map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                  {stat.value}
                </div>
                <div className="text-sm text-indigo-300">
                  {stat.label}
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
        
        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-6 h-10 border-2 border-white/30 rounded-full flex items-start justify-center p-2"
          >
            <motion.div
              animate={{ y: [0, 12, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="w-1 h-2 bg-white rounded-full"
            />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};

export default HeroSection;
