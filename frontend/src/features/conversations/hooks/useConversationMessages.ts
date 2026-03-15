import { useQuery } from '@tanstack/react-query';
import { fetchMessages } from '../api/conversations';

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ['conversationMessages', conversationId],
    queryFn: () => fetchMessages(conversationId!),
    enabled: !!conversationId,
  });
}
