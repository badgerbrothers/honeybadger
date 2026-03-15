import { useQuery } from '@tanstack/react-query';
import { fetchProjectArtifacts } from '../api/artifacts';

export function useProjectArtifacts(projectId: string | null) {
  return useQuery({
    queryKey: ['projectArtifacts', projectId],
    queryFn: () => fetchProjectArtifacts(projectId!),
    enabled: !!projectId,
  });
}
