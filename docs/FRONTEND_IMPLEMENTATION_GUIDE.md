# Frontend Implementation Guide - InsightDocs

**Complete guide for building the React frontend with Vite, TypeScript, Tailwind CSS, and Shadcn UI**

---

## 📋 Table of Contents

1. [Tech Stack Overview](#tech-stack-overview)
2. [Project Structure](#project-structure)
3. [Setup Steps](#setup-steps)
4. [Design System](#design-system)
5. [Component Architecture](#component-architecture)
6. [Pages to Build](#pages-to-build)
7. [API Integration](#api-integration)
8. [State Management](#state-management)
9. [Best Practices](#best-practices)
10. [Implementation Order](#implementation-order)

---

## 🛠️ Tech Stack Overview

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.x | UI library |
| **Vite** | 5.x | Build tool & dev server |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.x | Utility-first CSS |
| **Shadcn UI** | Latest | Component library |
| **React Router** | 6.x | Client-side routing |
| **TanStack Query** | 5.x | Server state management |
| **Axios** | 1.x | HTTP client |
| **Zustand** | 4.x | Client state management |
| **Lucide React** | Latest | Icon library |

### Why This Stack?

✅ **Vite**: Lightning-fast dev server, instant HMR, optimized builds  
✅ **TypeScript**: Catch errors early, better IDE support  
✅ **Tailwind**: Rapid styling, consistent design system  
✅ **Shadcn UI**: Beautiful, accessible, customizable components  
✅ **TanStack Query**: Automatic caching, background refetching, optimistic updates  
✅ **Zustand**: Simple, minimal state management (for auth, UI state)  

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── components/           # Reusable components
│   │   ├── ui/              # Shadcn UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ... (more shadcn components)
│   │   ├── layout/          # Layout components
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── auth/            # Auth-specific components
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── documents/       # Document-related components
│   │   │   ├── DocumentCard.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   ├── DocumentUpload.tsx
│   │   │   └── DocumentViewer.tsx
│   │   ├── chat/            # Chat-related components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── SourceCitation.tsx
│   │   └── settings/        # Settings components
│   │       ├── ApiKeyForm.tsx
│   │       └── ProfileSettings.tsx
│   ├── pages/               # Page components
│   │   ├── Home.tsx
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── DocumentDetail.tsx
│   │   ├── Chat.tsx
│   │   └── Settings.tsx
│   ├── lib/                 # Utility functions
│   │   ├── api.ts           # Axios instance & API calls
│   │   ├── utils.ts         # Helper functions
│   │   └── validators.ts    # Form validation
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useDocuments.ts
│   │   ├── useChat.ts
│   │   └── useToast.ts
│   ├── store/               # Zustand stores
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   ├── types/               # TypeScript types
│   │   ├── api.ts
│   │   ├── document.ts
│   │   └── user.ts
│   ├── styles/              # Global styles
│   │   └── globals.css
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── vite-env.d.ts        # Vite types
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── components.json          # Shadcn UI config
└── .env.local               # Environment variables
```

---

## 🚀 Setup Steps

### Step 1: Initialize Vite Project

```bash
cd /home/harshil/insightdocs
rm -rf frontend  # Clean slate
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### Step 2: Install Dependencies

```bash
# Core dependencies
npm install react-router-dom @tanstack/react-query axios zustand

# Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Shadcn UI
npx shadcn-ui@latest init

# Additional utilities
npm install lucide-react clsx tailwind-merge
npm install @hookform/resolvers zod react-hook-form
npm install date-fns
npm install react-dropzone
```

### Step 3: Configure Tailwind CSS

**tailwind.config.js**:
```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

### Step 4: Configure Vite Proxy

**vite.config.ts**:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### Step 5: Setup TypeScript Paths

**tsconfig.json**:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### Step 6: Environment Variables

**.env.local**:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 🎨 Design System

### Color Palette

**Primary Colors** (Blue - Professional, Trust):
- `primary`: `hsl(221.2 83.2% 53.3%)` - Main brand color
- `primary-foreground`: `hsl(210 40% 98%)` - Text on primary

**Accent Colors**:
- `accent`: `hsl(210 40% 96.1%)` - Subtle highlights
- `accent-foreground`: `hsl(222.2 47.4% 11.2%)` - Text on accent

**Neutral Colors**:
- `background`: `hsl(0 0% 100%)` - Page background
- `foreground`: `hsl(222.2 84% 4.9%)` - Main text
- `muted`: `hsl(210 40% 96.1%)` - Disabled states
- `border`: `hsl(214.3 31.8% 91.4%)` - Borders

**Semantic Colors**:
- `destructive`: `hsl(0 84.2% 60.2%)` - Error, delete
- `success`: `hsl(142.1 76.2% 36.3%)` - Success states
- `warning`: `hsl(47.9 95.8% 53.1%)` - Warning states

### Typography

**Font Family**: Inter (Google Fonts)
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
```

**Font Sizes**:
- `text-xs`: 0.75rem (12px)
- `text-sm`: 0.875rem (14px)
- `text-base`: 1rem (16px)
- `text-lg`: 1.125rem (18px)
- `text-xl`: 1.25rem (20px)
- `text-2xl`: 1.5rem (24px)
- `text-3xl`: 1.875rem (30px)
- `text-4xl`: 2.25rem (36px)

### Spacing

Use Tailwind's default spacing scale (4px increments):
- `p-2`: 8px padding
- `p-4`: 16px padding
- `p-6`: 24px padding
- `p-8`: 32px padding

### Border Radius

- `rounded-sm`: 4px
- `rounded`: 6px
- `rounded-md`: 8px
- `rounded-lg`: 12px
- `rounded-xl`: 16px

### Shadows

- `shadow-sm`: Subtle
- `shadow`: Default
- `shadow-md`: Medium
- `shadow-lg`: Large
- `shadow-xl`: Extra large

---

## 🧩 Component Architecture

### Atomic Design Methodology

1. **Atoms**: Basic UI elements (Button, Input, Badge)
2. **Molecules**: Simple component groups (FormField, SearchBar)
3. **Organisms**: Complex components (Navbar, DocumentCard, ChatInterface)
4. **Templates**: Page layouts (AppLayout)
5. **Pages**: Full pages (Dashboard, Login)

### Key Components to Build

#### 1. Layout Components

**AppLayout.tsx** - Main layout wrapper:
```tsx
<div className="min-h-screen bg-background">
  <Navbar />
  <div className="flex">
    <Sidebar /> {/* Optional for dashboard */}
    <main className="flex-1 p-6">
      {children}
    </main>
  </div>
  <Footer />
</div>
```

**Navbar.tsx** - Top navigation:
- Logo
- Navigation links (Dashboard, Documents, Chat)
- User menu (Profile, Settings, Logout)
- Theme toggle (dark/light mode)

#### 2. Auth Components

**LoginForm.tsx** - Login form:
- Email input (validation)
- Password input (show/hide toggle)
- Remember me checkbox
- Submit button
- Link to register

**RegisterForm.tsx** - Registration form:
- Name input
- Email input (validation)
- Password input (strength indicator)
- Confirm password
- Submit button
- Link to login

**ProtectedRoute.tsx** - Route guard:
```tsx
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" />;
  return children;
};
```

#### 3. Document Components

**DocumentUpload.tsx** - Drag-and-drop uploader:
- Drag zone (react-dropzone)
- File type validation (23 formats)
- Size limit display
- Upload progress bar
- Preview before upload

**DocumentCard.tsx** - Document list item:
- Thumbnail/icon
- Filename
- File size, upload date
- Status badge (processing/completed)
- Actions (View, Chat, Delete)

**DocumentList.tsx** - Document grid/list:
- Search/filter bar
- Sort options (date, name, size)
- Grid/list view toggle
- Pagination
- Empty state

**DocumentViewer.tsx** - Document detail view:
- PDF viewer (or preview for other formats)
- Metadata panel
- Summary / quiz / mind map action buttons
- Citation-backed Q&A button
- Download button
- Chunk viewer with bbox highlighting

#### 4. Chat Components

**ChatInterface.tsx** - Main chat UI:
- Document selector dropdown
- Query history sidebar/panel
- Message history
- Input box
- Send button
- Streaming response indicator

**ChatMessage.tsx** - Single message:
- Avatar (user/AI)
- Message text (markdown rendering)
- Timestamp
- Source citations
- Copy button

**SourceCitation.tsx** - Citation card:
- Document name
- Page number
- Relevance score
- Preview text
- Click to view in document

**ChatInput.tsx** - Message input:
- Auto-resizing textarea
- Send button
- Character count
- Example prompts (on empty state)

#### 5. Settings Components

**ApiKeyForm.tsx** - BYOK settings:
- Current status indicator (using default/own key)
- Masked API key display
- Input field (with validation)
- Save button
- Delete button (with confirmation)
- Guide link to Google AI Studio

#### 6. Task Components

**TaskStatusCard.tsx** - Async job summary:
- Task type (upload, query, document processing)
- Status badge
- Progress bar
- Created time
- Link to task details

**TaskList.tsx** - Task feed:
- Recent uploads and query jobs
- Filter by status
- Auto-refresh while processing
- Empty state when no tasks exist

---

## 📄 Pages to Build

### 1. Home Page (`/`)

**Purpose**: Landing page for non-authenticated users

**Sections**:
- Hero section with CTA
- Feature highlights (BYOK, 23 formats, Ask Your PDF, citations)
- How it works (3-step process)
- Competitive advantages
- Footer with links

**Actions**: Login, Register buttons

---

### 2. Login Page (`/login`)

**Purpose**: User authentication

**Components**:
- LoginForm
- Link to register
- "Forgot password?" (future)

**Flow**:
1. User enters email + password
2. API call to `/auth/login` with form-encoded `username` + `password`
3. Store JWT token in Zustand + localStorage
4. Redirect to `/dashboard`

---

### 3. Register Page (`/register`)

**Purpose**: New user signup

**Components**:
- RegisterForm
- Link to login

**Flow**:
1. User enters name, email, password
2. API call to `/auth/register`
3. Auto-login after registration
4. Redirect to `/dashboard`

---

### 4. Dashboard Page (`/dashboard`) 🔒

**Purpose**: Main hub after login

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Navbar                                      │
├─────────────────────────────────────────────┤
│                                             │
│  📊 Stats Cards                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │ Docs │ │Chunks│ │Queries│ │ Size │      │
│  └──────┘ └──────┘ └──────┘ └──────┘      │
│                                             │
│  📤 Upload Zone (Drag & Drop)               │
│                                             │
│  📄 Recent Documents                        │
│  ┌─────────────────────────────────────┐   │
│  │ Document Grid/List                  │   │
│  │ - Search/Filter                     │   │
│  │ - Sort options                      │   │
│  │ - Pagination                        │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**Features**:
- Document upload (drag-and-drop)
- Document list (search, filter, sort)
- Quick stats
- Recent queries
- Task status overview for uploads and query/document processing

---

### 5. Document Detail Page (`/documents/:id`) 🔒

**Purpose**: View single document and interact

**Layout**:
```
┌─────────────────────────────────────────────┐
│ ← Back to Dashboard     [Actions Dropdown]  │
├─────────────────────────────────────────────┤
│                                             │
│  Document: sample.pdf                       │
│  📊 Status: Completed | Size: 2.5 MB        │
│                                             │
│  Tabs: [Preview] [Chat] [Metadata] [Chunks] │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │  Tab Content Area                   │   │
│  │  - Preview: PDF viewer              │   │
│  │  - Chat: RAG interface              │   │
│  │  - Metadata: File info              │   │
│  │  - Chunks: Text chunks with bbox    │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**Actions**:
- Summarize document
- Generate quiz
- Generate mind map
- Ask question with citations
- Download document
- Delete document
- Share (future)

---

### 6. Chat Page (`/chat`) 🔒

**Purpose**: RAG chat interface

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Select Document: [Dropdown]   [New Chat]    │
├─────────────────────────────────────────────┤
│                                             │
│  💬 Message History                         │
│  ┌─────────────────────────────────────┐   │
│  │ User: What is this document about?  │   │
│  │                                     │   │
│  │ AI: This document discusses...      │   │
│  │ Sources: [Page 1] [Page 3]          │   │
│  │                                     │   │
│  │ User: Tell me more about...         │   │
│  │                                     │   │
│  │ AI: [Streaming response...]         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ Type your message...           [Send]│   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**Features**:
- Document selector
- Real-time streaming responses
- Source citations with page numbers
- Message history
- Query history panel/sidebar from `/query/history`
- Copy responses
- Export chat (future)

---

### 7. Settings Page (`/settings`) 🔒

**Purpose**: User settings and BYOK management

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Settings                                    │
├─────────────────────────────────────────────┤
│                                             │
│  Tabs: [API Key] [Profile] [Preferences]   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │                                     │   │
│  │  🔑 API Key Management (BYOK)       │   │
│  │                                     │   │
│  │  Status: 🟢 Using your own key      │   │
│  │                                     │   │
│  │  Current Key: sk-***************    │   │
│  │                                     │   │
│  │  ┌──────────────────────────────┐  │   │
│  │  │ New API Key                  │  │   │
│  │  └──────────────────────────────┘  │   │
│  │                                     │   │
│  │  [Save] [Delete] [Test Connection]  │   │
│  │                                     │   │
│  │  📚 How to get an API key →         │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘
```

**Features**:
- BYOK API key input (encrypted storage)
- BYOK status fetched from `/users/me/byok-status`
- Live model health, fallback order, and active-model display
- Enable/disable BYOK toggle
- Profile editing (name, email)
- Theme preference (light/dark)
- Notification settings (future)

---

## 🔌 Backend API Surface (Current)

This is the exact backend surface the frontend should target now.

> Note: There is **no** `GET /users/me` profile endpoint yet. The login response already includes the user object, and BYOK state should be fetched separately from `/users/me/byok-status`.

| Area | Endpoints | Frontend usage |
|------|-----------|----------------|
| Authentication | `POST /auth/register`, `POST /auth/login` | Sign up and sign in |
| Documents | `POST /documents/upload`, `GET /documents/`, `GET /documents/{document_id}`, `DELETE /documents/{document_id}` | Dashboard + document detail |
| Document Intelligence | `POST /documents/{document_id}/summarize`, `POST /documents/{document_id}/quiz`, `POST /documents/{document_id}/mindmap` | Document actions and media |
| Query | `POST /query/`, `GET /query/history` | Chat page and query history |
| Tasks | `GET /tasks/`, `GET /tasks/{task_id}` | Upload/query job status |
| User Settings | `PUT /users/me/api-key`, `DELETE /users/me/api-key`, `PATCH /users/me/byok-settings`, `GET /users/me/byok-status` | BYOK settings panel |
| System | `GET /`, `GET /api/v1/health` | App bootstrap and diagnostics |

### Auth Contract Notes

- `POST /auth/register` accepts JSON: `{ name, email, password }`
- `POST /auth/login` uses OAuth2 form data:
  - `username` = email
  - `password` = password
- `POST /query/` accepts JSON: `{ query, top_k? }`
- Query responses include structured citations with `source_number`, `page_number`, `chunk_index`, and `bbox` so the UI can jump to the exact passage.

---

## 🔌 API Integration

### API Client Setup

**src/lib/api.ts**:
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (add auth token)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle errors)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### API Functions

**src/lib/api.ts** (continued):
```typescript
// Auth
export const login = (email: string, password: string) => {
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
};

export const register = (name: string, email: string, password: string) =>
  api.post('/auth/register', { name, email, password });

// Documents
export const getDocuments = () => api.get('/documents/');
export const getDocument = (id: string) => api.get(`/documents/${id}`);
export const uploadDocument = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/documents/upload', formData);
};
export const deleteDocument = (id: string) => api.delete(`/documents/${id}`);
export const summarizeDocument = (id: string) =>
  api.post(`/documents/${id}/summarize`);

export const generateQuiz = (id: string) =>
  api.post(`/documents/${id}/quiz`);

export const generateMindmap = (id: string) =>
  api.post(`/documents/${id}/mindmap`);

// Ask your PDF chat
export const sendQuery = (query: string, topK = 5, conversationId?: string) =>
  api.post('/query/', { query, top_k: topK, conversation_id: conversationId });

export const getQueryHistory = (skip = 0, limit = 100, conversationId?: string) =>
  api.get('/query/history', { params: { skip, limit, conversation_id: conversationId } });

// Tasks
export const getTasks = (skip = 0, limit = 100) =>
  api.get('/tasks/', { params: { skip, limit } });

export const getTaskStatus = (taskId: string) => api.get(`/tasks/${taskId}`);

// API Key (BYOK)
export const saveApiKey = (apiKey: string) =>
  api.put('/users/me/api-key', { api_key: apiKey });

export const deleteApiKey = () => api.delete('/users/me/api-key');

export const updateByokSettings = (enabled: boolean) =>
  api.patch('/users/me/byok-settings', { enabled });

export const getByokStatus = () => api.get('/users/me/byok-status');
```

---

## 🗂️ State Management

### Zustand Store for Auth

**src/store/authStore.ts**:
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => {
        localStorage.setItem('token', token);
        set({ user, token, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('token');
        set({ user: null, token: null, isAuthenticated: false });
      },
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    { name: 'auth-storage' }
  )
);
```

> BYOK state is separate from the login response. Fetch `/users/me/byok-status` in the Settings page when you need to show whether the user is using their own Gemini key.

### TanStack Query for Server State

**src/main.tsx**:
```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
```

### Custom Hooks

**src/hooks/useDocuments.ts**:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDocuments, uploadDocument, deleteDocument } from '@/lib/api';

export const useDocuments = () => {
  const queryClient = useQueryClient();

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: getDocuments,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  return {
    documents: documents?.data || [],
    isLoading,
    uploadDocument: uploadMutation.mutate,
    deleteDocument: deleteMutation.mutate,
  };
};
```

---

## ✅ Best Practices

### 1. Code Organization
- One component per file
- Group related components in folders
- Use barrel exports (index.ts)

### 2. TypeScript
- Define types in `src/types/`
- Avoid `any` type
- Use strict mode

### 3. Styling
- Use Tailwind utilities first
- Create custom classes only when necessary
- Follow mobile-first approach

### 4. Performance
- Lazy load routes with React.lazy()
- Memoize expensive computations
- Use TanStack Query for caching

### 5. Accessibility
- Use semantic HTML
- Add ARIA labels
- Ensure keyboard navigation
- Test with screen readers

### 6. Security
- Never store sensitive data in localStorage unencrypted
- Validate all user input
- Sanitize displayed content
- Use HTTPS in production

---

## 🎯 Implementation Order

### Phase 1: Foundation (Day 1)
1. ✅ Initialize Vite project
2. ✅ Install dependencies
3. ✅ Configure Tailwind + Shadcn UI
4. ✅ Setup API client
5. ✅ Create basic layout components

### Phase 2: Authentication (Day 1-2)
1. ✅ Create auth store (Zustand)
2. ✅ Build LoginForm component
3. ✅ Build RegisterForm component
4. ✅ Create ProtectedRoute component
5. ✅ Setup routing
6. ✅ Test auth flow

### Phase 3: Dashboard (Day 2-3)
1. ✅ Create Dashboard page
2. ✅ Build DocumentUpload component
3. ✅ Build DocumentCard component
4. ✅ Build DocumentList component
5. ✅ Implement search/filter
6. ✅ Test upload flow

### Phase 4: Ask Your PDF Interface (Day 3-4)
1. ✅ Create Chat page
2. ✅ Build ChatInterface component
3. ✅ Build ChatMessage component
4. ✅ Build ChatInput component
5. ✅ Implement streaming (optional)
6. ✅ Add source citations
7. ✅ Test RAG flow

### Phase 5: Settings (Day 4)
1. ✅ Create Settings page
2. ✅ Build ApiKeyForm component
3. ✅ Implement BYOK save/delete
4. ✅ Add validation
5. ✅ Test API key flow

### Phase 6: Polish (Day 5)
1. ✅ Add loading states
2. ✅ Add error handling
3. ✅ Add empty states
4. ✅ Improve responsiveness
5. ✅ Add animations
6. ✅ Test thoroughly

---

## 🔗 Useful Resources

- **Shadcn UI Docs**: https://ui.shadcn.com/
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **TanStack Query Docs**: https://tanstack.com/query/latest
- **React Router Docs**: https://reactrouter.com/
- **Vite Docs**: https://vitejs.dev/
- **TypeScript Handbook**: https://www.typescriptlang.org/docs/

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: Tailwind styles not applying  
**Fix**: Ensure `globals.css` is imported in `main.tsx`

**Issue**: API calls failing with CORS  
**Fix**: Check Vite proxy configuration in `vite.config.ts`

**Issue**: Shadcn components not found  
**Fix**: Run `npx shadcn-ui@latest add <component-name>`

**Issue**: TypeScript errors with path aliases  
**Fix**: Verify `tsconfig.json` has correct `baseUrl` and `paths`

---

## 📝 Summary

This guide provides a complete blueprint for building the InsightDocs frontend. Follow the implementation order, use the component structure, and integrate with the current backend API surface, including document intelligence, task tracking, and BYOK settings. The result will be a modern, performant, and beautiful React application! 🚀
