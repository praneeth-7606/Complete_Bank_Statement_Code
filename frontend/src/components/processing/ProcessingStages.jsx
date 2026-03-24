import { motion } from 'framer-motion';
import {
  FileText,
  Brain,
  Tags,
  Lightbulb,
  CheckCircle,
  Circle,
} from 'lucide-react';
import { PROCESSING_STAGES } from '../../utils/constants';

/**
 * ProcessingStages Component
 * Displays visual indicators for processing stages with progress
 * 
 * @param {number} progress - Current progress (0-100)
 * @param {string} currentStage - Current stage name (optional)
 */
const ProcessingStages = ({ progress = 0 }) => {
  // Icon mapping
  const iconMap = {
    FileText,
    Brain,
    Tags,
    Lightbulb,
    CheckCircle,
  };

  // Determine current stage based on progress
  const getCurrentStage = () => {
    for (const stage of PROCESSING_STAGES) {
      if (progress >= stage.range[0] && progress < stage.range[1]) {
        return stage.name;
      }
    }
    if (progress >= 100) {
      return 'Finalizing';
    }
    return 'Extracting';
  };

  const currentStage = getCurrentStage();

  return (
    <div className="mb-6">
      {/* Stage Indicators */}
      <div className="flex items-center justify-between mb-4">
        {PROCESSING_STAGES.map((stage, index) => {
          const Icon = iconMap[stage.icon] || Circle;
          const isComplete = progress > stage.range[1];
          const isCurrent = currentStage === stage.name;
          const isUpcoming = progress < stage.range[0];

          return (
            <div key={stage.name} className="flex items-center flex-1">
              {/* Stage Circle */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: index * 0.1 }}
                className="relative flex flex-col items-center"
              >
                {/* Icon Circle */}
                <motion.div
                  animate={{
                    scale: isCurrent ? [1, 1.1, 1] : 1,
                    backgroundColor: isComplete
                      ? '#16a34a'
                      : isCurrent
                      ? '#2563eb'
                      : '#e5e7eb',
                  }}
                  transition={{
                    scale: {
                      duration: 1,
                      repeat: isCurrent ? Infinity : 0,
                      ease: 'easeInOut',
                    },
                    backgroundColor: { duration: 0.3 },
                  }}
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center
                    ${isComplete ? 'bg-green-600' : isCurrent ? 'bg-blue-600' : 'bg-gray-200'}
                    transition-all duration-300
                  `}
                >
                  <Icon
                    className={`
                      w-5 h-5
                      ${isComplete || isCurrent ? 'text-white' : 'text-gray-400'}
                    `}
                  />
                </motion.div>

                {/* Stage Label */}
                <motion.p
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 + 0.2 }}
                  className={`
                    text-xs font-medium mt-2 text-center whitespace-nowrap
                    ${isComplete ? 'text-green-600' : isCurrent ? 'text-blue-600' : 'text-gray-400'}
                  `}
                >
                  {stage.name}
                </motion.p>

                {/* Checkmark for completed stages */}
                {isComplete && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute -top-1 -right-1 w-4 h-4 bg-green-600 rounded-full flex items-center justify-center"
                  >
                    <CheckCircle className="w-3 h-3 text-white" />
                  </motion.div>
                )}

                {/* Pulse animation for current stage */}
                {isCurrent && (
                  <motion.div
                    animate={{
                      scale: [1, 1.5, 1],
                      opacity: [0.5, 0, 0.5],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut',
                    }}
                    className="absolute inset-0 w-10 h-10 rounded-full bg-blue-400"
                  />
                )}
              </motion.div>

              {/* Connecting Line */}
              {index < PROCESSING_STAGES.length - 1 && (
                <div className="flex-1 h-0.5 mx-2 bg-gray-200 relative overflow-hidden">
                  <motion.div
                    initial={{ width: '0%' }}
                    animate={{
                      width: isComplete ? '100%' : isCurrent ? '50%' : '0%',
                    }}
                    transition={{ duration: 0.5 }}
                    className={`
                      absolute inset-y-0 left-0
                      ${isComplete ? 'bg-green-600' : 'bg-blue-600'}
                    `}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Current Stage Description */}
      <motion.div
        key={currentStage}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <p className="text-sm text-gray-600">
          {PROCESSING_STAGES.find((s) => s.name === currentStage)?.description ||
            'Processing...'}
        </p>
      </motion.div>
    </div>
  );
};

export default ProcessingStages;
