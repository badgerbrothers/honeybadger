import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { QueueStatus } from '@/lib/types';

import { fetchKanbanBoard, updateTaskQueueStatus } from '../api/kanban';

export function useTaskKanban(projectId?: string) {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['kanban', projectId ?? null],
    queryFn: () => fetchKanbanBoard(projectId),
    refetchInterval: 5000,
  });

  const updateStatus = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: QueueStatus }) =>
      updateTaskQueueStatus(taskId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kanban', projectId ?? null] });
    },
  });

  return {
    kanban: data,
    isLoading,
    error,
    updateTaskStatus: updateStatus.mutate,
  };
}
