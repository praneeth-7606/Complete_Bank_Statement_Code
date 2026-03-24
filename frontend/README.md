# FinanceAI - Financial Statement Analyzer Frontend

A modern, AI-powered financial statement analysis application built with React, Vite, and Tailwind CSS.

## Features

- 📊 **Dashboard** - Overview of your financial health with key metrics
- 📤 **Upload** - Process single or multiple bank statement PDFs
- 📝 **Transactions** - View, search, and filter all transactions
- 💬 **AI Chat** - Ask questions about your finances in natural language
- 📈 **Analytics** - Visual insights with charts and AI-powered recommendations
- 🎯 **Corrections** - Teach the AI to improve categorization accuracy

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Router** - Navigation
- **Recharts** - Data visualization
- **Framer Motion** - Animations
- **Axios** - API communication
- **Lucide React** - Icon library

## Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Update `.env` with your API URL:
```
VITE_API_URL=http://localhost:8000
```

### Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The production build will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/        # Reusable components
│   │   └── Layout.jsx     # Main layout with sidebar
│   ├── pages/            # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Upload.jsx
│   │   ├── Transactions.jsx
│   │   ├── Chat.jsx
│   │   ├── Analytics.jsx
│   │   └── Corrections.jsx
│   ├── services/         # API services
│   │   └── api.js
│   ├── App.jsx           # Main app component
│   ├── main.jsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── package.json         # Dependencies
```

## Features Overview

### Dashboard
- Quick overview of financial metrics
- Recent transactions
- Quick action buttons
- Animated statistics cards

### Upload
- Drag-and-drop PDF upload
- Multiple file support
- Password protection for PDFs
- Real-time processing status
- Results visualization

### Transactions
- Searchable transaction list
- Filter by type (income/expense)
- Filter by category
- Export to CSV
- Responsive table design

### Chat
- AI-powered financial assistant
- Natural language queries
- Suggested questions
- Real-time responses
- Chat history

### Analytics
- Category breakdown pie chart
- Monthly income vs expenses bar chart
- Spending trend line chart
- AI-generated insights
- Detailed category table

### Corrections
- Teach the AI with keyword rules
- Category assignment
- Recent corrections history
- Example corrections

## API Integration

The frontend communicates with the backend API through the `api.js` service layer:

- `POST /process-statement/` - Single PDF processing
- `POST /process-multiple-statements/` - Batch PDF processing
- `POST /chat` - AI chat queries
- `POST /correct-transaction/` - Submit corrections

## Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:
```js
colors: {
  primary: {
    // Your custom colors
  }
}
```

### API URL
Update the API base URL in `.env`:
```
VITE_API_URL=your-api-url
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.
