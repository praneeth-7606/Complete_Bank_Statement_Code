/**
 * SkeletonLoader Component
 * Loading placeholder with shimmer animation
 * 
 * @param {string} variant - Skeleton type: 'text', 'card', 'circle', 'rectangle', 'stat-card', 'transaction-row', 'chart'
 * @param {number} count - Number of skeleton items to render
 * @param {string} className - Additional CSS classes
 */
const SkeletonLoader = ({
  variant = 'text',
  count = 1,
  className = ''
}) => {
  // Base shimmer styles
  const shimmerBase = 'animate-shimmer bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%]';
  
  // Variant-specific components
  const variants = {
    text: (
      <div className={`h-4 ${shimmerBase} rounded ${className}`} />
    ),
    
    card: (
      <div className={`bg-white rounded-2xl p-6 shadow-lg ${className}`}>
        <div className={`h-12 w-12 ${shimmerBase} rounded-full mb-4`} />
        <div className={`h-4 ${shimmerBase} rounded mb-2 w-1/2`} />
        <div className={`h-6 ${shimmerBase} rounded w-3/4`} />
      </div>
    ),
    
    circle: (
      <div className={`rounded-full ${shimmerBase} ${className}`} />
    ),
    
    rectangle: (
      <div className={`${shimmerBase} rounded ${className}`} />
    ),
    
    'stat-card': (
      <div className={`bg-white rounded-2xl p-6 shadow-lg ${className}`}>
        <div className="flex items-start justify-between mb-4">
          <div className={`h-12 w-12 ${shimmerBase} rounded-full`} />
        </div>
        <div className={`h-3 ${shimmerBase} rounded mb-2 w-1/3`} />
        <div className={`h-8 ${shimmerBase} rounded w-2/3`} />
      </div>
    ),
    
    'transaction-row': (
      <div className={`flex items-center justify-between p-4 bg-white rounded-lg ${className}`}>
        <div className="flex items-center gap-4 flex-1">
          <div className={`h-10 w-10 ${shimmerBase} rounded-full`} />
          <div className="flex-1">
            <div className={`h-4 ${shimmerBase} rounded mb-2 w-1/3`} />
            <div className={`h-3 ${shimmerBase} rounded w-1/4`} />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className={`h-6 w-20 ${shimmerBase} rounded-full`} />
          <div className={`h-5 w-24 ${shimmerBase} rounded`} />
        </div>
      </div>
    ),
    
    chart: (
      <div className={`bg-white rounded-2xl p-6 shadow-lg ${className}`}>
        <div className={`h-6 ${shimmerBase} rounded mb-6 w-1/4`} />
        <div className={`h-64 ${shimmerBase} rounded`} />
      </div>
    )
  };
  
  // Render multiple skeletons if count > 1
  if (count > 1) {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, index) => (
          <div key={index}>
            {variants[variant]}
          </div>
        ))}
      </div>
    );
  }
  
  return variants[variant];
};

export default SkeletonLoader;
