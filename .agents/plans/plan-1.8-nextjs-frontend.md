# Feature: Next.js Frontend Foundation (Plan 1.8)

## Feature Description

Create the foundational Next.js frontend structure for Badgers MVP, implementing project list and creation pages with Tailwind CSS styling and API client configuration. This establishes the base architecture for the user interface, enabling users to view and create projects through a modern, responsive web application.

## User Story

As a user
I want to view my projects and create new ones through a web interface
So that I can organize my AI task execution workflows in dedicated workspaces

## Problem Statement

The Badgers MVP currently has no frontend interface. Users need a web application to:
- View all their projects in a list
- Create new projects with names and descriptions
- Navigate to project details
- Access a clean, modern UI built with Next.js and Tailwind CSS

## Solution Statement

Build a Next.js 14+ frontend with App Router, implementing:
1. API client with TypeScript types for backend communication
2. TanStack Query setup for server state management
3. Project list page displaying all projects
4. Project creation form with validation
5. Reusable UI components following Tailwind best practices
6. Responsive layout with proper routing

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: Frontend (Next.js application)
**Dependencies**: Next.js 14+, React 18, TanStack Query, Tailwind CSS, Zod

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**Backend API Reference:**
- Backend API will be at `http://localhost:8000/api`
- Projects endpoint: `GET /api/projects`, `POST /api/projects`
- Expected schema: `{ id: uuid, name: string, description: string, created_at: datetime }`

**Existing Frontend Files:**
- `frontend/package.json` - Dependencies already configured
- `frontend/tailwind.config.ts` - Tailwind configuration exists
- `frontend/tsconfig.json` - TypeScript configuration exists
- `frontend/next.config.js` - Next.js configuration exists

### New Files to Create

**Core Infrastructure:**
- `frontend/src/lib/api.ts` - API client with fetch wrapper
- `frontend/src/lib/types.ts` - TypeScript types for API responses
- `frontend/src/lib/query-client.ts` - TanStack Query configuration

**App Router Pages:**
- `frontend/src/app/layout.tsx` - Root layout with providers
- `frontend/src/app/page.tsx` - Home page (redirect to projects)
- `frontend/src/app/projects/page.tsx` - Projects list page
- `frontend/src/app/globals.css` - Global styles with Tailwind directives

**Feature Modules:**
- `frontend/src/features/projects/components/ProjectCard.tsx` - Project card component
- `frontend/src/features/projects/components/ProjectList.tsx` - Projects list container
- `frontend/src/features/projects/components/CreateProjectForm.tsx` - Project creation form
- `frontend/src/features/projects/hooks/useProjects.ts` - Projects query hook
- `frontend/src/features/projects/hooks/useCreateProject.ts` - Create project mutation hook
- `frontend/src/features/projects/api/projects.ts` - Projects API functions

**Shared Components:**
- `frontend/src/components/ui/Button.tsx` - Reusable button component
- `frontend/src/components/ui/Card.tsx` - Reusable card component
- `frontend/src/components/ui/Input.tsx` - Reusable input component
- `frontend/src/components/layout/Header.tsx` - App header
- `frontend/src/components/layout/Container.tsx` - Content container

### Relevant Documentation

