import { useQuery } from '@tanstack/react-query';
import { fetchRunArtifacts } from '../api/artifacts';

export function useRunArtifacts(runId: string | null) {
  return useQuery({
    queryKey: ['runArtifacts', runId],
    queryFn: () => fetchRunArtifacts(runId!),
    enabled: !!runId,
  });
}
