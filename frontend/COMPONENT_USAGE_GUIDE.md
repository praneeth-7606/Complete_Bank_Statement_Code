# Component Usage Guide - Quick Reference

## Import Components
```jsx
import { Button, Card, Badge, Input, Skeleton, EmptyState, Modal, Table } from '../components/ui'
```

## Button Component

### Basic Usage
```jsx
<Button variant="primary" size="md">
  Click Me
</Button>
```

### With Icon
```jsx
<Button variant="primary" icon={Upload} iconPosition="left">
  Upload File
</Button>
```

### Loading State
```jsx
<Button variant="primary" loading={isLoading}>
  {isLoading ? 'Processing...' : 'Submit'}
</Button>
```

### Full Width
```jsx
<Button variant="primary" fullWidth>
  Full Width Button
</Button>
```

### All Variants
```jsx
<Button variant="primary">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="success">Success</Button>
<Button variant="danger">Danger</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="ai">AI Feature</Button>
```

## Card Component

### Basic Card
```jsx
<Card variant="default" padding="md">
  <h3>Card Title</h3>
  <p>Card content goes here</p>
</Card>
```

### Elevated Card
```jsx
<Card variant="elevated" padding="lg">
  <h3>Elevated Card</h3>
</Card>
```

### Clickable Card
```jsx
<Card variant="default" hover clickable onClick={handleClick}>
  <h3>Click Me</h3>
</Card>
```

### Glass Effect
```jsx
<Card variant="glass" padding="lg">
  <h3>Glassmorphism</h3>
</Card>
```

## Badge Component

### Basic Badge
```jsx
<Badge variant="success">Active</Badge>
```

### With Dot Indicator
```jsx
<Badge variant="success" dot>
  Online
</Badge>
```

### All Variants
```jsx
<Badge variant="default">Default</Badge>
<Badge variant="primary">Primary</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="danger">Danger</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="ai">AI</Badge>
```

## Input Component

### Basic Input
```jsx
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  fullWidth
/>
```

### With Icon
```jsx
<Input
  label="Search"
  icon={Search}
  iconPosition="left"
  placeholder="Search..."
  fullWidth
/>
```

### With Error
```jsx
<Input
  label="Password"
  type="password"
  error="Password must be at least 8 characters"
  fullWidth
/>
```

### With Helper Text
```jsx
<Input
  label="Username"
  helperText="Choose a unique username"
  fullWidth
/>
```

## Skeleton Component

### Text Skeleton
```jsx
<Skeleton variant="text" />
```

### Card Skeleton
```jsx
<Skeleton variant="card" />
```

### Multiple Skeletons
```jsx
<Skeleton variant="table-row" count={5} />
```

### All Variants
```jsx
<Skeleton variant="text" />
<Skeleton variant="title" />
<Skeleton variant="card" />
<Skeleton variant="circle" className="w-12 h-12" />
<Skeleton variant="rectangle" className="w-full h-32" />
<Skeleton variant="stat-card" />
<Skeleton variant="table-row" />
<Skeleton variant="chart" />
```

## EmptyState Component

### Basic Empty State
```jsx
<EmptyState
  icon={FileText}
  title="No transactions yet"
  description="Upload a statement to get started"
/>
```

### With Action Button
```jsx
<EmptyState
  icon={Upload}
  title="No statements uploaded"
  description="Upload your first bank statement to begin"
  action={handleUpload}
  actionLabel="Upload Statement"
/>
```

## Modal Component

### Basic Modal
```jsx
const [isOpen, setIsOpen] = useState(false)

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Confirm Action"
>
  <p>Are you sure you want to proceed?</p>
  <div className="flex gap-4 mt-6">
    <Button variant="danger" onClick={handleConfirm}>
      Confirm
    </Button>
    <Button variant="ghost" onClick={() => setIsOpen(false)}>
      Cancel
    </Button>
  </div>
</Modal>
```

### Different Sizes
```jsx
<Modal size="sm">Small Modal</Modal>
<Modal size="md">Medium Modal</Modal>
<Modal size="lg">Large Modal</Modal>
<Modal size="xl">Extra Large Modal</Modal>
<Modal size="full">Full Width Modal</Modal>
```

### Without Close Button
```jsx
<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  showCloseButton={false}
>
  Content
</Modal>
```