- [Next.js 14 App Router](https://nextjs.org/docs/app)
  - Specific section: App Router fundamentals
  - Why: Required for understanding file-based routing and layouts

- [TanStack Query v5](https://tanstack.com/query/latest/docs/framework/react/overview)
  - Specific section: Quick Start, Queries, Mutations
  - Why: Server state management for API calls

- [Tailwind CSS](https://tailwindcss.com/docs)
  - Specific section: Utility-first fundamentals
  - Why: Styling approach for all components

- [Zod](https://zod.dev/)
  - Specific section: Basic usage
  - Why: Form validation and type safety

### Patterns to Follow

**Naming Conventions:**
- Components: PascalCase (e.g., `ProjectCard.tsx`)
- Hooks: camelCase with `use` prefix (e.g., `useProjects.ts`)
- API functions: camelCase (e.g., `fetchProjects`)
- Types: PascalCase (e.g., `Project`, `CreateProjectInput`)

**File Organization:**
```
features/
  projects/
    components/     # Feature-specific components
    hooks/          # Feature-specific hooks
    api/            # Feature-specific API calls
    types.ts        # Feature-specific types
```

**API Client Pattern:**
```typescript
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`API error: ${response.statusText}`);
  return response.json();
}
```

**TanStack Query Pattern:**
```typescript
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });
}
```

**Component Pattern:**
```typescript
interface Props {
  // Explicit props, no spreading
}

export function Component({ prop1, prop2 }: Props) {
  // Implementation
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation Setup

Set up core infrastructure including API client, TypeScript types, and TanStack Query configuration.

**Tasks:**
- Configure API client with base URL and error handling
- Define TypeScript types for Project entity
- Set up TanStack Query client with default options
- Create root layout with query provider

### Phase 2: UI Components

Build reusable UI components following Tailwind best practices.

**Tasks:**
- Create Button component with variants (primary, secondary)
- Create Card component for content containers
- Create Input component for form fields
- Create Header component for app navigation
- Create Container component for page layout

### Phase 3: Projects Feature

Implement projects list and creation functionality.

**Tasks:**
- Create projects API functions (fetch, create)
- Create useProjects hook for fetching projects
- Create useCreateProject hook for creating projects
- Build ProjectCard component to display project info
- Build ProjectList component to render project grid
- Build CreateProjectForm with validation

### Phase 4: Pages & Routing

Set up Next.js pages and routing structure.

**Tasks:**
- Create root layout with providers and global styles
- Create home page (redirect to /projects)
- Create projects list page
- Configure Tailwind in globals.css
- Test navigation and routing

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE `frontend/src/lib/types.ts`

- **IMPLEMENT**: TypeScript types for API entities
- **PATTERN**: Use interface for object types, type for unions
- **IMPORTS**: None required
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface CreateProjectInput {
  name: string;
  description: string;
}

export interface ApiError {
  detail: string;
}
```

---

### Task 2: CREATE `frontend/src/lib/api.ts`

- **IMPLEMENT**: API client with fetch wrapper and error handling
- **PATTERN**: Generic request function with TypeScript generics
- **IMPORTS**: `ApiError` from `./types`
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { ApiError } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export class ApiClientError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiClientError';
  }
}

export async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: response.statusText
    }));
    throw new ApiClientError(response.status, error.detail);
  }

  if (response.status === 204) return null as T;
  return response.json();
}
```

---

### Task 3: CREATE `frontend/src/lib/query-client.ts`

- **IMPLEMENT**: TanStack Query client configuration
- **PATTERN**: Singleton QueryClient with default options
- **IMPORTS**: `QueryClient` from `@tanstack/react-query`
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

---

### Task 4: CREATE `frontend/src/app/globals.css`

- **IMPLEMENT**: Global styles with Tailwind directives
- **PATTERN**: Tailwind base, components, utilities
- **IMPORTS**: None
- **VALIDATE**: File exists and contains Tailwind directives

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-50 text-gray-900;
  }
}
```

---

### Task 5: CREATE `frontend/src/components/ui/Button.tsx`

- **IMPLEMENT**: Reusable button component with variants
- **PATTERN**: Variant-based styling with Tailwind
- **IMPORTS**: React
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

export function Button({
  variant = 'primary',
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

### Task 6: CREATE `frontend/src/components/ui/Card.tsx`

- **IMPLEMENT**: Reusable card container component
- **PATTERN**: Simple wrapper with Tailwind styling
- **IMPORTS**: React
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {children}
    </div>
  );
}
```

---

### Task 7: CREATE `frontend/src/components/ui/Input.tsx`

- **IMPLEMENT**: Reusable input component with error state
- **PATTERN**: Controlled input with error styling
- **IMPORTS**: React
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label className="text-sm font-medium text-gray-700">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            error ? 'border-red-500' : 'border-gray-300'
          } ${className}`}
          {...props}
        />
        {error && <span className="text-sm text-red-500">{error}</span>}
      </div>
    );
  }
);

Input.displayName = 'Input';
```

---

### Task 8: CREATE `frontend/src/components/layout/Header.tsx`

- **IMPLEMENT**: App header with navigation
- **PATTERN**: Fixed header with logo and nav links
- **IMPORTS**: Next.js Link
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import Link from 'next/link';

export function Header() {
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="text-xl font-bold text-gray-900">
            Badgers MVP
          </Link>
          <nav className="flex gap-6">
            <Link
              href="/projects"
              className="text-gray-600 hover:text-gray-900"
            >
              Projects
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
```

---

### Task 9: CREATE `frontend/src/components/layout/Container.tsx`

- **IMPLEMENT**: Content container with max-width
- **PATTERN**: Centered container with responsive padding
- **IMPORTS**: React
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
interface ContainerProps {
  children: React.ReactNode;
}

export function Container({ children }: ContainerProps) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {children}
    </div>
  );
}
```

---

### Task 10: CREATE `frontend/src/features/projects/api/projects.ts`

- **IMPLEMENT**: Projects API functions
- **PATTERN**: Async functions returning typed promises
- **IMPORTS**: `request` from `@/lib/api`, types from `@/lib/types`
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { request } from '@/lib/api';
import { Project, CreateProjectInput } from '@/lib/types';

export async function fetchProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

export async function createProject(data: CreateProjectInput): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
```

