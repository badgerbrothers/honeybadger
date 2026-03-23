export type MessageRole = "user" | "assistant" | "system";
export type TaskQueueStatus = "scheduled" | "queued" | "in_progress" | "done";
export type TaskRunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type RagFileStatus = "pending" | "running" | "completed" | "failed";
export type ApiProviderId = "openai" | "anthropic" | "relay";

export interface ApiProject {
  id: string;
  name: string;
  description: string | null;
  active_rag_collection_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiProjectNode {
  id: string;
  project_id: string;
  parent_id: string | null;
  name: string;
  path: string;
  node_type: string;
  size: number | null;
  created_at: string;
  updated_at: string;
}

export interface ApiProjectFileUploadResponse {
  id: string;
  project_id: string;
  name: string;
  path: string;
  size: number;
  mime_type: string | null;
  created_at: string;
}

export interface ApiConversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ApiTask {
  id: string;
  conversation_id: string;
  project_id: string;
  rag_collection_id: string | null;
  goal: string;
  skill: string | null;
  model: string;
  current_run_id: string | null;
  queue_status: TaskQueueStatus;
  scheduled_at: string | null;
  priority: number;
  assigned_agent: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiTaskRun {
  id: string;
  task_id: string;
  status: TaskRunStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  logs: Array<Record<string, unknown>> | null;
  working_memory: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface ApiTaskKanban {
  scheduled: ApiTask[];
  queued: ApiTask[];
  in_progress: ApiTask[];
  done: ApiTask[];
}

export interface ApiModelCatalog {
  default_model: string;
  supported_models: string[];
}

export interface ApiModelProviderSettings {
  enabled: boolean;
  api_key: string;
  base_url: string;
  main_model: string;
  note: string;
}

export interface ApiModelSettings {
  active_provider: ApiProviderId;
  providers: Record<ApiProviderId, ApiModelProviderSettings>;
  updated_at: string | null;
}

export interface ApiRoleDoc {
  id: string;
  name: string;
  summary: string;
  iconKind: "browser" | "terminal" | "python" | "file";
  markdown: string;
  category: string;
  path: string;
}

export interface ApiSkillDoc {
  id: string;
  name: string;
  summary: string;
  iconKind: "browser" | "terminal" | "python" | "file";
  tools: Array<"browser" | "shell" | "python" | "fileio">;
  markdown: string;
  category: string;
  path: string;
}

export interface ApiArtifact {
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

export interface ApiRagCollection {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiRagFile {
  id: string;
  rag_collection_id: string;
  storage_path: string;
  file_name: string;
  file_size: number;
  mime_type: string | null;
  status: RagFileStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiRagFileUploadResponse extends ApiRagFile {
  index_job_id: string | null;
}

export interface ApiProjectRagBinding {
  project_id: string;
  rag_collection_id: string | null;
  updated_at: string;
}
