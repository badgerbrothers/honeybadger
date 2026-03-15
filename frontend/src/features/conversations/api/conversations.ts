import { request } from '@/lib/api';
import {
  Conversation,
  CreateConversationInput,
  CreateMessageInput,
  Message,
} from '@/lib/types';

export async function fetchConversation(conversationId: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${conversationId}`);
}

export async function fetchConversations(projectId?: string): Promise<Conversation[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
  return request<Conversation[]>(`/conversations/${query}`);
}

export async function createConversation(data: CreateConversationInput): Promise<Conversation> {
  return request<Conversation>('/conversations/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchMessages(conversationId: string): Promise<Message[]> {
  return request<Message[]>(`/conversations/${conversationId}/messages`);
}

export async function createMessage(
  conversationId: string,
  data: CreateMessageInput,
): Promise<Message> {
  return request<Message>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
