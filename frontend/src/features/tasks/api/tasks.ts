import { request } from '@/lib/api';
import { CreateTaskInput, Task, TaskRun } from '@/lib/types';

export async function fetchTask(taskId: string): Promise<Task> {
  return request<Task>(`/tasks/${taskId}`);
}

export async function fetchTasks(params?: {
  conversationId?: string;
  projectId?: string;
}): Promise<Task[]> {
  const query = new URLSearchParams();
  if (params?.conversationId) query.set('conversation_id', params.conversationId);
  if (params?.projectId) query.set('project_id', params.projectId);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request<Task[]>(`/tasks/${suffix}`);
}

export async function createTask(data: CreateTaskInput): Promise<Task> {
  return request<Task>('/tasks/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function createTaskRun(taskId: string): Promise<TaskRun> {
  return request<TaskRun>(`/tasks/${taskId}/runs`, {
    method: 'POST',
  });
}

export async function retryTaskRun(taskId: string): Promise<TaskRun> {
  return request<TaskRun>(`/tasks/${taskId}/retry`, {
    method: 'POST',
  });
}

export async function fetchTaskRun(runId: string): Promise<TaskRun> {
  return request<TaskRun>(`/runs/${runId}`);
}

export async function cancelTaskRun(runId: string): Promise<TaskRun> {
  return request<TaskRun>(`/runs/${runId}/cancel`, {
    method: 'POST',
  });
}
