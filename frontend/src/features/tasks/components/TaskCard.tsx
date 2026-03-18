'use client';

import React from 'react';
import { useDrag } from 'react-dnd';

import { Card } from '@/components/ui/Card';
import { Task } from '@/lib/types';

export const TASK_CARD_DND_TYPE = 'TASK_CARD';

export interface TaskCardDragItem {
  taskId: string;
  fromStatus: Task['queue_status'];
}

interface TaskCardProps {
  task: Task;
}

export function TaskCard({ task }: TaskCardProps) {
  const [{ isDragging }, dragRef] = useDrag(
    () => ({
      type: TASK_CARD_DND_TYPE,
      item: {
        taskId: task.id,
        fromStatus: task.queue_status,
      } satisfies TaskCardDragItem,
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    }),
    [task.id, task.queue_status]
  );

  return (
    <div
      ref={(node) => {
        dragRef(node);
      }}
      className={isDragging ? 'opacity-60' : ''}
    >
      <Card className="mb-2 cursor-move p-4 transition-shadow hover:shadow-md">
        <h3 className="mb-2 text-sm font-medium text-gray-900">{task.goal}</h3>
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
          {task.assigned_agent ? (
            <span className="rounded bg-gray-100 px-2 py-0.5">{task.assigned_agent}</span>
          ) : null}
          {task.scheduled_at ? (
            <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700">
              {new Date(task.scheduled_at).toLocaleString()}
            </span>
          ) : null}
          {task.priority > 0 ? (
            <span className="rounded bg-orange-100 px-2 py-0.5 text-orange-700">P{task.priority}</span>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
