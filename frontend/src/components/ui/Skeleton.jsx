/**
 * Unified Skeleton Loader - Design System v2.0
 * Loading placeholders with shimmer animation
 */
const Skeleton = ({
  variant = 'text',
  count = 1,
  className = '',
  ...props
}) => {
  const shimmer = 'animate-pulse bg-gradient-to-r from-neutral-200 via-neutral-300 to-neutral-200 bg-[length:200%_100%]'
  
  const variants = {
    text: <div className={`h-4 ${shimmer} rounded ${className}`} />,
    
    title: <div className={`h-8 ${shimmer} rounded w-1/2 ${className}`} />,
    
    card: (
      <div className={`bg-white rounded-2xl p-6 shadow-md ${className}`}>
        <div className={`h-12 w-12 ${shimmer} rounded-xl mb-4`} />
        <div className={`h-4 ${shimmer} rounded mb-2 w-1/2`} />
        <div className={`h-6 ${shimmer} rounded w-3/4`} />
      </div>
    ),
    
    circle: <div className={`rounded-full ${shimmer} ${className}`} />,
    
    rectangle: <div className={`${shimmer} rounded-xl ${className}`} />,
    
    'stat-card': (
      <div className={`bg-white rounded-2xl p-6 shadow-md ${className}`}>
        <div className="flex items-start justify-between mb-4">
          <div className={`h-12 w-12 ${shimmer} rounded-xl`} />
        </div>
        <div className={`h-3 ${shimmer} rounded mb-2 w-1/3`} />
        <div className={`h-8 ${shimmer} rounded w-2/3`} />
      </div>
    ),
    
    'table-row': (
      <div className={`flex items-center gap-4 p-4 bg-white rounded-xl ${className}`}>
        <div className={`h-10 w-10 ${shimmer} rounded-full flex-shrink-0`} />
        <div className="flex-1 space-y-2">
          <div className={`h-4 ${shimmer} rounded w-1/3`} />
          <div className={`h-3 ${shimmer} rounded w-1/4`} />
        </div>
        <div className={`h-6 w-20 ${shimmer} rounded-full`} />
      </div>
    ),
    
    chart: (
      <div className={`bg-white rounded-2xl p-6 shadow-md ${className}`}>
        <div className={`h-6 ${shimmer} rounded mb-6 w-1/4`} />
        <div className={`h-64 ${shimmer} rounded-xl`} />
      </div>
    )
  }
  
  if (count > 1) {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, index) => (
          <div key={index}>{variants[variant]}</div>
        ))}
      </div>
    )
  }
  
  return variants[variant]
}

export default Skeleton