---

### Task 11: CREATE `frontend/src/features/projects/hooks/useProjects.ts`

- **IMPLEMENT**: Query hook for fetching projects
- **PATTERN**: TanStack Query useQuery wrapper
- **IMPORTS**: `useQuery` from `@tanstack/react-query`, `fetchProjects` from API
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { useQuery } from '@tanstack/react-query';
import { fetchProjects } from '../api/projects';

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });
}
```

---

### Task 12: CREATE `frontend/src/features/projects/hooks/useCreateProject.ts`

- **IMPLEMENT**: Mutation hook for creating projects
- **PATTERN**: TanStack Query useMutation with cache invalidation
- **IMPORTS**: `useMutation`, `useQueryClient` from `@tanstack/react-query`, `createProject` from API
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProject } from '../api/projects';

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
```

---

### Task 13: CREATE `frontend/src/features/projects/components/ProjectCard.tsx`

- **IMPLEMENT**: Project card component displaying project info
- **PATTERN**: Card wrapper with project details
- **IMPORTS**: `Card` from `@/components/ui/Card`, `Project` type, Next.js Link
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { Card } from '@/components/ui/Card';
import { Project } from '@/lib/types';
import Link from 'next/link';

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {project.name}
        </h3>
        <p className="text-gray-600 text-sm mb-4">
          {project.description || 'No description'}
        </p>
        <p className="text-xs text-gray-400">
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </Card>
    </Link>
  );
}
```

---

### Task 14: CREATE `frontend/src/features/projects/components/ProjectList.tsx`

- **IMPLEMENT**: Projects list container with loading and error states
- **PATTERN**: Grid layout with conditional rendering
- **IMPORTS**: `useProjects` hook, `ProjectCard` component
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { useProjects } from '../hooks/useProjects';
import { ProjectCard } from './ProjectCard';

export function ProjectList() {
  const { data: projects, isLoading, error } = useProjects();

  if (isLoading) {
    return <div className="text-center py-12">Loading projects...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        Failed to load projects: {error.message}
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No projects yet. Create your first project to get started.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
```

---

### Task 15: CREATE `frontend/src/features/projects/components/CreateProjectForm.tsx`

- **IMPLEMENT**: Project creation form with validation
- **PATTERN**: Controlled form with useState and validation
- **IMPORTS**: `useState` from React, `useCreateProject` hook, UI components
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
'use client';

import { useState, FormEvent } from 'react';
import { useCreateProject } from '../hooks/useCreateProject';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';

export function CreateProjectForm() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});

  const { mutate: createProject, isPending } = useCreateProject();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    const newErrors: typeof errors = {};
    if (!name.trim()) newErrors.name = 'Name is required';
    if (name.length > 100) newErrors.name = 'Name must be less than 100 characters';
    if (description.length > 500) newErrors.description = 'Description must be less than 500 characters';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    createProject(
      { name: name.trim(), description: description.trim() },
      {
        onSuccess: () => {
          setName('');
          setDescription('');
          setErrors({});
        },
      }
    );
  };

  return (
    <Card>
      <h2 className="text-xl font-semibold mb-4">Create New Project</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Project Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={errors.name}
          placeholder="My Project"
          disabled={isPending}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Project description..."
            disabled={isPending}
            className={`px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.description ? 'border-red-500' : 'border-gray-300'
            }`}
            rows={3}
          />
          {errors.description && (
            <span className="text-sm text-red-500">{errors.description}</span>
          )}
        </div>
        <Button type="submit" disabled={isPending}>
          {isPending ? 'Creating...' : 'Create Project'}
        </Button>
      </form>
    </Card>
  );
}
```

---

### Task 16: CREATE `frontend/src/app/layout.tsx`

- **IMPLEMENT**: Root layout with providers and metadata
- **PATTERN**: Next.js App Router layout with QueryClientProvider
- **IMPORTS**: QueryClientProvider, queryClient, Header, React
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import type { Metadata } from 'next';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';
import { Header } from '@/components/layout/Header';
import './globals.css';

export const metadata: Metadata = {
  title: 'Badgers MVP',
  description: 'AI-powered task execution platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryClientProvider client={queryClient}>
          <Header />
          <main className="min-h-screen">{children}</main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
```

---

### Task 17: CREATE `frontend/src/app/page.tsx`

- **IMPLEMENT**: Home page with redirect to projects
- **PATTERN**: Next.js redirect
- **IMPORTS**: Next.js redirect
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/projects');
}
```

---

### Task 18: CREATE `frontend/src/app/projects/page.tsx`

- **IMPLEMENT**: Projects list page
- **PATTERN**: Client component with feature components
- **IMPORTS**: Container, ProjectList, CreateProjectForm
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

```typescript
'use client';

