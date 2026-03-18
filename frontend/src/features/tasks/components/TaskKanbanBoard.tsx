'use client';

import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

import { QueueStatus } from '@/lib/types';

import { useTaskKanban } from '../hooks/useTaskKanban';
import { KanbanColumn } from './KanbanColumn';

interface TaskKanbanBoardProps {
  projectId?: string;
}

export function TaskKanbanBoard({ projectId }: TaskKanbanBoardProps) {
  const { kanban, isLoading, error, updateTaskStatus } = useTaskKanban(projectId);

  if (isLoading) {
    return <div className="p-4 text-gray-600">Loading tasks...</div>;
  }
  if (error) {
    return <div className="p-4 text-red-600">Failed to load task board.</div>;
  }
  if (!kanban) {
    return <div className="p-4 text-gray-600">No task data available.</div>;
  }

  const handleDrop = (taskId: string, newStatus: QueueStatus) => {
    updateTaskStatus({ taskId, status: newStatus });
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex gap-4 overflow-x-auto p-2">
        <KanbanColumn
          title="Scheduled"
          status="scheduled"
          tasks={kanban.scheduled}
          count={kanban.scheduled.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="Queue"
          status="queued"
          tasks={kanban.queued}
          count={kanban.queued.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="In Progress"
          status="in_progress"
          tasks={kanban.in_progress}
          count={kanban.in_progress.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="Done"
          status="done"
          tasks={kanban.done}
          count={kanban.done.length}
          onDrop={handleDrop}
        />
      </div>
    </DndProvider>
  );
}
