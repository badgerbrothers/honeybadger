export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskRunEvent {
  type: 'status_change' | 'tool_call' | 'tool_result' | 'step' | 'error';
  timestamp?: string;
  data?: any;
}

export interface StatusChangeEvent extends TaskRunEvent {
  type: 'status_change';
  status: TaskStatus;
}

export interface ToolCallEvent extends TaskRunEvent {
  type: 'tool_call';
  tool_name: string;
  arguments: Record<string, any>;
}

export interface ToolResultEvent extends TaskRunEvent {
  type: 'tool_result';
  tool_name: string;
  success: boolean;
  output?: string;
  error?: string;
}

export interface StepEvent extends TaskRunEvent {
  type: 'step';
  message: string;
  iteration?: number;
}

export interface ErrorEvent extends TaskRunEvent {
  type: 'error';
  message: string;
}
