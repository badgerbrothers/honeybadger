import { apiFetch } from "./client";
import type {
  ApiArtifact,
  ApiConversation,
  ApiMessage,
  ApiModelCatalog,
  ApiModelSettings,
  ApiProject,
  ApiProjectFileUploadResponse,
  ApiProjectNode,
  ApiProjectRagBinding,
  ApiRagCollection,
  ApiRagFile,
  ApiRagFileUploadResponse,
  ApiRoleDoc,
  ApiSkillDoc,
  ApiTask,
  ApiTaskKanban,
  ApiTaskRun,
  MessageRole,
  TaskQueueStatus,
} from "./types";

export const projectsApi = {
  list: () => apiFetch<ApiProject[]>("/projects/"),
  create: (payload: { name: string; description?: string | null }) =>
    apiFetch<ApiProject>("/projects/", { method: "POST", body: payload }),
  update: (projectId: string, payload: { name?: string; description?: string | null }) =>
    apiFetch<ApiProject>(`/projects/${projectId}`, { method: "PATCH", body: payload }),
  remove: (projectId: string) =>
    apiFetch<void>(`/projects/${projectId}`, { method: "DELETE" }),

  listFiles: (projectId: string) =>
    apiFetch<ApiProjectNode[]>(`/projects/${projectId}/files`),
  uploadFile: (projectId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<ApiProjectFileUploadResponse>(`/projects/${projectId}/files/upload`, {
      method: "POST",
      body: fd,
    });
  },
  deleteFile: (projectId: string, fileId: string) =>
    apiFetch<void>(`/projects/${projectId}/files/${fileId}`, { method: "DELETE" }),

  listArtifacts: (projectId: string) =>
    apiFetch<ApiArtifact[]>(`/projects/${projectId}/artifacts`),

  getRagBinding: (projectId: string) =>
    apiFetch<ApiProjectRagBinding>(`/projects/${projectId}/rag`),
  putRagBinding: (projectId: string, rag_collection_id: string | null) =>
    apiFetch<ApiProjectRagBinding>(`/projects/${projectId}/rag`, {
      method: "PUT",
      body: { rag_collection_id },
    }),
};

export const conversationsApi = {
  list: (projectId?: string | null) =>
    apiFetch<ApiConversation[]>(
      projectId ? `/conversations/?project_id=${encodeURIComponent(projectId)}` : "/conversations/",
    ),
  create: (payload: { project_id: string; title?: string | null }) =>
    apiFetch<ApiConversation>("/conversations/", { method: "POST", body: payload }),
  update: (conversationId: string, payload: { title?: string | null }) =>
    apiFetch<ApiConversation>(`/conversations/${conversationId}`, { method: "PATCH", body: payload }),
  remove: (conversationId: string) =>
    apiFetch<void>(`/conversations/${conversationId}`, { method: "DELETE" }),

  listMessages: (conversationId: string) =>
    apiFetch<ApiMessage[]>(`/conversations/${conversationId}/messages`),
  createMessage: (conversationId: string, payload: { role: MessageRole; content: string }) =>
    apiFetch<ApiMessage>(`/conversations/${conversationId}/messages`, {
      method: "POST",
      body: payload,
    }),
};

export const tasksApi = {
  list: (params: { conversationId?: string | null; projectId?: string | null }) => {
    const qs = new URLSearchParams();
    if (params.conversationId) qs.set("conversation_id", params.conversationId);
    if (params.projectId) qs.set("project_id", params.projectId);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch<ApiTask[]>(`/tasks/${suffix}`);
  },
  create: (payload: {
    conversation_id: string;
    project_id: string;
    goal: string;
    model?: string | null;
    skill?: string | null;
    rag_collection_id?: string | null;
  }) => apiFetch<ApiTask>("/tasks/", { method: "POST", body: payload }),

  models: () => apiFetch<ApiModelCatalog>("/tasks/models"),
  getModelSettings: () => apiFetch<ApiModelSettings>("/tasks/model-settings"),
  putModelSettings: (payload: ApiModelSettings) =>
    apiFetch<ApiModelSettings>("/tasks/model-settings", {
      method: "PUT",
      body: {
        active_provider: payload.active_provider,
        providers: payload.providers,
      },
    }),
  listRoles: () => apiFetch<ApiRoleDoc[]>("/tasks/roles"),
  listSkills: () => apiFetch<ApiSkillDoc[]>("/tasks/skills"),
  kanban: (projectId?: string | null) =>
    apiFetch<ApiTaskKanban>(
      projectId ? `/tasks/kanban?project_id=${encodeURIComponent(projectId)}` : "/tasks/kanban",
    ),
  setQueueStatus: (taskId: string, queueStatus: TaskQueueStatus) =>
    apiFetch<ApiTask>(`/tasks/${taskId}/queue-status?queue_status=${encodeURIComponent(queueStatus)}`, {
      method: "PATCH",
    }),
  runs: (taskId: string) =>
    apiFetch<ApiTaskRun[]>(`/tasks/${taskId}/runs`),

  createRun: (taskId: string) =>
    apiFetch<ApiTaskRun>(`/tasks/${taskId}/runs`, { method: "POST" }),
};

export const runsApi = {
  get: (runId: string) => apiFetch<ApiTaskRun>(`/runs/${runId}`),
  cancel: (runId: string) => apiFetch<ApiTaskRun>(`/runs/${runId}/cancel`, { method: "POST" }),
  artifacts: (runId: string) => apiFetch<ApiArtifact[]>(`/runs/${runId}/artifacts`),
};

export const artifactsApi = {
  downloadBlob: (artifactId: string) =>
    apiFetch<Blob>(`/artifacts/${artifactId}/download`, { responseType: "blob" }),
  saveToProject: (artifactId: string) =>
    apiFetch<any>(`/artifacts/${artifactId}/save-to-project`, { method: "POST" }),
};

export const ragsApi = {
  list: () => apiFetch<ApiRagCollection[]>("/rags/"),
  create: (payload: { name: string; description?: string | null }) =>
    apiFetch<ApiRagCollection>("/rags/", { method: "POST", body: payload }),
  update: (ragId: string, payload: { name?: string | null; description?: string | null }) =>
    apiFetch<ApiRagCollection>(`/rags/${ragId}`, { method: "PATCH", body: payload }),
  remove: (ragId: string) => apiFetch<void>(`/rags/${ragId}`, { method: "DELETE" }),

  files: (ragId: string) => apiFetch<ApiRagFile[]>(`/rags/${ragId}/files`),
  uploadFile: (ragId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<ApiRagFileUploadResponse>(`/rags/${ragId}/files/upload`, {
      method: "POST",
      body: fd,
    });
  },
};
