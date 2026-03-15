import { useQuery } from '@tanstack/react-query';
import { fetchConversations } from '../api/conversations';

export function useProjectConversations(projectId: string | null) {
  return useQuery({
    queryKey: ['projectConversations', projectId],
    queryFn: () => fetchConversations(projectId!),
    enabled: !!projectId,
  });
}
