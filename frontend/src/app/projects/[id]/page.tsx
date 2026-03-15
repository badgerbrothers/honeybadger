'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Container } from '@/components/layout/Container';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FileList } from '@/features/projects/components/FileList';
import { FileUploadZone } from '@/features/projects/components/FileUploadZone';
import { useProject } from '@/features/projects/hooks/useProject';
import { createConversation } from '@/features/conversations/api/conversations';
import { useProjectConversations } from '@/features/conversations/hooks/useProjectConversations';

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id || null;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [conversationTitle, setConversationTitle] = useState('');

  const { data: project, isLoading, error } = useProject(projectId);
  const { data: conversations } = useProjectConversations(projectId);
  const { mutate: createConversationMutation, isPending: isCreatingConversation } = useMutation({
    mutationFn: (title: string) =>
      createConversation({
        project_id: projectId!,
        title: title || `Conversation ${new Date().toLocaleString()}`,
      }),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['projectConversations', projectId] });
      setConversationTitle('');
      router.push(`/conversations/${conversation.id}`);
    },
  });

  if (isLoading) {
    return (
      <Container>
        <p className="text-gray-500">Loading project...</p>
      </Container>
    );
  }

  if (error || !projectId || !project) {
    return (
      <Container>
        <Card>
          <p className="text-red-700">Failed to load project.</p>
        </Card>
      </Container>
    );
  }

  return (
    <Container>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
            <p className="text-gray-600 mt-2">{project.description || 'No description'}</p>
          </div>
          <div className="flex gap-2">
            <Link href="/projects" className="text-sm text-blue-600 hover:text-blue-700">
              Back to projects
            </Link>
            <Link href={`/projects/${project.id}/artifacts`} className="text-sm text-blue-600 hover:text-blue-700">
              View artifacts
            </Link>
          </div>
        </div>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Conversations</h2>
          <form
            className="flex gap-2 mb-4"
            onSubmit={(event) => {
              event.preventDefault();
              createConversationMutation(conversationTitle.trim());
            }}
          >
            <input
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="New conversation title"
              value={conversationTitle}
              onChange={(event) => setConversationTitle(event.target.value)}
            />
            <Button type="submit" disabled={isCreatingConversation}>
              {isCreatingConversation ? 'Creating...' : 'Open Conversation'}
            </Button>
          </form>

          {conversations && conversations.length > 0 ? (
            <div className="space-y-2">
              {conversations.map((conversation) => (
                <Link
                  key={conversation.id}
                  href={`/conversations/${conversation.id}`}
                  className="block rounded-lg border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <p className="font-medium text-gray-900">{conversation.title}</p>
                  <p className="text-gray-500">Created {new Date(conversation.created_at).toLocaleString()}</p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No conversations yet.</p>
          )}
        </Card>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <FileUploadZone projectId={projectId} />
          <FileList projectId={projectId} />
        </div>
      </div>
    </Container>
  );
}
