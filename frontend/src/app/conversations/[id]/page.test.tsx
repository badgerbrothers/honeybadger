import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import ConversationDetailPage from './page';

const mockPush = vi.fn();
const mockCreateTask = vi.fn();

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'conv-1' }),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/features/conversations/hooks/useConversation', () => ({
  useConversation: () => ({
    data: { id: 'conv-1', project_id: 'proj-1', title: 'Conversation Title' },
    isLoading: false,
  }),
}));

vi.mock('@/features/conversations/hooks/useConversationMessages', () => ({
  useConversationMessages: () => ({
    data: [],
    isLoading: false,
  }),
}));

vi.mock('@/features/tasks/hooks/useModelCatalog', () => ({
  useModelCatalog: () => ({
    data: {
      default_model: 'gpt-5.3-codex',
      supported_models: ['gpt-5.3-codex', 'gpt-4-turbo-preview'],
    },
    isLoading: false,
  }),
}));

vi.mock('@/features/conversations/api/conversations', () => ({
  createMessage: vi.fn().mockResolvedValue({ id: 'msg-1' }),
}));

vi.mock('@/features/tasks/api/tasks', () => ({
  fetchTasks: vi.fn().mockResolvedValue([]),
  createTask: (...args: unknown[]) => mockCreateTask(...args),
  createTaskRun: vi.fn().mockResolvedValue({ id: 'run-1' }),
  retryTaskRun: vi.fn().mockResolvedValue({ id: 'run-2' }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConversationDetailPage />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
});

describe('ConversationDetailPage model selection', () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockCreateTask.mockReset();
    mockCreateTask.mockResolvedValue({
      id: 'task-1',
      conversation_id: 'conv-1',
      project_id: 'proj-1',
      goal: 'test',
      skill: null,
      model: 'gpt-5.3-codex',
      current_run_id: null,
      queue_status: 'scheduled',
      scheduled_at: null,
      priority: 0,
      assigned_agent: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  });

  it('initializes model select with backend default model', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByRole('combobox')[0]).toHaveValue('gpt-5.3-codex');
    });
  });

  it('submits selected model in task payload', async () => {
    renderPage();

    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'gpt-4-turbo-preview' } });
    fireEvent.change(screen.getAllByPlaceholderText('Task goal...')[0], {
      target: { value: 'Run task with selected model' },
    });
    fireEvent.submit(screen.getByRole('button', { name: 'Create Task' }).closest('form')!);

    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledTimes(1);
    });

    expect(mockCreateTask).toHaveBeenCalledWith(
      expect.objectContaining({
        conversation_id: 'conv-1',
        project_id: 'proj-1',
        goal: 'Run task with selected model',
        model: 'gpt-4-turbo-preview',
      }),
    );
  });
});
