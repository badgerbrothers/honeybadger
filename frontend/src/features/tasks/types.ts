export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type TaskRunEventType =
  | 'status_change'
  | 'run_started'
  | 'run_completed'
  | 'run_failed'
  | 'run_cancelled'
  | 'tool_call'
  | 'tool_result'
  | 'step'
  | 'artifact_created'
  | 'error';

export interface TaskRunEvent {
  type: TaskRunEventType;
  timestamp?: string;
  [key: string]: unknown;
}

export interface StatusChangeEvent extends TaskRunEvent {
  type: 'status_change';
  status: TaskStatus;
}

export interface RunStartedEvent extends TaskRunEvent {
  type: 'run_started';
  status?: TaskStatus;
}

export interface RunCompletedEvent extends TaskRunEvent {
  type: 'run_completed';
  result?: string;
}

export interface RunFailedEvent extends TaskRunEvent {
  type: 'run_failed';
  error?: string;
}

export interface RunCancelledEvent extends TaskRunEvent {
  type: 'run_cancelled';
}

export interface ToolCallEvent extends TaskRunEvent {
  type: 'tool_call';
  tool_name?: string;
  tool?: string;
  arguments?: Record<string, unknown>;
}

export interface ToolResultEvent extends TaskRunEvent {
  type: 'tool_result';
  tool_name?: string;
  tool?: string;
  success?: boolean;
  output?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface StepEvent extends TaskRunEvent {
  type: 'step';
  message?: string;
  iteration?: number;
}

export interface ArtifactCreatedEvent extends TaskRunEvent {
  type: 'artifact_created';
  artifact_id?: string;
  name?: string;
  artifact_type?: string;
}

export interface ErrorEvent extends TaskRunEvent {
  type: 'error';
  message: string;
}
