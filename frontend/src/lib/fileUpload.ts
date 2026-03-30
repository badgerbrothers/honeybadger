import { ApiError } from "@/lib/api/client";

export const KNOWLEDGE_FILE_EXTENSIONS = [
  ".txt",
  ".md",
  ".markdown",
  ".pdf",
  ".json",
  ".csv",
] as const;

export const KNOWLEDGE_FILE_ACCEPT = KNOWLEDGE_FILE_EXTENSIONS.join(",");
export const RAG_KNOWLEDGE_FILE_MAX_SIZE = 10 * 1024 * 1024 * 1024;
export const RAG_PDF_FILE_MAX_SIZE = 10 * 1024 * 1024 * 1024;
export const PROJECT_KNOWLEDGE_FILE_MAX_SIZE = 10 * 1024 * 1024 * 1024;

function extensionOf(name: string) {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function formatLimit(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024) return `${bytes / (1024 * 1024 * 1024)}GB`;
  return `${bytes / (1024 * 1024)}MB`;
}

function extractApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    const trimmed = detail.trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("<!DOCTYPE html") || trimmed.startsWith("<html")) return null;
    return trimmed;
  }

  if (detail && typeof detail === "object") {
    if ("detail" in detail && typeof (detail as { detail?: unknown }).detail === "string") {
      return (detail as { detail: string }).detail;
    }
    if ("message" in detail && typeof (detail as { message?: unknown }).message === "string") {
      return (detail as { message: string }).message;
    }
  }

  return null;
}

function ragLimitForFile(file: File): number {
  return extensionOf(file.name) === ".pdf" ? RAG_PDF_FILE_MAX_SIZE : RAG_KNOWLEDGE_FILE_MAX_SIZE;
}

export function validateRagKnowledgeFiles(files: File[]): string | null {
  for (const file of files) {
    const ext = extensionOf(file.name);
    if (!KNOWLEDGE_FILE_EXTENSIONS.includes(ext as (typeof KNOWLEDGE_FILE_EXTENSIONS)[number])) {
      return `Unsupported file type: ${file.name}. Supported: ${KNOWLEDGE_FILE_EXTENSIONS.join(", ")}.`;
    }
    const limit = ragLimitForFile(file);
    if (file.size > limit) {
      return `File too large: ${file.name}. Maximum size is ${formatLimit(limit)}.`;
    }
  }

  return null;
}

export function validateProjectKnowledgeFiles(files: File[]): string | null {
  for (const file of files) {
    const ext = extensionOf(file.name);
    if (!KNOWLEDGE_FILE_EXTENSIONS.includes(ext as (typeof KNOWLEDGE_FILE_EXTENSIONS)[number])) {
      return `Unsupported file type: ${file.name}. Supported: ${KNOWLEDGE_FILE_EXTENSIONS.join(", ")}.`;
    }
    if (file.size > PROJECT_KNOWLEDGE_FILE_MAX_SIZE) {
      return `File too large: ${file.name}. Maximum size is ${formatLimit(PROJECT_KNOWLEDGE_FILE_MAX_SIZE)}.`;
    }
  }

  return null;
}

export function describeRagUploadError(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = extractApiDetail(error.detail);
    if (detail) return detail;
    if (error.status === 413) {
      return `File too large. Text-like files support up to ${formatLimit(RAG_KNOWLEDGE_FILE_MAX_SIZE)}. PDFs support up to ${formatLimit(RAG_PDF_FILE_MAX_SIZE)}.`;
    }
    if (error.status === 400) {
      return `Unsupported file type. Supported: ${KNOWLEDGE_FILE_EXTENSIONS.join(", ")}.`;
    }
    if (error.status === 503) {
      return "Upload failed. Storage service is unavailable.";
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Upload failed.";
}

export function describeProjectUploadError(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = extractApiDetail(error.detail);
    if (detail) return detail;
    if (error.status === 413) {
      return `File too large. Maximum size is ${formatLimit(PROJECT_KNOWLEDGE_FILE_MAX_SIZE)}.`;
    }
    if (error.status === 400) {
      return `Unsupported file type. Supported: ${KNOWLEDGE_FILE_EXTENSIONS.join(", ")}.`;
    }
    if (error.status === 503) {
      return "Upload failed. Storage service is unavailable.";
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Upload failed.";
}
