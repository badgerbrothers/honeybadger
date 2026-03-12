export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
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
  created_at: string;
  updated_at: string;
}

export interface TaskRun {
  id: string;
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
