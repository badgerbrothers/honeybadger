'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Container } from '@/components/layout/Container';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { createMessage } from '@/features/conversations/api/conversations';
import { useConversation } from '@/features/conversations/hooks/useConversation';
import { useConversationMessages } from '@/features/conversations/hooks/useConversationMessages';
import { useModelCatalog } from '@/features/tasks/hooks/useModelCatalog';
import { createTask, createTaskRun, fetchTasks, retryTaskRun } from '@/features/tasks/api/tasks';

export default function ConversationDetailPage() {
  const params = useParams<{ id: string }>();
  const conversationId = params?.id || null;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [messageContent, setMessageContent] = useState('');
  const [goal, setGoal] = useState('');
  const [skill, setSkill] = useState('');
  const [model, setModel] = useState('');
  const modelInitializedRef = useRef(false);

  const { data: conversation, isLoading: isConversationLoading } = useConversation(conversationId);
  const { data: messages, isLoading: isMessagesLoading } = useConversationMessages(conversationId);
  const { data: modelCatalog, isLoading: isModelCatalogLoading } = useModelCatalog();
  const { data: tasks, isLoading: isTasksLoading } = useQuery({
    queryKey: ['tasksByConversation', conversationId],
    queryFn: () => fetchTasks({ conversationId: conversationId! }),
    enabled: !!conversationId,
  });

  useEffect(() => {
    if (!modelInitializedRef.current && modelCatalog?.default_model) {
      setModel(modelCatalog.default_model);
      modelInitializedRef.current = true;
    }
  }, [modelCatalog]);

  const { mutate: createMessageMutation, isPending: isCreatingMessage } = useMutation({
    mutationFn: (content: string) =>
      createMessage(conversationId!, {
        role: 'user',
        content,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversationMessages', conversationId] });
      setMessageContent('');
    },
  });

  const { mutate: createTaskMutation, isPending: isCreatingTask } = useMutation({
    mutationFn: () => {
      const payload = {
        conversation_id: conversationId!,
        project_id: conversation!.project_id,
        goal: goal.trim(),
      } as {
        conversation_id: string;
        project_id: string;
        goal: string;
        skill?: string;
        model?: string;
      };

      const normalizedSkill = skill.trim();
      const normalizedModel = model.trim();
      if (normalizedSkill) payload.skill = normalizedSkill;
      if (normalizedModel) payload.model = normalizedModel;
      return createTask(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasksByConversation', conversationId] });
      setGoal('');
    },
  });

  const { mutate: createRunMutation, isPending: isCreatingRun } = useMutation({
    mutationFn: (taskId: string) => createTaskRun(taskId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['tasksByConversation', conversationId] });
      router.push(`/runs/${run.id}`);
    },
  });

  const { mutate: retryRunMutation, isPending: isRetryingRun } = useMutation({
    mutationFn: (taskId: string) => retryTaskRun(taskId),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['tasksByConversation', conversationId] });
      router.push(`/runs/${run.id}`);
    },
  });

  if (isConversationLoading || !conversationId) {
    return (
      <Container>
        <p className="text-gray-500">Loading conversation...</p>
      </Container>
    );
  }

  if (!conversation) {
    return (
      <Container>
        <Card>
          <p className="text-red-700">Conversation not found.</p>
        </Card>
      </Container>
    );
  }

  return (
    <Container>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{conversation.title}</h1>
            <p className="text-sm text-gray-600 mt-1">Conversation ID: {conversation.id}</p>
          </div>
          <Link href={`/projects/${conversation.project_id}`} className="text-sm text-blue-600 hover:text-blue-700">
            Back to project
          </Link>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Messages</h2>
            <div className="space-y-3 max-h-96 overflow-auto mb-4">
              {isMessagesLoading && <p className="text-gray-500 text-sm">Loading messages...</p>}
              {!isMessagesLoading && (!messages || messages.length === 0) && (
                <p className="text-gray-500 text-sm">No messages yet.</p>
              )}
              {messages?.map((message) => (
                <div key={message.id} className="rounded-lg border border-gray-200 p-3">
                  <p className="text-xs uppercase text-gray-500 mb-1">{message.role}</p>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
            </div>
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!messageContent.trim()) return;
                createMessageMutation(messageContent.trim());
              }}
            >
              <textarea
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm min-h-24"
                placeholder="Write a user message..."
                value={messageContent}
                onChange={(event) => setMessageContent(event.target.value)}
              />
              <Button type="submit" disabled={isCreatingMessage}>
                {isCreatingMessage ? 'Sending...' : 'Send Message'}
              </Button>
            </form>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Create Task</h2>
            <form
              className="space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                if (!goal.trim()) return;
                createTaskMutation();
              }}
            >
              <textarea
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm min-h-24"
                placeholder="Task goal..."
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
              />
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="Skill (optional, e.g. core_piv_loop:prime)"
                value={skill}
                onChange={(event) => setSkill(event.target.value)}
              />
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={isModelCatalogLoading || !modelCatalog}
              >
                {!modelCatalog && (
                  <option value="">
                    {isModelCatalogLoading ? 'Loading models...' : 'Default model (server)'}
                  </option>
                )}
                {modelCatalog?.supported_models.map((supportedModel) => (
                  <option key={supportedModel} value={supportedModel}>
                    {supportedModel}
                  </option>
                ))}
              </select>
              <Button type="submit" disabled={isCreatingTask}>
                {isCreatingTask ? 'Creating task...' : 'Create Task'}
              </Button>
            </form>
          </Card>
        </div>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Tasks</h2>
          {isTasksLoading && <p className="text-sm text-gray-500">Loading tasks...</p>}
          {!isTasksLoading && (!tasks || tasks.length === 0) && (
            <p className="text-sm text-gray-500">No tasks yet.</p>
          )}
          <div className="space-y-3">
            {tasks?.map((task) => (
              <div key={task.id} className="rounded-lg border border-gray-200 p-4">
                <p className="text-sm text-gray-900 font-medium">{task.goal}</p>
                <p className="text-xs text-gray-500 mt-1">Task ID: {task.id}</p>
                <div className="flex flex-wrap items-center gap-3 mt-3">
                  {task.current_run_id ? (
                    <Link href={`/runs/${task.current_run_id}`} className="text-sm text-blue-600 hover:text-blue-700">
                      Open Current Run
                    </Link>
                  ) : (
                    <span className="text-sm text-gray-500">No active run</span>
                  )}
                  <Button
                    type="button"
                    onClick={() => createRunMutation(task.id)}
                    disabled={isCreatingRun}
                  >
                    {isCreatingRun ? 'Starting...' : 'Create Run'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => retryRunMutation(task.id)}
                    disabled={isRetryingRun}
                  >
                    {isRetryingRun ? 'Retrying...' : 'Retry Task'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Container>
  );
}
