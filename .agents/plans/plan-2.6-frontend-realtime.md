# Feature: Frontend Real-time Updates with WebSocket

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a WebSocket client in the frontend to display real-time task execution progress and tool calls. Users will see live updates as the AI agent executes tasks, including status changes, tool invocations, and step-by-step progress. This transforms the static task view into a dynamic, observable execution experience.

## User Story

As a user
I want to see real-time updates of task execution progress
So that I can monitor what the AI agent is doing and understand the workflow as it happens

## Problem Statement

Currently, the frontend lacks real-time visibility into task execution. Users cannot see:
- When a task starts running
- What tools the agent is calling (browser, file, python, web)
- Step-by-step progress through the execution loop
- When tasks complete or fail
- Error messages in real-time

This creates a "black box" experience where users submit tasks and wait without feedback.

## Solution Statement

Implement a WebSocket client that connects to the backend's `/api/runs/{run_id}/stream` endpoint. Create React hooks for managing WebSocket connections, event handling, and state updates. Build UI components to display task status, execution steps, tool calls, and progress indicators. Use TanStack Query for data synchronization and React's built-in state management for real-time event streams.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: Frontend (features/tasks, lib/websocket, components/ui)
**Dependencies**: Native WebSocket API (browser built-in), TanStack Query, React hooks

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/app/routers/runs.py` (lines 40-48) - Why: WebSocket endpoint implementation pattern
- `backend/app/services/event_broadcaster.py` (lines 29-40) - Why: Event structure and broadcasting pattern
- `frontend/src/features/projects/hooks/useProjects.ts` - Why: TanStack Query hook pattern to mirror
- `frontend/src/features/projects/components/CreateProjectForm.tsx` (lines 1-82) - Why: Form component pattern with state management
- `frontend/src/lib/api.ts` - Why: API client pattern and error handling
- `frontend/src/lib/types.ts` - Why: Type definition patterns
- `backend/app/schemas/task.py` (lines 33-44) - Why: TaskRunResponse schema for type definitions
- `frontend/src/components/ui/Card.tsx` - Why: UI component pattern to follow

### New Files to Create

- `frontend/src/lib/websocket.ts` - WebSocket client utility with reconnection logic
- `frontend/src/features/tasks/hooks/useTaskRunStream.ts` - React hook for WebSocket connection
- `frontend/src/features/tasks/types.ts` - TypeScript types for task events
- `frontend/src/features/tasks/components/TaskRunViewer.tsx` - Main component for displaying task execution
- `frontend/src/features/tasks/components/TaskStatusBadge.tsx` - Status indicator component
- `frontend/src/features/tasks/components/ToolCallItem.tsx` - Individual tool call display
- `frontend/src/features/tasks/components/ExecutionTimeline.tsx` - Timeline of execution steps

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
  - Specific section: WebSocket events (onopen, onmessage, onerror, onclose)
  - Why: Native browser WebSocket API reference
- [React useEffect Hook](https://react.dev/reference/react/useEffect)
  - Specific section: Cleanup functions
  - Why: Proper WebSocket connection lifecycle management
- [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview)
  - Specific section: Query invalidation
  - Why: Synchronizing WebSocket updates with cached data

### Patterns to Follow

**Naming Conventions:**
```typescript
// Hook naming: use{Feature}{Action}
export function useTaskRunStream(runId: string) { }

// Component naming: PascalCase with descriptive names
export function TaskRunViewer({ runId }: Props) { }

// Type naming: PascalCase with descriptive suffixes
export interface TaskRunEvent { }
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';
```

**Error Handling:**
```typescript
// Pattern from frontend/src/lib/api.ts
export class WebSocketError extends Error {
  constructor(public code: number, message: string) {
    super(message);
    this.name = 'WebSocketError';
  }
}
```

**React Hook Pattern:**
```typescript
// Pattern from frontend/src/features/projects/hooks/useProjects.ts
import { useQuery } from '@tanstack/react-query';

export function useTaskRunStream(runId: string) {
  // Hook implementation with proper cleanup
}
```

**Component Pattern:**
```typescript
// Pattern from frontend/src/features/projects/components/CreateProjectForm.tsx
'use client';

import { useState } from 'react';

export function TaskRunViewer({ runId }: Props) {
  const [state, setState] = useState<Type>(initialValue);
  // Component logic
}
```

**Styling Pattern:**
```typescript
// Pattern from frontend/src/components/ui/Card.tsx
// Use Tailwind CSS classes with template literals
className={`base-classes ${conditionalClasses}`}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create TypeScript types and WebSocket utility infrastructure.

**Tasks:**
- Define event types matching backend event structure
- Create WebSocket client with reconnection logic
- Set up error handling and connection state management

### Phase 2: React Integration

Build React hooks for WebSocket connection management.

