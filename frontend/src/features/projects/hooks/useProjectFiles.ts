import { useQuery } from '@tanstack/react-query';
import { fetchProjectFiles } from '../api/files';

export function useProjectFiles(projectId: string | null) {
  return useQuery({
    queryKey: ['projectFiles', projectId],
    queryFn: () => fetchProjectFiles(projectId!),
    enabled: !!projectId,
  });
}
