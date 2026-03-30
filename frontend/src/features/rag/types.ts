export type RagStatus = "ready" | "indexing" | "error";

export interface Rag {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  fileCount: number;
  status: RagStatus;
}

export interface RagFile {
  id: string;
  ragId: string;
  name: string;
  mimeType: string;
  size: number;
  updatedAt: string;
  path: string;
  status?: string;
  errorMessage?: string | null;
  uploadProgress?: number;
  uploadState?: "waiting" | "uploading" | "completed" | "failed";
  indexProgress?: number;
  indexState?: "waiting" | "pending" | "running" | "completed" | "failed";
  isTransient?: boolean;
  previewText?: string;
}
