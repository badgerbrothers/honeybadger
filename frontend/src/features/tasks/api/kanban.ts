import { request } from '@/lib/api';
import { QueueStatus, Task } from '@/lib/types';

export interface KanbanBoardData {
  scheduled: Task[];
  queued: Task[];
  in_progress: Task[];
  done: Task[];
}

export async function fetchKanbanBoard(projectId?: string): Promise<KanbanBoardData> {
  const query = projectId ? `?project_id=${projectId}` : '';
  return request<KanbanBoardData>(`/tasks/kanban${query}`);
}

export async function updateTaskQueueStatus(
  taskId: string,
  queueStatus: QueueStatus
): Promise<Task> {
  return request<Task>(`/tasks/${taskId}/queue-status?queue_status=${queueStatus}`, {
    method: 'PATCH',
  });
}
