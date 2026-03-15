import { useQuery } from '@tanstack/react-query';
import { fetchConversation } from '../api/conversations';

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => fetchConversation(conversationId!),
    enabled: !!conversationId,
  });
}
