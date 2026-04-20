/**
 * Unified Table Component - Design System v2.0
 * Consistent table styling across all pages
 */
const Table = ({
  headers,
  data,
  renderRow,
  emptyMessage = 'No data available',
  className = '',
  ...props
}) => {
  return (
    <div className={`overflow-x-auto rounded-2xl border border-neutral-200 ${className}`} {...props}>
      <table className="w-full">
        <thead className="bg-neutral-50 border-b border-neutral-200">
          <tr>
            {headers.map((header, index) => (
              <th
                key={index}
                className="px-6 py-4 text-left text-sm font-semibold text-neutral-700 uppercase tracking-wider"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-neutral-200">
          {data.length > 0 ? (
            data.map((item, index) => renderRow(item, index))
          ) : (
            <tr>
              <td
                colSpan={headers.length}
                className="px-6 py-12 text-center text-neutral-500"
              >
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export default Table
