'use client';

import { useMemo } from 'react';
import { Card } from '@/components/ui/Card';
import { useTaskRunStream } from '../hooks/useTaskRunStream';
import { TaskStatusBadge } from './TaskStatusBadge';
import { ExecutionTimeline } from './ExecutionTimeline';
import { TaskStatus, StatusChangeEvent } from '../types';

interface TaskRunViewerProps {
  runId: string | null;
  initialStatus?: TaskStatus;
}

export function TaskRunViewer({ runId, initialStatus = 'pending' }: TaskRunViewerProps) {
  const { events, isConnected, error } = useTaskRunStream(runId);

  const currentStatus = useMemo(() => {
    const statusEvents = events.filter((e): e is StatusChangeEvent => e.type === 'status_change');
    if (statusEvents.length === 0) return initialStatus;
    const lastStatus = statusEvents[statusEvents.length - 1];
    return lastStatus.status || initialStatus;
  }, [events, initialStatus]);

  if (!runId) {
    return (
      <Card>
        <p className="text-gray-500 text-center py-8">No active task run</p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Task Execution</h2>
        <div className="flex items-center gap-3">
          {isConnected && (
            <span className="flex items-center gap-2 text-sm text-gray-600">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              Live
            </span>
          )}
          <TaskStatusBadge status={currentStatus} />
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">Connection error: {error}</p>
        </div>
      )}

      <ExecutionTimeline events={events} />
    </Card>
  );
}
