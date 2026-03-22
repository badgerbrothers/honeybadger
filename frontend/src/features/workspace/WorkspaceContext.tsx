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
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  conversationsApi,
  projectsApi,
  tasksApi,
} from "@/lib/api/endpoints";
import type { ApiConversation, ApiMessage, ApiProject, ApiTask } from "@/lib/api/types";

export type TaskStatus = "schedule" | "queue" | "inprogress" | "done";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
}

export interface Task {
  id: string; // UUID
  title: string; // derived from `goal`
  status: TaskStatus;
  tags: string[];
  agentLabel: string;
  agentInitials: string;
  meta?: string;
  progress?: number;
  highlight?: "info" | "warn";
  raw?: ApiTask;
}

export interface Conversation {
  id: string;
  projectId: string;
  title: string;
  updatedAt: string;
  messages: Message[];
  raw?: ApiConversation;
}

export interface Project {
  id: string;
  name: string;
  updatedAt: string;
  activeRagCollectionId: string | null;
  raw?: ApiProject;
}

interface SendMessageResult {
  taskId: string;
  runId: string;
}

interface WorkspaceState {
  projects: Project[];
  activeProjectId: string | null;
  activeProject: Project | null;

  conversations: Conversation[];
  activeConversations: Conversation[];
  activeConversationId: string | null;
  activeConversation: Conversation | null;

  messageDraft: string;
  setMessageDraft: (value: string) => void;

  selectProject: (id: string) => void;
  createProject: () => Promise<void>;
  renameProject: (id: string, name: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;

  selectConversation: (id: string) => void;
  createConversation: () => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;

  sendMessage: (content: string, opts?: { model?: string | null }) => Promise<SendMessageResult | null>;

  activeTasks: Task[];
  moveTask: (taskId: string, next: TaskStatus) => Promise<void>;
  createTask: (input: string | { title: string; tags?: string[]; meta?: string }) => Promise<void>;
  moveAllQueueToInProgress: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

const LS_ACTIVE_PROJECT = "badgers.workspace.activeProjectId";
const LS_ACTIVE_CONV_BY_PROJECT = "badgers.workspace.activeConversationIdByProject";

function loadString(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

function storeString(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  if (!value) window.localStorage.removeItem(key);
  else window.localStorage.setItem(key, value);
}

function loadJson<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function storeJson(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

function mapProject(p: ApiProject): Project {
  return {
    id: p.id,
    name: p.name,
    updatedAt: p.updated_at,
    activeRagCollectionId: p.active_rag_collection_id,
    raw: p,
  };
}

function mapConversation(c: ApiConversation): Conversation {
  return {
    id: c.id,
    projectId: c.project_id,
    title: c.title,
    updatedAt: c.updated_at,
    messages: [],
    raw: c,
  };
}

function mapMessage(m: ApiMessage): Message {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    createdAt: m.created_at,
  };
}

function statusFromQueueStatus(queueStatus: string): TaskStatus {
  if (queueStatus === "scheduled") return "schedule";
  if (queueStatus === "queued") return "queue";
  if (queueStatus === "in_progress") return "inprogress";
  if (queueStatus === "done") return "done";
  return "schedule";
}

function queueStatusFromStatus(status: TaskStatus) {
  if (status === "schedule") return "scheduled" as const;
  if (status === "queue") return "queued" as const;
  if (status === "inprogress") return "in_progress" as const;
  return "done" as const;
}

function agentInitials(name: string) {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  const parts = trimmed.split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "?";
  const second = parts.length > 1 ? (parts[1]?.[0] ?? "") : "";
  return (first + second).toUpperCase();
}

function mapTask(t: ApiTask): Task {
  const label = t.assigned_agent?.trim() || "Unassigned";
  return {
    id: t.id,
    title: t.goal,
    status: statusFromQueueStatus(t.queue_status),
    tags: t.skill ? [t.skill] : [],
    agentLabel: label,
    agentInitials: agentInitials(label),
    meta: t.model,
    raw: t,
  };
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();

  const [messageDraft, setMessageDraft] = useState("");
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() => loadString(LS_ACTIVE_PROJECT));
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const [activeConversationByProject, setActiveConversationByProject] = useState<Record<string, string>>(
    () => loadJson<Record<string, string>>(LS_ACTIVE_CONV_BY_PROJECT) ?? {},
  );

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: projectsApi.list,
  });

  const projects = useMemo(() => (projectsQuery.data ?? []).map(mapProject), [projectsQuery.data]);