**Tasks:**
- Create useTaskRunStream hook with connection lifecycle
- Implement event parsing and state updates
- Add TanStack Query integration for cache invalidation

### Phase 3: UI Components

Build display components for task execution visualization.

**Tasks:**
- Create TaskStatusBadge for status indicators
- Build ToolCallItem for individual tool displays
- Implement ExecutionTimeline for step-by-step progress
- Create TaskRunViewer as main container component

### Phase 4: Testing & Validation

Validate WebSocket connection, event handling, and UI rendering.

**Tasks:**
- Test WebSocket connection and reconnection
- Verify event parsing and state updates
- Validate UI component rendering
- Test error scenarios and edge cases

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE frontend/src/features/tasks/types.ts

- **IMPLEMENT**: TypeScript types for task run events and status
- **PATTERN**: Mirror backend event structure from `backend/app/services/event_broadcaster.py:29-40`
- **IMPORTS**: None (base types file)
- **GOTCHA**: Status enum must match backend TaskStatus exactly
- **VALIDATE**: `cd frontend && npm run build`

```typescript
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskRun {
  id: string;
  task_id: string;
  status: TaskStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskRunEvent {
  type: 'status_change' | 'tool_call' | 'tool_result' | 'step' | 'error';
  timestamp?: string;
  data?: any;
}

export interface StatusChangeEvent extends TaskRunEvent {
  type: 'status_change';
  status: TaskStatus;
}

export interface ToolCallEvent extends TaskRunEvent {
  type: 'tool_call';
  tool_name: string;
  arguments: Record<string, any>;
}

export interface ToolResultEvent extends TaskRunEvent {
  type: 'tool_result';
  tool_name: string;
  success: boolean;
  output?: string;
  error?: string;
}

export interface StepEvent extends TaskRunEvent {
  type: 'step';
  message: string;
  iteration?: number;
}

export interface ErrorEvent extends TaskRunEvent {
  type: 'error';
  message: string;
}
```

### CREATE frontend/src/lib/websocket.ts

- **IMPLEMENT**: WebSocket client with auto-reconnection and event handling
- **PATTERN**: Error handling from `frontend/src/lib/api.ts:5-10`
- **IMPORTS**: None (uses native WebSocket API)
- **GOTCHA**: WebSocket URL uses ws:// protocol, not http://. Must handle reconnection on disconnect.
- **VALIDATE**: `cd frontend && npm run build`

```typescript
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Set<(event: MessageEvent) => void> = new Set();
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.listeners.forEach(listener => listener(event));
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          this.handleReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  onMessage(listener: (event: MessageEvent) => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
```

### CREATE frontend/src/features/tasks/hooks/useTaskRunStream.ts

- **IMPLEMENT**: React hook for WebSocket connection to task run stream
- **PATTERN**: Hook structure from `frontend/src/features/projects/hooks/useProjects.ts`
- **IMPORTS**: `import { useEffect, useState, useCallback } from 'react'`, `import { WebSocketClient } from '@/lib/websocket'`, `import { TaskRunEvent } from '../types'`
- **GOTCHA**: Must cleanup WebSocket on unmount. WebSocket URL must use ws:// protocol and correct port.
- **VALIDATE**: `cd frontend && npm run build`

```typescript
import { useEffect, useState, useCallback } from 'react';
import { WebSocketClient } from '@/lib/websocket';
import { TaskRunEvent } from '../types';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useTaskRunStream(runId: string | null) {
  const [events, setEvents] = useState<TaskRunEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    const wsUrl = `${WS_BASE}/api/runs/${runId}/stream`;
    const client = new WebSocketClient(wsUrl);

    client.connect()
      .then(() => setIsConnected(true))
      .catch((err) => setError(err.message));

    const unsubscribe = client.onMessage((event) => {
      try {
        const data = JSON.parse(event.data) as TaskRunEvent;
        setEvents((prev) => [...prev, data]);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    });

    return () => {
      unsubscribe();
      client.disconnect();
      setIsConnected(false);
    };
  }, [runId]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isConnected, error, clearEvents };
}
```

### CREATE frontend/src/features/tasks/components/TaskStatusBadge.tsx

- **IMPLEMENT**: Status badge component with color coding
- **PATTERN**: Component structure from `frontend/src/components/ui/Card.tsx`
- **IMPORTS**: `import { TaskStatus } from '../types'`
- **GOTCHA**: Use Tailwind color classes, not inline styles
- **VALIDATE**: `cd frontend && npm run build`

```typescript
'use client';

import { TaskStatus } from '../types';

interface TaskStatusBadgeProps {
  status: TaskStatus;
}

const statusConfig: Record<TaskStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'bg-gray-100 text-gray-700' },
  running: { label: 'Running', className: 'bg-blue-100 text-blue-700' },
  completed: { label: 'Completed', className: 'bg-green-100 text-green-700' },
  failed: { label: 'Failed', className: 'bg-red-100 text-red-700' },
  cancelled: { label: 'Cancelled', className: 'bg-yellow-100 text-yellow-700' },
};

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
```

