"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { projectsApi, ragsApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import type { ApiProjectRagBinding, ApiRagCollection, ApiRagFile } from "@/lib/api/types";
import {
  DEFAULT_MULTIPART_UPLOAD_CONCURRENCY,
  uploadMultipartFileParts,
} from "@/lib/browserMultipartUpload";

export type RagStatus = "ready" | "indexing" | "error";

export interface Rag {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  fileCount: number;
  status: RagStatus;
  raw?: ApiRagCollection;
}

export interface RagFile {
  id: string;
  ragId: string;
  name: string;
  mimeType: string;
  size: number;
  updatedAt: string;
  path: string;
  status: string;
  errorMessage?: string | null;
  uploadProgress: number;
  uploadState: "waiting" | "uploading" | "completed" | "failed";
  indexProgress: number;
  indexState: "waiting" | "pending" | "running" | "completed" | "failed";
  isTransient?: boolean;
  raw?: ApiRagFile;
}

interface RagState {
  rags: Rag[];
  activeRagId: string | null;
  activeRag: Rag | null;

  selectRag: (id: string) => void;
  createRag: (name?: string) => Promise<Rag>;
  renameRag: (id: string, name: string) => Promise<void>;
  deleteRag: (id: string) => Promise<void>;

  ragFilesByRag: Record<string, RagFile[]>;
  activeFileIdByRag: Record<string, string | null>;
  selectFile: (ragId: string, fileId: string) => void;

  uploadFiles: (ragId: string, files: File[]) => Promise<void>;
  bindRagToActiveProject: (ragId: string) => Promise<ApiProjectRagBinding | null>;
}

const RagContext = createContext<RagState | null>(null);

const LS_ACTIVE_PROJECT = "badgers.workspace.activeProjectId";

function loadActiveProjectId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(LS_ACTIVE_PROJECT);
}

function makeClientUploadId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `local-${crypto.randomUUID()}`;
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function indexStateFromStatus(status: string): RagFile["indexState"] {
  if (status === "completed") return "completed";
  if (status === "failed") return "failed";
  if (status === "running") return "running";
  if (status === "pending") return "pending";
  return "waiting";
}

function indexProgressFromStatus(status: string): number {
  if (status === "completed") return 100;
  if (status === "failed") return 72;
  if (status === "running") return 72;
  if (status === "pending") return 12;
  return 0;
}

function mergeServerAndTransientFiles(serverFiles: RagFile[], transientFiles: RagFile[]): RagFile[] {
  const serverIds = new Set(serverFiles.map((file) => file.id));
  const visibleTransient = transientFiles.filter((file) => {
    if (file.uploadState === "failed") return true;
    return !serverIds.has(file.id);
  });
  return [...visibleTransient, ...serverFiles];
}

function mapRag(r: ApiRagCollection): Rag {
  return {
    id: r.id,
    name: r.name,
    description: r.description ?? "",
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    fileCount: 0,
    status: "ready",
    raw: r,
  };
}

