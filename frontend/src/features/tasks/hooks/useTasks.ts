import { useQuery } from '@tanstack/react-query';
import { fetchTasks } from '../api/tasks';

export function useTasks(filters?: { conversationId?: string; projectId?: string }) {
  return useQuery({
    queryKey: ['tasks', filters?.conversationId ?? null, filters?.projectId ?? null],
    queryFn: () => fetchTasks(filters),
  });
}
