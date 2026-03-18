'use client';

import React from 'react';
import { useDrop } from 'react-dnd';

import { QueueStatus, Task } from '@/lib/types';

import { TASK_CARD_DND_TYPE, TaskCard, TaskCardDragItem } from './TaskCard';

interface KanbanColumnProps {
  title: string;
  status: QueueStatus;
  tasks: Task[];
  count: number;
  onDrop: (taskId: string, newStatus: QueueStatus) => void;
}

export function KanbanColumn({ title, status, tasks, count, onDrop }: KanbanColumnProps) {
  const [{ isOver, canDrop }, dropRef] = useDrop(
    () => ({
      accept: TASK_CARD_DND_TYPE,
      canDrop: (item: TaskCardDragItem) => item.fromStatus !== status,
      drop: (item: TaskCardDragItem) => {
        if (item.fromStatus !== status) {
          onDrop(item.taskId, status);
        }
      },
      collect: (monitor) => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    [onDrop, status]
  );

  return (
    <div
      ref={(node) => {
        dropRef(node);
      }}
      className={`min-w-[280px] flex-1 rounded-lg p-4 ${
        isOver && canDrop ? 'bg-blue-50' : 'bg-gray-50'
      }`}
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-semibold text-gray-700">{title}</h2>
        <span className="rounded-full bg-gray-200 px-2 py-1 text-sm text-gray-600">{count}</span>
      </div>
      <div className="space-y-2">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
        {tasks.length === 0 ? <p className="py-8 text-center text-gray-400">No tasks</p> : null}
      </div>
    </div>
  );
}