### CREATE frontend/src/features/tasks/components/ToolCallItem.tsx

- **IMPLEMENT**: Display individual tool call with arguments and results
- **PATTERN**: Card component from `frontend/src/components/ui/Card.tsx`
- **IMPORTS**: `import { ToolCallEvent, ToolResultEvent } from '../types'`
- **GOTCHA**: Arguments may be complex objects, use JSON.stringify for display
- **VALIDATE**: `cd frontend && npm run build`

```typescript
'use client';

import { ToolCallEvent, ToolResultEvent } from '../types';

interface ToolCallItemProps {
  toolCall: ToolCallEvent;
  result?: ToolResultEvent;
}

export function ToolCallItem({ toolCall, result }: ToolCallItemProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-sm font-semibold text-blue-600">
          {toolCall.tool_name}
        </span>
        {result && (
          <span className={`text-xs px-2 py-0.5 rounded ${
            result.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {result.success ? 'Success' : 'Failed'}
          </span>
        )}
      </div>

      {Object.keys(toolCall.arguments).length > 0 && (
        <div className="mb-2">
          <p className="text-xs text-gray-500 mb-1">Arguments:</p>
          <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </pre>
        </div>
      )}

      {result && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Result:</p>
          <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
            {result.success ? result.output : result.error}
          </pre>
        </div>
      )}
    </div>
  );
}
```

### CREATE frontend/src/features/tasks/components/ExecutionTimeline.tsx

- **IMPLEMENT**: Timeline view of execution steps and events
- **PATTERN**: List rendering from `frontend/src/features/projects/components/ProjectList.tsx`
- **IMPORTS**: `import { TaskRunEvent, ToolCallEvent, ToolResultEvent, StepEvent } from '../types'`, `import { ToolCallItem } from './ToolCallItem'`
- **GOTCHA**: Match tool calls with their results by tool_name and timestamp proximity
- **VALIDATE**: `cd frontend && npm run build`

```typescript
'use client';

import { TaskRunEvent, ToolCallEvent, ToolResultEvent, StepEvent } from '../types';
import { ToolCallItem } from './ToolCallItem';

interface ExecutionTimelineProps {
  events: TaskRunEvent[];
}

export function ExecutionTimeline({ events }: ExecutionTimelineProps) {
  const toolCalls = events.filter((e): e is ToolCallEvent => e.type === 'tool_call');
  const toolResults = events.filter((e): e is ToolResultEvent => e.type === 'tool_result');
  const steps = events.filter((e): e is StepEvent => e.type === 'step');

  return (
    <div className="space-y-4">
      {steps.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Execution Steps</h3>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex gap-2 text-sm">
                <span className="text-gray-400">{step.iteration || idx + 1}.</span>
                <span className="text-gray-700">{step.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {toolCalls.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Tool Calls</h3>
          <div className="space-y-3">
            {toolCalls.map((call, idx) => {
              const result = toolResults.find(r => r.tool_name === call.tool_name);
              return <ToolCallItem key={idx} toolCall={call} result={result} />;
            })}
          </div>
        </div>
      )}

      {events.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-8">
          Waiting for execution to start...
        </p>
      )}
    </div>
  );
}
```


### CREATE frontend/src/features/tasks/components/TaskRunViewer.tsx

- **IMPLEMENT**: Main container component for task run visualization
- **PATTERN**: Form component pattern from `frontend/src/features/projects/components/CreateProjectForm.tsx:1-82`
- **IMPORTS**: `import { Card } from '@/components/ui/Card'`, `import { useTaskRunStream } from '../hooks/useTaskRunStream'`, `import { TaskStatusBadge } from './TaskStatusBadge'`, `import { ExecutionTimeline } from './ExecutionTimeline'`, `import { TaskStatus } from '../types'`
- **GOTCHA**: Must handle null runId gracefully. Extract latest status from events.
- **VALIDATE**: `cd frontend && npm run build`

### UPDATE frontend/src/lib/types.ts

- **IMPLEMENT**: Add Task and TaskRun types to shared types file
- **PATTERN**: Existing type definitions in file
- **IMPORTS**: None (append to existing file)
- **GOTCHA**: Keep consistent with backend schemas
- **VALIDATE**: `cd frontend && npm run build`

### CREATE frontend/src/features/tasks/api/tasks.ts

- **IMPLEMENT**: API client functions for tasks and runs
- **PATTERN**: API client from `frontend/src/features/projects/api/projects.ts`
- **IMPORTS**: `import { request } from '@/lib/api'`, `import { Task, TaskRun } from '@/lib/types'`
- **GOTCHA**: Use /api prefix for all endpoints
- **VALIDATE**: `cd frontend && npm run build`

### CREATE frontend/src/features/tasks/hooks/useTaskRun.ts

- **IMPLEMENT**: TanStack Query hook for fetching task run data
- **PATTERN**: Hook from `frontend/src/features/projects/hooks/useProjects.ts`
- **IMPORTS**: `import { useQuery } from '@tanstack/react-query'`, `import { fetchTaskRun } from '../api/tasks'`
- **GOTCHA**: Disable query when runId is null
- **VALIDATE**: `cd frontend && npm run build`

### CREATE frontend/src/features/tasks/index.ts

- **IMPLEMENT**: Barrel export for tasks feature
- **PATTERN**: Standard barrel export pattern
- **IMPORTS**: None (exports only)
- **GOTCHA**: Export all public components and hooks
- **VALIDATE**: `cd frontend && npm run build`

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual components and hooks in isolation

**Framework**: Jest + React Testing Library (already configured in Next.js)

**Key Test Cases**:
- `TaskStatusBadge`: Renders correct color and label for each status
- `ToolCallItem`: Displays tool name, arguments, and results correctly
- `ExecutionTimeline`: Groups and displays events properly
- `WebSocketClient`: Connection, reconnection, and message handling

### Integration Tests

**Scope**: Test WebSocket connection with mock server

**Approach**: Use mock WebSocket server to simulate backend events

**Key Test Cases**:
- `useTaskRunStream`: Connects to WebSocket and receives events
- `TaskRunViewer`: Updates UI when events arrive
- Error handling when WebSocket connection fails
- Cleanup on component unmount

### Edge Cases

- **Null runId**: Component should display "No active task run" message
- **Connection failure**: Should display error message and attempt reconnection
- **Malformed events**: Should log error but not crash
- **Rapid status changes**: Should display latest status correctly
- **Large tool outputs**: Should handle long strings without breaking layout
- **Empty events array**: Should show "Waiting for execution" message

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd frontend && npm run lint
```