import { Container } from '@/components/layout/Container';
import { ProjectList } from '@/features/projects/components/ProjectList';
import { CreateProjectForm } from '@/features/projects/components/CreateProjectForm';

export default function ProjectsPage() {
  return (
    <Container>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Projects</h1>
          <p className="text-gray-600">
            Manage your AI task execution workspaces
          </p>
        </div>

        <CreateProjectForm />

        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            Your Projects
          </h2>
          <ProjectList />
        </div>
      </div>
    </Container>
  );
}
```

---

## TESTING STRATEGY

### Manual Testing

Since this is foundational UI work, focus on manual testing in the browser.

**Test Scenarios:**
1. Navigate to `http://localhost:3000` - should redirect to `/projects`
2. Projects page loads without errors
3. Create project form accepts valid input
4. Create project form shows validation errors for invalid input
5. After creating project, it appears in the list
6. Project cards display correct information
7. Clicking project card navigates to project detail (will 404 for now, expected)
8. Responsive layout works on mobile/tablet/desktop

### Type Safety

All TypeScript compilation must pass with zero errors.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Install Dependencies

```bash
cd frontend && npm install
```

**Expected**: All dependencies installed successfully

---

### Level 2: TypeScript Compilation

```bash
cd frontend && npx tsc --noEmit
```

**Expected**: No TypeScript errors

---

### Level 3: Next.js Build

```bash
cd frontend && npm run build
```

**Expected**: Build completes successfully with no errors

---

### Level 4: Development Server

```bash
cd frontend && npm run dev
```

**Expected**: Server starts on http://localhost:3000

---

### Level 5: Manual Browser Testing

1. Open http://localhost:3000
2. Verify redirect to /projects
3. Verify page renders without console errors
4. Test project creation form
5. Verify responsive layout

**Expected**: All UI elements render correctly, no console errors

---

## ACCEPTANCE CRITERIA

- [ ] All TypeScript files compile without errors
- [ ] Next.js build completes successfully
- [ ] Development server starts without errors
- [ ] Home page redirects to /projects
- [ ] Projects page renders with header and layout
- [ ] Create project form validates input correctly
- [ ] Create project form submits data to API
- [ ] Projects list displays fetched projects
- [ ] Project cards show name, description, and date
- [ ] Responsive layout works on mobile and desktop
- [ ] No console errors in browser
- [ ] Tailwind styles applied correctly
- [ ] TanStack Query manages server state

---

## COMPLETION CHECKLIST

- [ ] All 18 tasks completed in order
- [ ] TypeScript compilation passes
- [ ] Next.js build succeeds
- [ ] Manual browser testing completed
- [ ] All acceptance criteria met
- [ ] No linting errors
- [ ] Code follows project conventions

---

## NOTES

**Important Considerations:**

1. **API Integration**: This plan assumes backend API is running at `http://localhost:8000/api`. If backend is not ready, API calls will fail. This is expected for frontend-only development.

2. **Path Aliases**: Uses `@/` alias for imports. Ensure `tsconfig.json` has:
   ```json
   {
     "compilerOptions": {
       "paths": {
         "@/*": ["./src/*"]
       }
     }
   }
   ```

3. **Client Components**: Components using hooks must have `'use client'` directive at the top.

4. **QueryClientProvider**: Must be in client component. Layout.tsx needs `'use client'` or wrap children in separate client component.

5. **Environment Variables**: Create `.env.local` if API URL differs:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

**Design Decisions:**

- **Feature-based structure**: Projects feature is self-contained in `features/projects/`
- **Minimal dependencies**: Uses only essential libraries already in package.json
- **No form library**: Simple useState for form state (can add react-hook-form later)
- **No UI library**: Custom components with Tailwind (can add shadcn/ui later)
- **Optimistic updates**: Not implemented in MVP (can add later)

**Future Enhancements:**

- Add react-hook-form + Zod for complex forms
- Add shadcn/ui components
- Add loading skeletons
- Add toast notifications
- Add error boundaries
- Add optimistic updates
- Add project detail page
- Add project edit/delete

---

## CONFIDENCE SCORE

**8/10** - High confidence for one-pass implementation success

**Reasoning:**
- Clear, atomic tasks with validation steps
- All dependencies already configured
- Patterns well-documented with code examples
- TypeScript provides compile-time safety
- Manual testing is straightforward

**Potential Risks:**
- QueryClientProvider in server component (needs 'use client')
- Path alias configuration might need adjustment
- API integration depends on backend availability