function mapRagFile(f: ApiRagFile): RagFile {
  return {
    id: f.id,
    ragId: f.rag_collection_id,
    name: f.file_name,
    mimeType: f.mime_type ?? "application/octet-stream",
    size: f.file_size,
    updatedAt: f.updated_at,
    path: f.storage_path,
    status: f.status,
    errorMessage: f.error_message,
    uploadProgress: 100,
    uploadState: "completed",
    indexProgress: indexProgressFromStatus(f.status),
    indexState: indexStateFromStatus(f.status),
    raw: f,
  };
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function nextNameIndex(base: string, existingNames: string[]): number {
  const normalizedBase = base.trim().toLowerCase();
  const re = new RegExp(`^${escapeRegex(normalizedBase)}(?:\\s+(\\d+))?$`);
  let max = 0;
  for (const raw of existingNames) {
    const normalized = raw.trim().toLowerCase();
    const match = re.exec(normalized);
    if (!match) continue;
    const idx = match[1] ? Number.parseInt(match[1], 10) : 1;
    if (Number.isFinite(idx) && idx > max) max = idx;
  }
  return Math.max(1, max + 1);
}

export function RagProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [activeRagId, setActiveRagId] = useState<string | null>(null);
  const [activeFileIdByRag, setActiveFileIdByRag] = useState<Record<string, string | null>>(
    () => ({}),
  );
  const [transientFilesByRag, setTransientFilesByRag] = useState<Record<string, RagFile[]>>(() => ({}));

  const ragsQuery = useQuery({
    queryKey: ["rags"],
    queryFn: ragsApi.list,
  });

  const rags = useMemo(() => (ragsQuery.data ?? []).map(mapRag), [ragsQuery.data]);

  // Active rag is computed after we derive fileCount/status, see `ragsWithComputedMeta`.

  const ragFileQueries = useQueries({
    queries: rags.map((r) => ({
      queryKey: ["ragFiles", r.id],
      queryFn: () => ragsApi.files(r.id),
      refetchInterval: 8_000,
    })),
  });

  const serverRagFilesByRag = useMemo(() => {
    const out: Record<string, RagFile[]> = {};
    rags.forEach((r, idx) => {
      out[r.id] = (ragFileQueries[idx]?.data ?? []).map(mapRagFile);
    });
    return out;
  }, [ragFileQueries, rags]);

  useEffect(() => {
    setTransientFilesByRag((prev) => {
      let changed = false;
      const next: Record<string, RagFile[]> = {};

      for (const [ragId, transientFiles] of Object.entries(prev)) {
        const serverIds = new Set((serverRagFilesByRag[ragId] ?? []).map((file) => file.id));
        const filtered = transientFiles.filter((file) => {
          if (file.uploadState === "failed") return true;
          return !serverIds.has(file.id);
        });
        if (filtered.length > 0) next[ragId] = filtered;
        if (filtered.length !== transientFiles.length) changed = true;
      }

      return changed ? next : prev;
    });
  }, [serverRagFilesByRag]);

  const ragFilesByRag = useMemo(() => {
    const out: Record<string, RagFile[]> = {};
    const ragIds = new Set([...Object.keys(serverRagFilesByRag), ...Object.keys(transientFilesByRag)]);
    ragIds.forEach((ragId) => {
      out[ragId] = mergeServerAndTransientFiles(
        serverRagFilesByRag[ragId] ?? [],
        transientFilesByRag[ragId] ?? [],
      );
    });
    return out;
  }, [serverRagFilesByRag, transientFilesByRag]);

  const ragsWithComputedMeta = useMemo(() => {
    return rags.map((r) => {
      const files = ragFilesByRag[r.id] ?? [];
      const hasRunning = files.some((f) => f.status === "pending" || f.status === "running");
      const hasFailed = files.some((f) => f.status === "failed");
      const status: RagStatus = hasRunning ? "indexing" : hasFailed ? "error" : "ready";
      return { ...r, fileCount: files.length, status };
    });
  }, [ragFilesByRag, rags]);

  const selectRag = useCallback((id: string) => setActiveRagId(id), []);

  const createRag = useCallback(
    async (name?: string) => {
      const tryCreate = async (candidateName: string) => {
        const created = await ragsApi.create({
          name: candidateName,
          description: "New RAG knowledge set.",
        });
        await qc.invalidateQueries({ queryKey: ["rags"] });
        const mapped = mapRag(created);
        setActiveRagId(mapped.id);
        return mapped;
      };

      const baseName = (name ?? "New RAG").trim() || "New RAG";
      const existingNames = ragsWithComputedMeta.map((r) => r.name);
      const hasExplicitName = !!name?.trim();

      if (hasExplicitName) {
        try {
          return await tryCreate(baseName);
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 409)) throw error;
        }
      }

      const startIndex = nextNameIndex(baseName, existingNames);
      for (let offset = 0; offset < 30; offset += 1) {
        const candidateName = `${baseName} ${startIndex + offset}`;
        try {
          return await tryCreate(candidateName);
        } catch (error) {
          if (error instanceof ApiError && error.status === 409) continue;
          throw error;
        }
      }

      throw new Error("Unable to create unique RAG name. Please retry.");
    },
    [qc, ragsWithComputedMeta],
  );

  const renameRag = useCallback(
    async (id: string, name: string) => {
      const trimmed = name.trim();
      if (!trimmed) return;
      await ragsApi.update(id, { name: trimmed });
      await qc.invalidateQueries({ queryKey: ["rags"] });
    },
    [qc],
  );

  const deleteRag = useCallback(
    async (id: string) => {
      await ragsApi.remove(id);
      await qc.invalidateQueries({ queryKey: ["rags"] });
      await qc.invalidateQueries({ queryKey: ["ragFiles", id] });
      setActiveRagId((cur) => (cur === id ? null : cur));
    },
    [qc],
  );

  const selectFile = useCallback((ragId: string, fileId: string) => {
    setActiveFileIdByRag((prev) => ({ ...prev, [ragId]: fileId }));
  }, []);

  const uploadFiles = useCallback(
    async (ragId: string, files: File[]) => {
      const upsertTransientFile = (fileId: string, updater: (current: RagFile | undefined) => RagFile) => {
        setTransientFilesByRag((prev) => {
          const currentFiles = prev[ragId] ?? [];
          const current = currentFiles.find((item) => item.id === fileId);
          const nextFile = updater(current);
          const nextFiles = current
            ? currentFiles.map((item) => (item.id === fileId ? nextFile : item))
            : [nextFile, ...currentFiles];
          return { ...prev, [ragId]: nextFiles };
        });
      };

      const failures: string[] = [];

      await Promise.all(
        files.map(async (file) => {
          const tempId = makeClientUploadId();
          const now = new Date().toISOString();
          let initialized: Awaited<ReturnType<typeof ragsApi.createMultipartUpload>> | null = null;

          upsertTransientFile(tempId, () => ({
            id: tempId,
            ragId,
            name: file.name,
            mimeType: file.type || "application/octet-stream",
            size: file.size,
            updatedAt: now,
            path: "",
            status: "uploading",
            errorMessage: null,
            uploadProgress: 0,
            uploadState: "uploading",
            indexProgress: 0,
            indexState: "waiting",
            isTransient: true,
          }));

          try {
            initialized = await ragsApi.createMultipartUpload(ragId, {
              file_name: file.name,
              file_size: file.size,
              mime_type: file.type || null,
            });
            const session = initialized;

            upsertTransientFile(tempId, (current) => ({
              ...(current as RagFile),
              path: session.storage_path,
              updatedAt: new Date().toISOString(),
            }));

            const completedParts = await uploadMultipartFileParts({
              file,
              partSize: session.part_size,
              parts: session.parts,
              contentType: file.type || "application/octet-stream",
              concurrency: DEFAULT_MULTIPART_UPLOAD_CONCURRENCY,
              onProgress: (loaded, total) => {
                const progress = total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 100;
                upsertTransientFile(tempId, (current) => ({
                  ...(current as RagFile),
                  uploadProgress: progress,
                  uploadState: "uploading",
                  updatedAt: new Date().toISOString(),
                }));
              },
            });

            const uploaded = await ragsApi.completeMultipartUpload(ragId, {
              upload_session_id: session.upload_session_id,
              parts: completedParts,
            });

            const mapped = mapRagFile(uploaded);
            setTransientFilesByRag((prev) => {
              const currentFiles = prev[ragId] ?? [];
              const nextFiles: RagFile[] = currentFiles.map((item) => {
                if (item.id !== tempId) return item;
                return {
                  ...mapped,
                  uploadProgress: 100,
                  uploadState: "completed",
                  indexProgress: indexProgressFromStatus(uploaded.status),
                  indexState: indexStateFromStatus(uploaded.status),
                  isTransient: true,
                };
              });
              return { ...prev, [ragId]: nextFiles };
            });
          } catch (error) {
            if (initialized?.upload_session_id) {
              try {
                await ragsApi.abortMultipartUpload(ragId, initialized.upload_session_id);
              } catch {
                // best effort cleanup
              }
            }
            const message = error instanceof Error ? error.message : "Upload failed.";
            failures.push(`${file.name}: ${message}`);
            upsertTransientFile(tempId, (current) => {
              const nextFile: RagFile = {
                ...(current as RagFile),
                status: "failed",
                errorMessage: message,
                uploadState: "failed",
                indexState: "waiting",
                updatedAt: new Date().toISOString(),
              };
              return nextFile;
            });
          }
        }),
      );

      await qc.invalidateQueries({ queryKey: ["ragFiles", ragId] });
      await qc.invalidateQueries({ queryKey: ["rags"] });
      if (failures.length > 0) {
        throw new Error(failures.join("\n"));
      }
    },
    [qc],
  );

  const bindRagToActiveProject = useCallback(async (ragId: string) => {
    const projectId = loadActiveProjectId();
    if (!projectId) return null;
    const binding = await projectsApi.putRagBinding(projectId, ragId);
    return binding;
  }, []);

  const value = useMemo<RagState>(() => {
    return {
      rags: ragsWithComputedMeta,
      activeRagId,
      activeRag:
        (activeRagId ? ragsWithComputedMeta.find((x) => x.id === activeRagId) ?? null : null),
      selectRag,
      createRag,
      renameRag,
      deleteRag,
      ragFilesByRag,
      activeFileIdByRag,
      selectFile,
      uploadFiles,
      bindRagToActiveProject,
    };
  }, [
    ragsWithComputedMeta,
    activeRagId,
    selectRag,
    createRag,
    renameRag,
    deleteRag,
    ragFilesByRag,
    activeFileIdByRag,
    selectFile,
    uploadFiles,
    bindRagToActiveProject,
  ]);

  return <RagContext.Provider value={value}>{children}</RagContext.Provider>;
}

export function useRag() {
  const ctx = useContext(RagContext);
  if (!ctx) throw new Error("useRag must be used within RagProvider");
  return ctx;
}

export function ragStatusLabel(status: RagStatus) {
  if (status === "indexing") return "Indexing";
  if (status === "error") return "Error";
  return "Ready";
}
