# Dispute Resolution Web Frontend

A modern, dark-mode enabled Next.js frontend for the dispute resolution chat application, built with ShadCN UI components and Tailwind CSS.

## Features

- ✨ **Dark Mode by Default** - Clean, professional dark theme with light mode support
- 💬 **Interactive Chat Interface** - Step-by-step dispute resolution workflow  
- 🎨 **ShadCN UI Components** - Beautiful, accessible, and customizable components
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- ⚡ **Fast Performance** - Next.js 14 with App Router and Server Components
- 🔄 **Real-time Updates** - Live chat interface with loading states and animations
- 🎯 **TypeScript** - Full type safety and IntelliSense support

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + ShadCN UI
- **Icons**: Lucide React
- **Theme**: Next-themes for dark/light mode
- **State Management**: React Hooks (minimal external state)

## Getting Started

### Prerequisites

- Node.js 18.0 or later
- npm 8.0 or later (or pnpm/yarn)

### Installation

```bash
# Navigate to the web directory
cd web

# Install dependencies
npm install
# or
pnpm install
# or  
yarn install
```

### Development Server

```bash
# Start the development server
npm run dev
# or
pnpm dev
# or
yarn dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Build for Production

```bash
# Build the application
npm run build
npm run start

# or
pnpm build
pnpm start
```

## Project Structure

```
web/
├── app/                    # Next.js App Router pages
│   ├── globals.css        # Global styles and CSS variables
│   ├── layout.tsx         # Root layout with theme provider
│   └── page.tsx           # Home page with chat interface
├── components/            # React components
│   ├── ui/               # ShadCN UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── table.tsx
│   │   └── badge.tsx
│   ├── ChatWindow.tsx    # Main chat interface
│   ├── CardItem.tsx      # Credit card selection component
│   ├── TransactionTable.tsx # Transaction list component
│   └── theme-provider.tsx   # Dark/light mode provider
├── lib/                  # Utility functions and API client
│   ├── utils.ts         # Common utilities and formatters
│   └── api-client.ts    # FastAPI backend client
└── package.json         # Dependencies and scripts
```

## Configuration

### Environment Variables

Create a `.env.local` file in the web directory:

```bash
# Fast MCP API endpoint
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Environment identifier
NEXT_PUBLIC_ENV=development
```

### API Integration

The frontend communicates with the FastAPI backend through the API client (`lib/api-client.ts`):

- **Customer Verification**: `POST /verify/customer`
- **Card Verification**: `POST /verify/card`
- **Transaction Verification**: `POST /verify/txn`
- **Case Status**: `POST /case/status`

## Components Overview

### ChatWindow
The main chat interface that orchestrates the dispute resolution workflow:
- Handles customer ID input
- Displays card selection interface
- Shows transaction table
- Processes dispute results
- Manages chat history and loading states

### CardItem
Displays individual credit cards with:
- Card type badges (Visa, Mastercard, etc.)
- Transaction count indicators
- Click-to-select functionality
- Hover animations

### TransactionTable
Interactive table showing:
- Transaction dates and amounts
- Merchant information
- Description text
- Dispute action buttons
- Responsive design for mobile

## Styling

### Dark Mode Implementation
- Uses `next-themes` for seamless theme switching
- CSS custom properties for color tokens
- Tailwind CSS classes with dark: prefixes
- Automatic system theme detection

### Design System
- **Colors**: Semantic color tokens (primary, secondary, muted, etc.)
- **Typography**: Inter font with consistent sizing scale
- **Spacing**: Tailwind spacing system (4px base)
- **Animations**: Smooth transitions and micro-interactions
- **Shadows**: Subtle elevation system

## Development Guidelines

### Component Best Practices
- Use `"use client"` directive for interactive components
- Implement proper TypeScript interfaces
- Include loading and error states
- Add accessibility attributes (ARIA labels, etc.)
- Follow React Server Component patterns where possible

### Code Organization
- Keep components small and focused
- Extract business logic to custom hooks
- Use consistent naming conventions
- Add JSDoc comments for complex functions

### Performance Optimization
- Implement proper loading states
- Use React.memo for expensive components
- Optimize images and assets
- Minimize bundle size with tree shaking

## API Integration Examples

```typescript
// Verify customer
const response = await apiClient.verifyCustomer("CUST_12345")

// Select card and get transactions  
const cardResponse = await apiClient.verifyCard("CUST_12345", "CARD_67890")

// Process dispute
const disputeResponse = await apiClient.verifyTransaction(
  "CUST_12345", 
  "CARD_67890", 
  "TXN_ABC123"
)
```

## Browser Support

- Chrome 90+ ✅
- Firefox 88+ ✅  
- Safari 14+ ✅
- Edge 90+ ✅

## Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checks
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure FastAPI server is running on port 8000
   - Check CORS configuration in backend
   - Verify `NEXT_PUBLIC_API_URL` environment variable

2. **Dark Mode Not Working**
   - Check if `next-themes` is properly installed
   - Verify ThemeProvider wrapper in layout.tsx
   - Ensure CSS variables are defined in globals.css

3. **Components Not Rendering**
   - Verify all ShadCN UI dependencies are installed
   - Check TypeScript errors in terminal
   - Ensure proper import paths

### Performance Tips

- Use Next.js Image component for optimized images
- Implement proper error boundaries
- Add loading skeletons for better UX
- Consider implementing service workers for offline support

## License

Part of the Dispute Resolution Chat Application - Built with ❤️ by GitHub Copilot