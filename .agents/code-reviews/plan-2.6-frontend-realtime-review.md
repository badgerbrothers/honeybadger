# Code Review: Frontend WebSocket Real-time Updates

**Date:** 2026-03-12
**Reviewer:** AI Code Review Agent
**Scope:** WebSocket real-time updates feature implementation

## Stats

- Files Modified: 3
- Files Added: 11
- Files Deleted: 0
- New lines: ~450
- Deleted lines: 1

## Summary

Reviewed the implementation of WebSocket-based real-time task execution monitoring. The feature includes a WebSocket client, React hooks, and UI components for displaying live task progress. Overall code quality is good with clean separation of concerns, but several issues need attention.

## Issues Found

### CRITICAL ISSUES

None found.

### HIGH SEVERITY ISSUES

**Issue 1: Type Duplication**

severity: high
file: frontend/src/lib/types.ts, frontend/src/features/tasks/types.ts
line: types.ts:17-26, tasks/types.ts:3-12
issue: TaskRun interface defined in two locations
detail: The TaskRun interface is duplicated in both the shared types file and the feature-specific types file. This creates maintenance burden and potential for inconsistency if one definition is updated but not the other.
suggestion: Remove TaskRun from frontend/src/features/tasks/types.ts and import it from @/lib/types instead. Keep only feature-specific types (TaskRunEvent and its variants) in the tasks types file.

**Issue 2: Unsafe Type Assertion**

severity: high
file: frontend/src/features/tasks/components/TaskRunViewer.tsx
line: 22
issue: Using 'as any' type assertion bypasses type safety
detail: Line 22 uses `(lastStatus as any).status` which completely bypasses TypeScript's type checking. This could lead to runtime errors if the event structure doesn't match expectations.
suggestion: Use a proper type guard or cast to StatusChangeEvent:
```typescript
const currentStatus = useMemo(() => {
  const statusEvents = events.filter((e): e is StatusChangeEvent => e.type === 'status_change');
  if (statusEvents.length === 0) return initialStatus;
  const lastStatus = statusEvents[statusEvents.length - 1];
  return lastStatus.status || initialStatus;
}, [events, initialStatus]);
```

**Issue 3: WebSocket Reconnection on Intentional Disconnect**

severity: high
file: frontend/src/lib/websocket.ts
line: 32-34
issue: onclose handler always triggers reconnection
detail: The WebSocket onclose handler (line 32) always calls handleReconnect(), even when disconnect() is called intentionally. This means the client will try to reconnect even after the user navigates away or the component unmounts.
suggestion: Add a flag to track intentional disconnects:
```typescript
private intentionalClose = false;

disconnect() {
  this.intentionalClose = true;
  if (this.ws) {
    this.ws.close();
    this.ws = null;
  }
  this.listeners.clear();
}

// In connect():
this.ws.onclose = () => {
  if (!this.intentionalClose) {
    this.handleReconnect();
  }
};
```


### MEDIUM SEVERITY ISSUES

**Issue 4: Fragile Tool Call Matching**

severity: medium
file: frontend/src/features/tasks/components/ExecutionTimeline.tsx
line: 36
issue: Tool calls matched to results by name only
detail: Line 36 uses `toolResults.find(r => r.tool_name === call.tool_name)` which will match the first result with the same tool name. If the same tool is called multiple times, results may be matched incorrectly.
suggestion: Backend should include a correlation ID in events. For MVP, add a timestamp-based matching or index-based matching as a fallback. Document this limitation in code comments.

**Issue 5: Connection State Not Updated on Error**

severity: medium
file: frontend/src/features/tasks/hooks/useTaskRunStream.ts
line: 18-20
issue: isConnected state not set to false when connection fails
detail: When client.connect() fails (line 20), the error is captured but isConnected remains false (never set to true). However, if connection succeeds then fails, isConnected won't be updated.
suggestion: Add error handler to update connection state:
```typescript
client.connect()
  .then(() => setIsConnected(true))
  .catch((err) => {
    setError(err.message);
    setIsConnected(false);
  });
```

**Issue 6: Unbounded Event Array Growth**

severity: medium
file: frontend/src/features/tasks/hooks/useTaskRunStream.ts
line: 25
issue: Events array grows without limit
detail: Line 25 appends every event to the array without any size limit. For long-running tasks with many tool calls, this could consume significant memory.
suggestion: Implement a maximum event limit (e.g., 1000 events) or use a circular buffer. Alternatively, add pagination or virtualization in the UI.

