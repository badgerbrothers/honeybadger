import { useQuery } from '@tanstack/react-query';
import { fetchTaskRun } from '../api/tasks';

export function useTaskRun(runId: string | null) {
  return useQuery({
    queryKey: ['taskRun', runId],
    queryFn: () => fetchTaskRun(runId!),
    enabled: !!runId,
  });
}
