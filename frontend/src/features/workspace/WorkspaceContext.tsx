"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type TaskStatus = "schedule" | "queue" | "inprogress" | "done";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  tags: string[];
  agentLabel: string;
  agentInitials: string;
  meta?: string;
  progress?: number;
  highlight?: "info" | "warn";
}

export interface Conversation {
  id: string;
  projectId: string;
  title: string;
  updatedAt: string;
  messages: Message[];
}

export interface Project {
  id: string;
  name: string;
  updatedAt: string;
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
  createProject: () => void;
  renameProject: (id: string, name: string) => void;
  deleteProject: (id: string) => void;

  selectConversation: (id: string) => void;
  createConversation: () => void;
  renameConversation: (id: string, title: string) => void;
  deleteConversation: (id: string) => void;

  sendMessage: (content: string) => void;

  tasksByConversation: Record<string, Task[]>;
  activeTasks: Task[];
  moveTask: (taskId: string, next: TaskStatus) => void;
  createTask: (input: string | { title: string; tags?: string[]; meta?: string }) => void;
  moveAllQueueToInProgress: () => void;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

function nowIso() {
  return new Date().toISOString();
}

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(16).slice(2)}-${Date.now()}`;
}

function sortConversations(items: Conversation[]) {
  return [...items].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
}

function sortProjects(items: Project[]) {
  return [...items].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt));
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [messageDraft, setMessageDraft] = useState("");
  const [projects, setProjects] = useState<Project[]>(() => {
    const seed: Project[] = [
      { id: "p-001", name: "Agent Work Platform", updatedAt: nowIso() },
      { id: "p-002", name: "Personal Sandbox", updatedAt: nowIso() },
      { id: "p-003", name: "Client Research", updatedAt: nowIso() },
      { id: "p-004", name: "Ops Automation", updatedAt: nowIso() },
    ];
    return sortProjects(seed);
  });
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() => "p-001");
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    const seed: Conversation[] = [
      { id: "c-001", projectId: "p-001", title: "Conversation 1", updatedAt: nowIso(), messages: [] },
      { id: "c-002", projectId: "p-001", title: "Agent routing rules", updatedAt: nowIso(), messages: [] },
      { id: "c-003", projectId: "p-001", title: "Tools + skills wiring", updatedAt: nowIso(), messages: [] },
      { id: "c-101", projectId: "p-002", title: "Scratchpad", updatedAt: nowIso(), messages: [] },
      { id: "c-201", projectId: "p-003", title: "Pricing notes", updatedAt: nowIso(), messages: [] },
      { id: "c-301", projectId: "p-004", title: "Runbook tasks", updatedAt: nowIso(), messages: [] },
    ];
    return sortConversations(seed);
  });
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => "c-001");
  const [lastConversationByProject, setLastConversationByProject] = useState<Record<string, string>>(() => ({ "p-001": "c-001" }));

  const [tasksByConversation, setTasksByConversation] = useState<Record<string, Task[]>>(() => ({
    "c-001": [
      {
        id: "TSK-892",
        title: "Batch-format Markdown docs",
        status: "schedule",
        tags: ["Docs"],
        agentLabel: "Default agent",
        agentInitials: "M",
        meta: "Waiting for scheduling",
      },
      {
        id: "TSK-890",
        title: "Build Snake game (React + Canvas)",
        status: "inprogress",
        tags: ["Frontend", "Sandbox"],
        agentLabel: "Default agent",
        agentInitials: "M",
        meta: "Executing: implementing UI and styles",
        progress: 45,
      },
    ],
    "c-002": [
      {
        id: "TSK-893",
        title: "Scrape competitor pricing page",
        status: "queue",
        tags: ["Web Search"],
        agentLabel: "Default agent",
        agentInitials: "M",
        meta: "Waiting for scheduling",
      },
      {
        id: "TSK-881",
        title: "Generate project structure diagram",
        status: "done",
        tags: ["Success"],
        agentLabel: "Default agent",
        agentInitials: "M",
        meta: "Completed yesterday",
      },
    ],
    "c-003": [
      {
        id: "TSK-885",
        title: "Auto-reply client email script",
        status: "inprogress",
        tags: ["Python"],
        agentLabel: "Default agent",
        agentInitials: "M",
        meta: "Permission requested: allow reading inbox.csv?",
        highlight: "warn",
      },
    ],
    "c-101": [],
    "c-201": [],
    "c-301": [],
  }));

  const activeProject = useMemo(() => {
    if (!activeProjectId) return null;
    return projects.find((p) => p.id === activeProjectId) ?? null;
  }, [projects, activeProjectId]);

  const activeConversations = useMemo(() => {
    if (!activeProjectId) return [];
    return sortConversations(conversations.filter((c) => c.projectId === activeProjectId));
  }, [conversations, activeProjectId]);

  const activeConversation = useMemo(() => {
    if (!activeConversationId) return null;
    return conversations.find((item) => item.id === activeConversationId) ?? null;
  }, [conversations, activeConversationId]);

  const activeTasks = useMemo(() => {
    if (!activeConversationId) return [];
    return tasksByConversation[activeConversationId] ?? [];
  }, [tasksByConversation, activeConversationId]);

  const selectProject = (id: string) => {
    setActiveProjectId(id);
    setMessageDraft("");
    setActiveConversationId((current) => {
      const last = lastConversationByProject[id];
      const list = sortConversations(conversations.filter((c) => c.projectId === id));
      const next = last && list.some((c) => c.id === last) ? last : list[0]?.id ?? null;
      return next ?? current;
    });
  };

  const createProject = () => {
    const created: Project = { id: uid("p"), name: "New project", updatedAt: nowIso() };
    const createdConversation: Conversation = {
      id: uid("c"),
      projectId: created.id,
      title: "New conversation",
      updatedAt: nowIso(),
      messages: [],
    };
    setProjects((prev) => sortProjects([created, ...prev]));
    setConversations((prev) => sortConversations([createdConversation, ...prev]));
    setTasksByConversation((prev) => ({ ...prev, [createdConversation.id]: [] }));
    setActiveProjectId(created.id);
    setActiveConversationId(createdConversation.id);
    setLastConversationByProject((prev) => ({ ...prev, [created.id]: createdConversation.id }));
    setMessageDraft("");
  };

  const renameProject = (id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setProjects((prev) => sortProjects(prev.map((p) => (p.id === id ? { ...p, name: trimmed, updatedAt: nowIso() } : p))));
  };

  const deleteProject = (id: string) => {
    const removedConversationIds = conversations.filter((c) => c.projectId === id).map((c) => c.id);
    setProjects((prev) => prev.filter((p) => p.id !== id));
    setConversations((prev) => prev.filter((c) => c.projectId !== id));
    setTasksByConversation((prev) => {
      const next = { ...prev };
      for (const cid of removedConversationIds) delete next[cid];
      return next;
    });
    setLastConversationByProject((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setActiveProjectId((current) => {
      if (current !== id) return current;
      const remaining = projects.filter((p) => p.id !== id);
      return remaining[0]?.id ?? null;
    });
    setActiveConversationId((current) => {
      const conv = conversations.find((c) => c.id === current) ?? null;
      if (!conv || conv.projectId !== id) return current;
      return null;
    });
    setMessageDraft("");
  };

  const selectConversation = (id: string) => {
    const found = conversations.find((c) => c.id === id) ?? null;
    if (found) {
      setActiveProjectId(found.projectId);
      setLastConversationByProject((prev) => ({ ...prev, [found.projectId]: id }));
    }
    setActiveConversationId(id);
    setMessageDraft("");
  };

  const createConversation = () => {
    if (!activeProjectId) return;
    const created: Conversation = {
      id: uid("c"),
      projectId: activeProjectId,
      title: `New conversation`,
      updatedAt: nowIso(),
      messages: [],
    };
    setConversations((prev) => sortConversations([created, ...prev]));
    setTasksByConversation((prev) => ({ ...prev, [created.id]: [] }));
    setActiveConversationId(created.id);
    setLastConversationByProject((prev) => ({ ...prev, [activeProjectId]: created.id }));
    setMessageDraft("");
  };

  const renameConversation = (id: string, title: string) => {
    const trimmed = title.trim();
    if (!trimmed) return;
    setConversations((prev) =>
      sortConversations(
        prev.map((item) =>
          item.id === id ? { ...item, title: trimmed, updatedAt: nowIso() } : item,
        ),
      ),
    );
  };

  const deleteConversation = (id: string) => {
    const removing = conversations.find((c) => c.id === id) ?? null;
    setConversations((prev) => prev.filter((item) => item.id !== id));
    setTasksByConversation((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setActiveConversationId((current) => {
      if (current !== id) return current;
      const projectId = removing?.projectId ?? activeProjectId;
      const remaining = projectId
        ? sortConversations(conversations.filter((c) => c.projectId === projectId && c.id !== id))
        : sortConversations(conversations.filter((c) => c.id !== id));
      return remaining[0]?.id ?? null;
    });
    if (removing) {
      setLastConversationByProject((prev) => {
        const next = { ...prev };
        if (next[removing.projectId] === id) delete next[removing.projectId];
        return next;
      });
    }
    setMessageDraft("");
  };

  const sendMessage = (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || !activeConversationId) return;
    const msg: Message = { id: uid("m"), role: "user", content: trimmed, createdAt: nowIso() };
    setConversations((prev) =>
      sortConversations(
        prev.map((item) =>
          item.id === activeConversationId
            ? { ...item, messages: [...item.messages, msg], updatedAt: nowIso() }
            : item,
        ),
      ),
    );
    setMessageDraft("");
  };

  const moveTask = (taskId: string, next: TaskStatus) => {
    if (!activeConversationId) return;
    setTasksByConversation((prev) => {
      const list = prev[activeConversationId] ?? [];
      return {
        ...prev,
        [activeConversationId]: list.map((item) =>
          item.id === taskId ? { ...item, status: next } : item,
        ),
      };
    });
  };

  const createTask = (input: string | { title: string; tags?: string[]; meta?: string }) => {
    const title = typeof input === "string" ? input : input.title;
    const trimmed = title.trim();
    if (!trimmed || !activeConversationId) return;
    const tags =
      typeof input === "string"
        ? []
        : (input.tags ?? []).map((t) => t.trim()).filter(Boolean);
    const meta =
      typeof input === "string" ? undefined : input.meta?.trim() || undefined;
    const task: Task = {
      id: `TSK-${Math.floor(Math.random() * 900) + 100}`,
      title: trimmed,
      status: "schedule",
      tags,
      agentLabel: "Unassigned",
      agentInitials: "?",
      meta,
    };
    setTasksByConversation((prev) => {
      const list = prev[activeConversationId] ?? [];
      return { ...prev, [activeConversationId]: [task, ...list] };
    });
  };

  const moveAllQueueToInProgress = () => {
    if (!activeConversationId) return;
    setTasksByConversation((prev) => {
      const list = prev[activeConversationId] ?? [];
      const schedule = list.filter((t) => t.status === "schedule");
      const queue = list.filter((t) => t.status === "queue");
      const inprogress = list.filter((t) => t.status === "inprogress");
      const done = list.filter((t) => t.status === "done");
      if (queue.length === 0) return prev;
      const movedQueue = queue.map((t) => ({ ...t, status: "inprogress" as const }));
      return {
        ...prev,
        [activeConversationId]: [...schedule, ...inprogress, ...movedQueue, ...done],
      };
    });
  };

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
    tasksByConversation,
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
