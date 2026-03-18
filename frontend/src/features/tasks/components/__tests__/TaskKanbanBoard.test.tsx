import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TaskKanbanBoard } from '../TaskKanbanBoard';

vi.mock('../../hooks/useTaskKanban', () => ({
  useTaskKanban: () => ({
    kanban: {
      scheduled: [
        {
          id: 'task-1',
          conversation_id: 'conv-1',
          project_id: 'proj-1',
          goal: 'Scheduled Task',
          skill: null,
          model: 'gpt-5.3-codex',
          current_run_id: null,
          queue_status: 'scheduled',
          scheduled_at: null,
          priority: 0,
          assigned_agent: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      queued: [],
      in_progress: [],
      done: [],
    },
    isLoading: false,
    error: null,
    updateTaskStatus: vi.fn(),
  }),
}));

describe('TaskKanbanBoard', () => {
  it('renders all kanban columns and task card', () => {
    render(<TaskKanbanBoard />);
    expect(screen.getByText('Scheduled')).toBeInTheDocument();
    expect(screen.getByText('Queue')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('Scheduled Task')).toBeInTheDocument();
  });
});
