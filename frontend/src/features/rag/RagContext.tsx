"use client";

import {
  useCallback,
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Rag, RagFile, RagStatus } from "./types";

interface RagState {
  rags: Rag[];
  activeRagId: string | null;
  activeRag: Rag | null;

  selectRag: (id: string) => void;
  createRag: (name?: string) => Rag;
  renameRag: (id: string, name: string) => void;
  deleteRag: (id: string) => void;

  ragFilesByRag: Record<string, RagFile[]>;
  activeFileIdByRag: Record<string, string | null>;
  selectFile: (ragId: string, fileId: string) => void;
}

const RagContext = createContext<RagState | null>(null);

function nowIso() {
  return new Date().toISOString();
}

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(16).slice(2)}-${Date.now()}`;
}

function sortRags(items: Rag[]) {
  return [...items].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
}

function sortFiles(items: RagFile[]) {
  return [...items].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
}

function seedRags(): Rag[] {
  const t = nowIso();
  return sortRags([
    {
      id: "rag-001",
      name: "Policy KB",
      description: "HR + finance policies (grounded answers).",
      createdAt: t,
      updatedAt: t,
      fileCount: 4,
      status: "ready",
    },
    {
      id: "rag-002",
      name: "Product Docs",
      description: "Internal product docs and API guides.",
      createdAt: t,
      updatedAt: t,
      fileCount: 6,
      status: "indexing",
    },
    {
      id: "rag-003",
      name: "Support Knowledge",
      description: "FAQ + known issues + troubleshooting.",
      createdAt: t,
      updatedAt: t,
      fileCount: 3,
      status: "ready",
    },
  ]);
}

function seedFiles(): Record<string, RagFile[]> {
  const t = nowIso();
  const md1 =
    "# Expense Policy (Excerpt)\n\n- Submit expenses within 30 days.\n- Provide receipts for travel and lodging.\n- If evidence is missing, add an explanation.\n";
  const md2 =
    "# Grounding Rules\n\n1. Claims must be supported by retrieved chunks.\n2. If evidence is insufficient, say so.\n3. Provide citations for each conclusion.\n";
  const md3 =
    "# API Quickstart\n\nThis doc explains the request/response format and error handling.\n";

  return {
    "rag-001": sortFiles([
      {
        id: "f-001",
        ragId: "rag-001",
        name: "expense_policy.md",
        mimeType: "text/markdown",
        size: md1.length,
        updatedAt: t,
        path: "/kb/policy/expense_policy.md",
        previewText: md1,
      },
      {
        id: "f-002",
        ragId: "rag-001",
        name: "security_baseline.txt",
        mimeType: "text/plain",
        size: 860,
        updatedAt: t,
        path: "/kb/policy/security_baseline.txt",
        previewText:
          "Passwords must be rotated regularly.\nAccess is least-privilege.\nAudit logs are retained.\n",
      },
      {
        id: "f-003",
        ragId: "rag-001",
        name: "grounding_rules.md",
        mimeType: "text/markdown",
        size: md2.length,
        updatedAt: t,
        path: "/kb/policy/grounding_rules.md",
        previewText: md2,
      },
      {
        id: "f-004",
        ragId: "rag-001",
        name: "travel_policy.pdf",
        mimeType: "application/pdf",
        size: 128_000,
        updatedAt: t,
        path: "/kb/policy/travel_policy.pdf",
      },
    ]),
    "rag-002": sortFiles([
      {
        id: "f-101",
        ragId: "rag-002",
        name: "api_quickstart.md",
        mimeType: "text/markdown",
        size: md3.length,
        updatedAt: t,
        path: "/kb/product/api_quickstart.md",
        previewText: md3,
      },
      {
        id: "f-102",
        ragId: "rag-002",
        name: "architecture_overview.md",
        mimeType: "text/markdown",
        size: 2200,
        updatedAt: t,
        path: "/kb/product/architecture_overview.md",
        previewText:
          "# Architecture Overview\n\nRetrieval: hybrid -> rerank.\nSynthesis: grounded answer with citations.\n",
      },
      {
        id: "f-103",
        ragId: "rag-002",
        name: "release_notes_2026-03.txt",
        mimeType: "text/plain",
        size: 1200,
        updatedAt: t,
        path: "/kb/product/release_notes_2026-03.txt",
        previewText: "2026-03 release notes...\n- Added rerank.\n- Improved chunking.\n",
      },
      {
        id: "f-104",
        ragId: "rag-002",
        name: "openapi.json",
        mimeType: "application/json",
        size: 45_000,
        updatedAt: t,
        path: "/kb/product/openapi.json",
        previewText: "{\n  \"openapi\": \"3.0.0\",\n  \"info\": {\"title\": \"Example\"}\n}\n",
      },
      {
        id: "f-105",
        ragId: "rag-002",
        name: "screenshots.png",
        mimeType: "image/png",
        size: 210_000,
        updatedAt: t,
        path: "/kb/product/screenshots.png",
      },
      {
        id: "f-106",
        ragId: "rag-002",
        name: "faq.md",
        mimeType: "text/markdown",
        size: 980,
        updatedAt: t,
        path: "/kb/product/faq.md",
        previewText: "# FAQ\n\nQ: ...\nA: ...\n",
      },
    ]),
    "rag-003": sortFiles([
      {
        id: "f-201",
        ragId: "rag-003",
        name: "support_faq.md",
        mimeType: "text/markdown",
        size: 1300,
        updatedAt: t,
        path: "/kb/support/support_faq.md",
        previewText: "# Support FAQ\n\n- Reset password\n- Billing issue\n",
      },
      {
        id: "f-202",
        ragId: "rag-003",
        name: "known_issues.txt",
        mimeType: "text/plain",
        size: 980,
        updatedAt: t,
        path: "/kb/support/known_issues.txt",
        previewText: "Known issue: ...\nWorkaround: ...\n",
      },
      {
        id: "f-203",
        ragId: "rag-003",
        name: "troubleshooting.md",
        mimeType: "text/markdown",
        size: 2100,
        updatedAt: t,
        path: "/kb/support/troubleshooting.md",
        previewText: "# Troubleshooting\n\n1. Check logs\n2. Validate config\n",
      },
    ]),
  };
}

export function RagProvider({ children }: { children: ReactNode }) {
  const [rags, setRags] = useState<Rag[]>(() => seedRags());
  const [activeRagId, setActiveRagId] = useState<string | null>(() => "rag-001");
  const [ragFilesByRag, setRagFilesByRag] = useState<Record<string, RagFile[]>>(
    () => seedFiles(),
  );
  const [activeFileIdByRag, setActiveFileIdByRag] = useState<Record<string, string | null>>(
    () => ({ "rag-001": "f-001", "rag-002": "f-101", "rag-003": "f-201" }),
  );

  const activeRag = useMemo(() => {
    if (!activeRagId) return null;
    return rags.find((r) => r.id === activeRagId) ?? null;
  }, [rags, activeRagId]);

  const selectRag = useCallback((id: string) => setActiveRagId(id), []);

  const createRag = useCallback((name?: string) => {
    const t = nowIso();
    const created: Rag = {
      id: uid("rag"),
      name: (name ?? "New RAG").trim() || "New RAG",
      description: "New RAG knowledge set.",
      createdAt: t,
      updatedAt: t,
      fileCount: 0,
      status: "ready",
    };
    setRags((prev) => sortRags([created, ...prev]));
    setRagFilesByRag((prev) => ({ ...prev, [created.id]: [] }));
    setActiveFileIdByRag((prev) => ({ ...prev, [created.id]: null }));
    setActiveRagId(created.id);
    return created;
  }, []);

  const renameRag = useCallback((id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setRags((prev) =>
      sortRags(prev.map((r) => (r.id === id ? { ...r, name: trimmed, updatedAt: nowIso() } : r))),
    );
  }, []);

  const deleteRag = useCallback((id: string) => {
    setRags((prev) => {
      const next = prev.filter((r) => r.id !== id);
      setActiveRagId((current) => {
        if (current !== id) return current;
        return next[0]?.id ?? null;
      });
      return next;
    });
    setRagFilesByRag((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setActiveFileIdByRag((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const selectFile = useCallback((ragId: string, fileId: string) => {
    setActiveFileIdByRag((prev) => ({ ...prev, [ragId]: fileId }));
  }, []);

  // Keep context value stable by including all function references in deps.
  const value = useMemo<RagState>(() => {
    return {
      rags,
      activeRagId,
      activeRag,
      selectRag,
      createRag,
      renameRag,
      deleteRag,
      ragFilesByRag,
      activeFileIdByRag,
      selectFile,
    };
  }, [
    rags,
    activeRagId,
    activeRag,
    selectRag,
    createRag,
    renameRag,
    deleteRag,
    ragFilesByRag,
    activeFileIdByRag,
    selectFile,
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
