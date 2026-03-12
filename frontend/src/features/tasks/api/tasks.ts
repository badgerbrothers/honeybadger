import { request } from '@/lib/api';
import { Task, TaskRun } from '@/lib/types';

export async function fetchTask(taskId: string): Promise<Task> {
  return request<Task>(`/tasks/${taskId}`);
}

export async function fetchTaskRun(runId: string): Promise<TaskRun> {
  return request<TaskRun>(`/runs/${runId}`);
}

export async function cancelTaskRun(runId: string): Promise<TaskRun> {
  return request<TaskRun>(`/runs/${runId}/cancel`, {
    method: 'POST',
  });
}
