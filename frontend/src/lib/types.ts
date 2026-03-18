export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at?: string;
}

export interface CreateProjectInput {
  name: string;
  description: string;
}

export interface ApiError {
  detail: string;
}

export interface Task {
  id: string;
  conversation_id: string;
  project_id: string;
  goal: string;
  skill: string | null;
  model: string;
  current_run_id: string | null;
  queue_status: QueueStatus;
  scheduled_at: string | null;
  priority: number;
  assigned_agent: string | null;
  created_at: string;
  updated_at: string;
}

export type QueueStatus = 'scheduled' | 'queued' | 'in_progress' | 'done';

export interface TaskRun {
  id: string;
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  logs: Array<Record<string, unknown>> | null;
  working_memory: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export type MessageRole = 'user' | 'assistant' | 'system';

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface CreateConversationInput {
  project_id: string;
  title: string;
}

export interface CreateMessageInput {
  role: MessageRole;
  content: string;
}

export interface CreateTaskInput {
  conversation_id: string;
  project_id: string;
  goal: string;
  skill?: string | null;
  model?: string | null;
  scheduled_at?: string | null;
  priority?: number;
  assigned_agent?: string | null;
}

export interface Artifact {
  id: string;
  project_id: string;
  task_run_id: string;
  name: string;
  artifact_type: string;
  storage_path: string;
  size: number;
  mime_type: string | null;
  created_at: string;
}

export interface SavedProjectNode {
  id: string;
  project_id: string;
  name: string;
  path: string;
  size: number;
}
