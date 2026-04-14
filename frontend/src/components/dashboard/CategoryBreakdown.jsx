import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { chartVariants } from '../../utils/animations';
import { Card } from '../common';

/**
 * CategoryBreakdown Component
 * Pie chart showing spending by category
 */
const CategoryBreakdown = ({ data = [], title = "Spending by Category" }) => {
  // Default data if none provided
  const defaultData = [
    { name: 'Food & Dining', value: 12500, color: '#f97316' },
    { name: 'Shopping', value: 8900, color: '#a855f7' },
    { name: 'Transportation', value: 5600, color: '#3b82f6' },
    { name: 'Bills & Utilities', value: 7800, color: '#eab308' },
    { name: 'Entertainment', value: 4200, color: '#ec4899' },
    { name: 'Other', value: 3000, color: '#6b7280' }
  ];

  const chartData = data.length > 0 ? data : defaultData;

  // Calculate total
  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const percentage = ((payload[0].value / total) * 100).toFixed(1);
      return (
        <div className="bg-white p-4 rounded-lg shadow-xl border border-gray-200">
          <p className="font-semibold text-gray-900 mb-1">{payload[0].name}</p>
          <p className="text-sm text-gray-600">
            ₹{payload[0].value.toLocaleString()} ({percentage}%)
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom label
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show label for small slices

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-xs font-semibold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card className="p-6">
      <motion.div variants={chartVariants} initial="hidden" animate="visible">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">{title}</h3>

        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
              animationDuration={1500}
              animationBegin={0}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="grid grid-cols-2 gap-3 mt-6">
          {chartData.map((item, index) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            return (
              <div key={index} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-600 truncate">{item.name}</p>
                  <p className="text-sm font-semibold text-gray-900">
                    ₹{item.value.toLocaleString()} ({percentage}%)
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </Card>
  );
};

export default CategoryBreakdown;