  // Ensure we always have an active project when projects load.
  useEffect(() => {
    if (projects.length === 0) {
      setActiveProjectId(null);
      storeString(LS_ACTIVE_PROJECT, null);
      return;
    }
    if (activeProjectId && projects.some((p) => p.id === activeProjectId)) return;
    const next = projects[0]?.id ?? null;
    setActiveProjectId(next);
    storeString(LS_ACTIVE_PROJECT, next);
  }, [activeProjectId, projects]);

  const activeProject = useMemo(() => {
    if (!activeProjectId) return null;
    return projects.find((p) => p.id === activeProjectId) ?? null;
  }, [projects, activeProjectId]);

  const conversationsQuery = useQuery({
    queryKey: ["conversations", activeProjectId],
    enabled: !!activeProjectId,
    queryFn: () => conversationsApi.list(activeProjectId),
  });

  const conversations = useMemo(
    () => (conversationsQuery.data ?? []).map(mapConversation),
    [conversationsQuery.data],
  );

  const activeConversations = useMemo(() => {
    if (!activeProjectId) return [];
    return conversations.filter((c) => c.projectId === activeProjectId);
  }, [activeProjectId, conversations]);

  // Keep active conversation id in sync when project or conversations change.
  useEffect(() => {
    if (!activeProjectId) {
      setActiveConversationId(null);
      return;
    }

    const preferred = activeConversationByProject[activeProjectId] ?? null;
    const existsPreferred = preferred && activeConversations.some((c) => c.id === preferred);
    const next = (existsPreferred ? preferred : activeConversations[0]?.id) ?? null;
    setActiveConversationId((current) => {
      if (current && activeConversations.some((c) => c.id === current)) return current;
      return next;
    });
  }, [activeConversationByProject, activeConversations, activeProjectId]);

  useEffect(() => {
    storeJson(LS_ACTIVE_CONV_BY_PROJECT, activeConversationByProject);
  }, [activeConversationByProject]);

  useEffect(() => {
    if (!activeProjectId || !activeConversationId) return;
    setActiveConversationByProject((prev) => ({ ...prev, [activeProjectId]: activeConversationId }));
  }, [activeConversationId, activeProjectId]);

  const messagesQuery = useQuery({
    queryKey: ["messages", activeConversationId],
    enabled: !!activeConversationId,
    queryFn: () => conversationsApi.listMessages(activeConversationId!),
  });
  const messages = useMemo(() => (messagesQuery.data ?? []).map(mapMessage), [messagesQuery.data]);

  const activeConversation = useMemo(() => {
    if (!activeConversationId) return null;
    const base = conversations.find((c) => c.id === activeConversationId) ?? null;
    if (!base) return null;
    return { ...base, messages };
  }, [activeConversationId, conversations, messages]);

  const kanbanQuery = useQuery({
    queryKey: ["kanban", activeProjectId],
    enabled: !!activeProjectId,
    queryFn: () => tasksApi.kanban(activeProjectId),
    refetchInterval: 8_000,
  });

  const apiKanban = kanbanQuery.data ?? null;
  const activeTasks = useMemo(() => {
    if (!apiKanban) return [];
    return [
      ...apiKanban.scheduled,
      ...apiKanban.queued,
      ...apiKanban.in_progress,
      ...apiKanban.done,
    ].map(mapTask);
  }, [apiKanban]);

  const selectProject = (id: string) => {
    setActiveProjectId(id);
    storeString(LS_ACTIVE_PROJECT, id);
    setMessageDraft("");
  };

  const selectConversation = (id: string) => {
    setActiveConversationId(id);
    setMessageDraft("");
  };

  const createProject = useCallback(async () => {
    const created = await projectsApi.create({ name: "New project" });
    await qc.invalidateQueries({ queryKey: ["projects"] });
    setActiveProjectId(created.id);
    storeString(LS_ACTIVE_PROJECT, created.id);

    // Ensure the new project has at least one conversation.
    const conv = await conversationsApi.create({
      project_id: created.id,
      title: "New conversation",
    });
    await qc.invalidateQueries({ queryKey: ["conversations", created.id] });
    setActiveConversationId(conv.id);
    setActiveConversationByProject((prev) => ({ ...prev, [created.id]: conv.id }));
  }, [qc]);

  const renameProject = useCallback(async (id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    await projectsApi.update(id, { name: trimmed });
    await qc.invalidateQueries({ queryKey: ["projects"] });
  }, [qc]);