**Issue 7: No Cleanup of Reconnection Timers**

severity: medium
file: frontend/src/lib/websocket.ts
line: 44-46
issue: setTimeout not cleared on disconnect
detail: The reconnection logic uses setTimeout (line 44) but doesn't store the timer ID. If disconnect() is called while a reconnection is pending, the timer will still fire.
suggestion: Store timer IDs and clear them in disconnect():
```typescript
private reconnectTimer: NodeJS.Timeout | null = null;

private handleReconnect() {
  if (this.reconnectAttempts < this.maxReconnectAttempts) {
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(console.error);
    }, this.reconnectDelay * this.reconnectAttempts);
  }
}

disconnect() {
  if (this.reconnectTimer) {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }
  // ... rest of disconnect logic
}
```

### LOW SEVERITY ISSUES

**Issue 8: Console.error Usage**

severity: low
file: frontend/src/lib/websocket.ts, frontend/src/features/tasks/hooks/useTaskRunStream.ts
line: 28, 45, 27
issue: Using console.error instead of proper logging
detail: Multiple locations use console.error for logging. This makes it difficult to control logging in production or integrate with logging services.
suggestion: Consider using a logging library or at least a centralized logging utility that can be configured per environment.

**Issue 9: Missing Key Props Warning**

severity: low
file: frontend/src/features/tasks/components/ExecutionTimeline.tsx
line: 22, 37
issue: Using array index as React key
detail: Lines 22 and 37 use array index as the key prop. This can cause issues if events are reordered or filtered.
suggestion: Use a unique identifier if available, or combine timestamp with index:
```typescript
key={`${step.timestamp || ''}-${idx}`}
```

**Issue 10: Missing Null Check**

severity: low
file: frontend/src/features/tasks/components/TaskStatusBadge.tsx
line: 18
issue: No null check for statusConfig lookup
detail: If an invalid status is passed, statusConfig[status] will be undefined, causing a runtime error on line 21.
suggestion: Add a fallback or validation:
```typescript
const config = statusConfig[status] || statusConfig.pending;
```


## POSITIVE FINDINGS

**Strengths:**

1. **Clean Architecture**: Excellent separation of concerns with WebSocket client, hooks, and UI components properly isolated.

2. **Type Safety**: Good use of TypeScript with discriminated unions for event types (TaskRunEvent variants).

3. **React Best Practices**: Proper use of useEffect cleanup, useMemo for derived state, and useCallback for stable function references.

4. **Component Composition**: UI components are small, focused, and reusable (TaskStatusBadge, ToolCallItem, ExecutionTimeline).

5. **Error Handling**: Error states are captured and displayed to users appropriately.

6. **Accessibility**: Good use of semantic HTML and ARIA-friendly color contrast in status badges.

7. **Code Consistency**: Follows existing project patterns (TanStack Query, Tailwind CSS, component structure).

## RECOMMENDATIONS

### Immediate (Before Merge)

1. Fix type duplication (Issue 1) - Remove duplicate TaskRun interface
2. Replace unsafe type assertion (Issue 2) - Use proper type guard
3. Fix WebSocket reconnection logic (Issue 3) - Add intentional disconnect flag

### Short Term (Next Sprint)

4. Improve tool call matching (Issue 4) - Add correlation IDs or document limitation
5. Fix connection state handling (Issue 5) - Update isConnected on all state changes
6. Add event limit (Issue 6) - Implement max 1000 events or circular buffer
7. Clear reconnection timers (Issue 7) - Store and clear setTimeout IDs

### Long Term (Future Enhancement)

8. Implement proper logging (Issue 8)
9. Use better React keys (Issue 9)
10. Add defensive null checks (Issue 10)

## CONCLUSION

**Overall Assessment: GOOD with required fixes**

The WebSocket real-time updates feature is well-implemented with clean architecture and good React practices. The code follows project conventions and provides a solid foundation for real-time task monitoring.

**Critical Issues:** 0
**High Issues:** 3 (must fix before merge)
**Medium Issues:** 4 (should fix soon)
**Low Issues:** 3 (nice to have)

The high-severity issues are straightforward to fix and don't require architectural changes. Once addressed, this feature is ready for production use.

**Estimated Fix Time:** 1-2 hours for high-severity issues

