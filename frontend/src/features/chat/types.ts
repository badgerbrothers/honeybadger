export type ToolKey = "search" | "code" | "rag";

export type ToolState = Record<ToolKey, boolean>;

export type MenuState =
  | {
      kind: "project" | "conversation";
      id: string;
    }
  | null;

export type RenameState =
  | {
      kind: "project" | "conversation";
      id: string;
      value: string;
    }
  | null;

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

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
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface ModelCatalogResponse {
  default_model: string;
  supported_models: string[];
}

export interface ProjectFileUploadResponse {
  id: string;
  project_id: string;
  name: string;
  path: string;
  size: number;
  mime_type: string | null;
  created_at: string;
}