### Level 2: Type Checking

```bash
cd frontend && npm run build
```

### Level 3: Manual Validation

**Start backend and frontend**:
```bash
# Terminal 1: Start backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend && npm run dev
```

**Test WebSocket connection**:
1. Open browser to http://localhost:3000
2. Create a test task (requires task creation UI or API call)
3. Verify TaskRunViewer displays and connects (check for "Live" indicator)
4. Use backend to broadcast test events
5. Verify events appear in ExecutionTimeline

---

## ACCEPTANCE CRITERIA

- [ ] WebSocket client connects to backend stream endpoint
- [ ] Real-time events display in UI as they arrive
- [ ] Task status updates reflect in badge component
- [ ] Tool calls show with arguments and results
- [ ] Execution timeline displays steps chronologically
- [ ] Connection status indicator shows live/disconnected state
- [ ] Error messages display when connection fails
- [ ] WebSocket cleanup on component unmount
- [ ] TypeScript types match backend schemas
- [ ] All validation commands pass
- [ ] UI follows existing design patterns
- [ ] Responsive layout works on mobile

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] TypeScript build passes with no errors
- [ ] ESLint passes with no warnings
- [ ] Manual testing confirms WebSocket connection works
- [ ] Events display correctly in UI
- [ ] Status badge updates in real-time
- [ ] Tool calls render with proper formatting
- [ ] Error handling works for connection failures
- [ ] Component cleanup prevents memory leaks
- [ ] Code follows project conventions

---

## NOTES

### Design Decisions

**WebSocket vs Server-Sent Events (SSE)**:
- Chose WebSocket because backend already implements WebSocket endpoint
- WebSocket provides bidirectional communication (future: send commands to agent)
- Native browser support, no additional libraries needed

**State Management**:
- Used React useState for WebSocket events (ephemeral, real-time data)
- TanStack Query for task/run data (cacheable, REST API data)
- Separation keeps concerns clear and leverages each tool's strengths

**Reconnection Strategy**:
- Exponential backoff with max 5 attempts
- Prevents overwhelming server during outages
- User sees connection status indicator

**Event Matching**:
- Tool calls matched to results by tool_name
- Simple approach works for MVP (single-threaded agent)
- Future: Add correlation IDs for parallel tool execution

### Performance Considerations

- Events array grows unbounded during long tasks
- Consider pagination or virtualization for 100+ events
- WebSocket messages are small (<1KB typically)
- No performance issues expected for MVP scope

### Security Considerations

- WebSocket endpoint should validate run ownership (future: auth)
- No sensitive data in events (agent outputs may contain user data)
- XSS risk: Tool outputs rendered in `<pre>` tags (safe)

### Future Enhancements

- Pause/resume task execution
- Send commands to agent via WebSocket
- Export execution log as JSON/text
- Collapsible timeline sections
- Search/filter events
- Real-time token usage tracking
