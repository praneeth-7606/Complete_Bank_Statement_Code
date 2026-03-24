import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { chartVariants } from '../../utils/animations';
import { Card } from '../common';

/**
 * SpendingChart Component
 * Monthly spending trend visualization with animated line chart
 */
const SpendingChart = ({ data = [], title = "Monthly Spending Trend" }) => {
  // Default data if none provided
  const defaultData = [
    { month: 'Jan', income: 45000, expenses: 32000 },
    { month: 'Feb', income: 52000, expenses: 38000 },
    { month: 'Mar', income: 48000, expenses: 35000 },
    { month: 'Apr', income: 61000, expenses: 42000 },
    { month: 'May', income: 55000, expenses: 39000 },
    { month: 'Jun', income: 58000, expenses: 41000 }
  ];
  
  const chartData = data.length > 0 ? data : defaultData;
  
  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 rounded-lg shadow-xl border border-gray-200">
          <p className="font-semibold text-gray-900 mb-2">{payload[0].payload.month}</p>
          <div className="space-y-1">
            <p className="text-sm text-green-600">
              Income: ₹{payload[0].value?.toLocaleString()}
            </p>
            <p className="text-sm text-red-600">
              Expenses: ₹{payload[1]?.value?.toLocaleString()}
            </p>
            <p className="text-sm text-blue-600 font-semibold">
              Net: ₹{(payload[0].value - (payload[1]?.value || 0)).toLocaleString()}
            </p>
          </div>
        </div>
      );
    }
    return null;
  };
  
  return (
    <Card className="p-6">
      <motion.div variants={chartVariants} initial="hidden" animate="visible">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">{title}</h3>
        
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorExpenses" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="month" 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#6b7280"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="income"
              stroke="#22c55e"
              strokeWidth={2}
              fill="url(#colorIncome)"
              animationDuration={1500}
            />
            <Area
              type="monotone"
              dataKey="expenses"
              stroke="#ef4444"
              strokeWidth={2}
              fill="url(#colorExpenses)"
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
        
        {/* Legend */}
        <div className="flex items-center justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <span className="text-sm text-gray-600">Income</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full" />
            <span className="text-sm text-gray-600">Expenses</span>
          </div>
        </div>
      </motion.div>
    </Card>
  );
};

export default SpendingChart;
