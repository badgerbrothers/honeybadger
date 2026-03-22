"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

import { projectsApi, ragsApi } from "@/lib/api/endpoints";
import type { ApiProjectRagBinding, ApiRagCollection, ApiRagFile } from "@/lib/api/types";

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
    raw: f,
  };
}

export function RagProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [activeRagId, setActiveRagId] = useState<string | null>(null);
  const [activeFileIdByRag, setActiveFileIdByRag] = useState<Record<string, string | null>>(
    () => ({}),
  );

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

  const ragFilesByRag = useMemo(() => {
    const out: Record<string, RagFile[]> = {};
    rags.forEach((r, idx) => {
      out[r.id] = (ragFileQueries[idx]?.data ?? []).map(mapRagFile);
    });
    return out;
  }, [ragFileQueries, rags]);

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
      const created = await ragsApi.create({
        name: (name ?? "New RAG").trim() || "New RAG",
        description: "New RAG knowledge set.",
      });
      await qc.invalidateQueries({ queryKey: ["rags"] });
      const mapped = mapRag(created);
      setActiveRagId(mapped.id);
      return mapped;
    },
    [qc],
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
      for (const f of files) {
        await ragsApi.uploadFile(ragId, f);
      }
      await qc.invalidateQueries({ queryKey: ["ragFiles", ragId] });
      await qc.invalidateQueries({ queryKey: ["rags"] });
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