## Table Component

### Basic Table
```jsx
<Table
  headers={['Name', 'Email', 'Status']}
  data={users}
  renderRow={(user, index) => (
    <tr key={index}>
      <td className="px-6 py-4">{user.name}</td>
      <td className="px-6 py-4">{user.email}</td>
      <td className="px-6 py-4">
        <Badge variant="success">{user.status}</Badge>
      </td>
    </tr>
  )}
  emptyMessage="No users found"
/>
```

## Design Tokens

### Using Colors
```jsx
import { designTokens } from '../lib/design-tokens'

const primaryColor = designTokens.colors.primary.main
const successColor = designTokens.colors.semantic.success
```

### Using Gradients
```jsx
import { gradients } from '../lib/design-tokens'

<div style={{ background: gradients.primary }}>
  Gradient Background
</div>
```

## Performance Utilities

### Debounce
```jsx
import { useDebounce } from '../utils/performance'

const [searchTerm, setSearchTerm] = useState('')
const debouncedSearch = useDebounce(searchTerm, 500)

useEffect(() => {
  // API call with debounced value
  fetchResults(debouncedSearch)
}, [debouncedSearch])
```

### Memoized Callback
```jsx
import { useStableCallback } from '../utils/performance'

const handleClick = useStableCallback(() => {
  // Expensive operation
}, [dependency])
```

### Format Numbers
```jsx
import { formatNumber } from '../utils/performance'

const formatted = formatNumber(1234567) // ₹1.23Cr
const formatted2 = formatNumber(45000) // ₹45.00K
```

## Common Patterns

### Loading State
```jsx
{loading ? (
  <Skeleton variant="card" count={3} />
) : (
  <Card>Content</Card>
)}
```

### Empty State
```jsx
{data.length === 0 ? (
  <EmptyState
    icon={FileText}
    title="No data"
    description="Get started by adding some data"
    action={handleAdd}
    actionLabel="Add Data"
  />
) : (
  <div>Data list</div>
)}
```

### Form with Validation
```jsx
<form onSubmit={handleSubmit}>
  <Input
    label="Email"
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    error={errors.email}
    fullWidth
    required
  />
  
  <Input
    label="Password"
    type="password"
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    error={errors.password}
    fullWidth
    required
  />
  
  <Button
    type="submit"
    variant="primary"
    loading={loading}
    fullWidth
  >
    Submit
  </Button>
</form>
```

### Confirmation Modal
```jsx
const [showConfirm, setShowConfirm] = useState(false)

<Button variant="danger" onClick={() => setShowConfirm(true)}>
  Delete
</Button>

<Modal
  isOpen={showConfirm}
  onClose={() => setShowConfirm(false)}
  title="Confirm Deletion"
  size="sm"
>
  <p>Are you sure you want to delete this item?</p>
  <div className="flex gap-4 mt-6">
    <Button
      variant="danger"
      onClick={handleDelete}
      fullWidth
    >
      Delete
    </Button>
    <Button
      variant="ghost"
      onClick={() => setShowConfirm(false)}
      fullWidth
    >
      Cancel
    </Button>
  </div>
</Modal>
```

## Best Practices

1. **Always use unified components** instead of custom styles
2. **Use design tokens** for colors and spacing
3. **Add loading states** with Skeleton components
4. **Add empty states** for better UX
5. **Use performance utilities** for expensive operations
6. **Keep components memoized** when possible
7. **Use consistent variants** across the app
8. **Add proper error handling** with error states
9. **Make components accessible** with ARIA labels
10. **Test on multiple screen sizes**

## Troubleshooting

### Component not styling correctly?
- Check if you're importing from `../components/ui`
- Verify Tailwind classes are being applied
- Check browser console for errors

### Performance issues?
- Use React.memo for expensive components
- Use useCallback for event handlers
- Use useMemo for expensive calculations
- Check for unnecessary re-renders

### Styling conflicts?
- Unified components should override old styles
- Remove custom inline styles
- Use className prop for additional styles

## Need Help?

Check these files:
- `/components/ui/` - Component implementations
- `/lib/design-tokens.js` - Design system constants
- `/utils/performance.js` - Performance utilities
- `tailwind.config.js` - Theme configuration
- `PHASE_2_COMPLETE.md` - Complete integration guide