  const deleteProject = useCallback(async (id: string) => {
    await projectsApi.remove(id);
    await qc.invalidateQueries({ queryKey: ["projects"] });
    setActiveConversationByProject((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, [qc]);

  const createConversation = useCallback(async () => {
    if (!activeProjectId) return;
    const created = await conversationsApi.create({
      project_id: activeProjectId,
      title: "New conversation",
    });
    await qc.invalidateQueries({ queryKey: ["conversations", activeProjectId] });
    setActiveConversationId(created.id);
    setActiveConversationByProject((prev) => ({ ...prev, [activeProjectId]: created.id }));
  }, [activeProjectId, qc]);

  const renameConversation = useCallback(async (id: string, title: string) => {
    const trimmed = title.trim();
    if (!trimmed) return;
    await conversationsApi.update(id, { title: trimmed });
    await qc.invalidateQueries({ queryKey: ["conversations", activeProjectId] });
  }, [activeProjectId, qc]);

  const deleteConversation = useCallback(async (id: string) => {
    await conversationsApi.remove(id);
    await qc.invalidateQueries({ queryKey: ["conversations", activeProjectId] });
    await qc.invalidateQueries({ queryKey: ["messages", id] });
    if (activeConversationId === id) setActiveConversationId(null);
  }, [activeConversationId, activeProjectId, qc]);

  const sendMessage = useCallback(
    async (content: string, opts?: { model?: string | null }): Promise<SendMessageResult | null> => {
      const trimmed = content.trim();
      if (!trimmed) return null;
      if (!activeProjectId || !activeConversationId) return null;

      const modelCatalog = await qc.fetchQuery({
        queryKey: ["modelCatalog"],
        queryFn: tasksApi.models,
      });
      const model = (opts?.model?.trim() || modelCatalog.default_model) ?? modelCatalog.default_model;

      await conversationsApi.createMessage(activeConversationId, {
        role: "user",
        content: trimmed,
      });

      // Refresh messages before starting run so UI shows user message immediately.
      await qc.invalidateQueries({ queryKey: ["messages", activeConversationId] });

      const task = await tasksApi.create({
        conversation_id: activeConversationId,
        project_id: activeProjectId,
        goal: trimmed,
        model,
      });

      await qc.invalidateQueries({ queryKey: ["kanban", activeProjectId] });

      const run = await tasksApi.createRun(task.id);
      setMessageDraft("");
      return { taskId: task.id, runId: run.id };
    },
    [activeConversationId, activeProjectId, qc],
  );

  const moveTask = useCallback(
    async (taskId: string, next: TaskStatus) => {
      await tasksApi.setQueueStatus(taskId, queueStatusFromStatus(next));
      if (activeProjectId) await qc.invalidateQueries({ queryKey: ["kanban", activeProjectId] });
    },
    [activeProjectId, qc],
  );

  const createTask = useCallback(
    async (input: string | { title: string; tags?: string[]; meta?: string }) => {
      const title = typeof input === "string" ? input : input.title;
      const trimmed = title.trim();
      if (!trimmed) return;
      if (!activeProjectId || !activeConversationId) return;

      const modelCatalog = await qc.fetchQuery({
        queryKey: ["modelCatalog"],
        queryFn: tasksApi.models,
      });
      const model = modelCatalog.default_model;

      await tasksApi.create({
        conversation_id: activeConversationId,
        project_id: activeProjectId,
        goal: trimmed,
        model,
      });
      if (activeProjectId) await qc.invalidateQueries({ queryKey: ["kanban", activeProjectId] });
    },
    [activeConversationId, activeProjectId, qc],
  );

  const moveAllQueueToInProgress = useCallback(async () => {
    const queued = apiKanban?.queued ?? [];
    if (queued.length === 0) return;
    await Promise.all(queued.map((t) => tasksApi.setQueueStatus(t.id, "in_progress")));
    if (activeProjectId) await qc.invalidateQueries({ queryKey: ["kanban", activeProjectId] });
  }, [activeProjectId, apiKanban, qc]);

  const value: WorkspaceState = {
    projects,
    activeProjectId,
    activeProject,
    conversations,
    activeConversations,
    activeConversationId,
    activeConversation,
    messageDraft,
    setMessageDraft,
    selectProject,
    createProject,
    renameProject,
    deleteProject,
    selectConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    activeTasks,
    moveTask,
    createTask,
    moveAllQueueToInProgress,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
