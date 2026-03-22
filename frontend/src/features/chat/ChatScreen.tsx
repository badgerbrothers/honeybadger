"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { requestForm, requestJson } from "./api";
import styles from "./ChatScreen.module.css";

type MenuTarget = { kind: "project" | "conversation"; id: string } | null;
type RenameTarget = { kind: "project" | "conversation"; id: string; value: string } | null;
type ToolKey = "search" | "code";
const CUSTOM_MODELS_STORAGE_KEY = "badgers.custom.models.v1";

interface Project {
  id: string;
  name: string;
  description: string | null;
  active_rag_collection_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

interface RagCollection {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface ProjectRagBinding {
  project_id: string;
  rag_collection_id: string | null;
  updated_at: string;
}

interface ModelCatalogResponse {
  default_model: string;
  supported_models: string[];
}

interface UploadedFileChip {
  localId: string;
  name: string;
  status: "uploading" | "uploaded" | "failed";
  error?: string;
}

const suggestions = [
  "Summarize current task priorities",
  "Break this requirement into execution steps",
  "Draft a Python script template",
];

export function ChatScreen() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const renameSkipCommitRef = useRef(false);

  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [conversationsByProject, setConversationsByProject] = useState<Record<string, Conversation[]>>({});
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const [menuTarget, setMenuTarget] = useState<MenuTarget>(null);
  const [renameTarget, setRenameTarget] = useState<RenameTarget>(null);
  const [otherProjectsCollapsed, setOtherProjectsCollapsed] = useState(false);

  const [ragCollections, setRagCollections] = useState<RagCollection[]>([]);
  const [selectedRagId, setSelectedRagId] = useState<string | null>(null);
  const [ragMenuOpen, setRagMenuOpen] = useState(false);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [models, setModels] = useState<string[]>(["gpt-5.3-codex"]);
  const [selectedModel, setSelectedModel] = useState("gpt-5.3-codex");
  const [toolState, setToolState] = useState<Record<ToolKey, boolean>>({ search: true, code: false });
  const [uploadedFileChips, setUploadedFileChips] = useState<UploadedFileChip[]>([]);
  const [catalogModels, setCatalogModels] = useState<string[]>([]);

  const selectedProject = useMemo(
    () => projects.find((item) => item.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );
  const selectedRag = useMemo(
    () => ragCollections.find((item) => item.id === selectedRagId) ?? null,
    [ragCollections, selectedRagId],
  );
  const currentProjectConversations = useMemo(() => {
    if (!selectedProjectId) return [];
    return sortConversations(conversationsByProject[selectedProjectId] ?? []);
  }, [conversationsByProject, selectedProjectId]);
  const allProjectsSorted = useMemo(() => sortProjects(projects), [projects]);

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    void loadConversations(selectedProjectId);
    void loadProjectRagBinding(selectedProjectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedConversationId) {
      setMessages([]);
      return;
    }
    void loadMessages(selectedConversationId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedConversationId]);

  useEffect(() => {
    if (!messageListRef.current) return;
    messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (renameTarget) requestAnimationFrame(() => renameInputRef.current?.focus());
  }, [renameTarget]);

  useEffect(() => {
    const onDocumentMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!pageRef.current?.contains(target)) return;
      const element = target as HTMLElement;
      if (!element.closest("[data-menu-panel]") && !element.closest("[data-menu-button]")) setMenuTarget(null);
      if (!element.closest("[data-rag-popover]") && !element.closest("[data-rag-button]")) setRagMenuOpen(false);
      if (!element.closest("[data-model-popover]") && !element.closest("[data-model-button]")) setModelMenuOpen(false);
      if (!element.closest("[data-rename-input]") && renameTarget) setRenameTarget(null);
    };
    document.addEventListener("mousedown", onDocumentMouseDown);
    return () => document.removeEventListener("mousedown", onDocumentMouseDown);
  }, [renameTarget]);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 56), 200);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 200 ? "auto" : "hidden";
  };

  const toggleTool = (key: ToolKey) => setToolState((prev) => ({ ...prev, [key]: !prev[key] }));

  const mergeModels = (baseModels: string[], customModels: string[]) => {
    const seen = new Set<string>();
    const merged: string[] = [];
    for (const item of [...baseModels, ...customModels]) {
      const normalized = item.trim();
      if (!normalized) continue;
      if (seen.has(normalized.toLowerCase())) continue;
      seen.add(normalized.toLowerCase());
      merged.push(normalized);
    }
    return merged;
  };

  const loadCustomModels = () => {
    if (typeof window === "undefined") return [];
    try {
      const raw = window.localStorage.getItem(CUSTOM_MODELS_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
    } catch {
      return [];
    }
  };

  const saveCustomModels = (items: string[]) => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(CUSTOM_MODELS_STORAGE_KEY, JSON.stringify(items));
  };

  const handleCreateProject = async () => {
    setError(null);
    try {
      const project = await requestJson<Project>("/projects/", {
        method: "POST",
        body: JSON.stringify({ name: `New Project ${timestampLabel(new Date())}`, description: null }),
      });
      const conversation = await createConversation(project.id);
      setProjects((prev) => sortProjects([project, ...prev]));
      setConversationsByProject((prev) => ({ ...prev, [project.id]: [conversation] }));
      setSelectedProjectId(project.id);
      setSelectedConversationId(conversation.id);
      setMessages([]);
      setOtherProjectsCollapsed(false);
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const handleSwitchProject = async (projectId: string) => {
    setSelectedProjectId(projectId);
    const existing = sortConversations(conversationsByProject[projectId] ?? []);
    setSelectedConversationId(existing[0]?.id ?? null);
    setMenuTarget(null);
    setRenameTarget(null);
  };

  const handleDeleteProject = async (projectId: string) => {
    setMenuTarget(null);
    setRenameTarget(null);
    setError(null);
    try {
      await requestJson<void>(`/projects/${projectId}`, { method: "DELETE" });
      const nextProjects = sortProjects(projects.filter((item) => item.id !== projectId));
      setProjects(nextProjects);
      setConversationsByProject((prev) => {
        const next = { ...prev };
        delete next[projectId];
        return next;
      });
      if (selectedProjectId === projectId) {
        const nextProject = nextProjects[0] ?? null;
        setSelectedProjectId(nextProject?.id ?? null);
        setSelectedConversationId(null);
        setMessages([]);
      }
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const handleDeleteConversation = async (conversation: Conversation) => {
    setMenuTarget(null);
    setRenameTarget(null);
    setError(null);
    try {
      await requestJson<void>(`/conversations/${conversation.id}`, { method: "DELETE" });
      setConversationsByProject((prev) => {
        const list = prev[conversation.project_id] ?? [];
        return { ...prev, [conversation.project_id]: sortConversations(list.filter((i) => i.id !== conversation.id)) };
      });
      if (selectedConversationId === conversation.id) setSelectedConversationId(null);
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const commitRename = async () => {
    if (!renameTarget) return;
    const nextValue = renameTarget.value.trim();
    const target = renameTarget;
    setRenameTarget(null);
    if (!nextValue) return;
    try {
      if (target.kind === "project") {
        const updated = await requestJson<Project>(`/projects/${target.id}`, {
          method: "PATCH",
          body: JSON.stringify({ name: nextValue }),
        });
        setProjects((prev) => sortProjects(prev.map((item) => (item.id === updated.id ? updated : item))));
      } else {
        const updated = await requestJson<Conversation>(`/conversations/${target.id}`, {
          method: "PATCH",
          body: JSON.stringify({ title: nextValue }),
        });
        setConversationsByProject((prev) => ({
          ...prev,
          [updated.project_id]: sortConversations(
            (prev[updated.project_id] ?? []).map((item) => (item.id === updated.id ? updated : item)),
          ),
        }));
      }
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const handleBindRag = async (ragId: string | null) => {
    if (!selectedProjectId) return;
    try {
      await requestJson<ProjectRagBinding>(`/projects/${selectedProjectId}/rag`, {
        method: "PUT",
        body: JSON.stringify({ rag_collection_id: ragId }),
      });
      setSelectedRagId(ragId);
      setRagMenuOpen(false);
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const handleCreateRag = async () => {
    const name = window.prompt("Create RAG", "")?.trim();
    if (!name) return;
    setError(null);
    try {
      const created = await requestJson<RagCollection>("/rags/", {
        method: "POST",
        body: JSON.stringify({ name, description: null }),
      });
      setRagCollections((prev) => sortRags([created, ...prev]));
      if (selectedProjectId) {
        await handleBindRag(created.id);
      } else {
        setSelectedRagId(created.id);
        setRagMenuOpen(false);
      }
    } catch (requestError) {
      setError(readableError(requestError));
    }
  };

  const handleCreateModel = () => {
    const model = window.prompt("Create model", "")?.trim();
    if (!model) return;
    const merged = mergeModels([model, ...models], []);
    setModels(merged);
    setSelectedModel(model);
    setModelMenuOpen(false);
    const customOnly = merged.filter(
      (item) => !catalogModels.some((catalogItem) => catalogItem.toLowerCase() === item.toLowerCase()),
    );
    saveCustomModels(customOnly);
  };

  const handleToggleRagMenu = async () => {
    setModelMenuOpen(false);
    const nextOpen = !ragMenuOpen;
    setRagMenuOpen(nextOpen);
    if (!nextOpen) return;
    try {
      const ragList = await requestJson<RagCollection[]>("/rags/");
      setRagCollections(sortRags(ragList));
    } catch {
      // Keep current list if refresh fails.
    }
  };

  const handleFilesPicked = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!selectedRagId) {
      setError("Select a RAG collection before uploading files.");
      return;
    }
    for (const file of files) {
      const localId = `${Date.now()}-${Math.random()}`;
      setUploadedFileChips((prev) => [...prev, { localId, name: file.name, status: "uploading" }]);
      const formData = new FormData();
      formData.append("file", file);
      try {
        await requestForm(`/rags/${selectedRagId}/files/upload`, formData);
        setUploadedFileChips((prev) => prev.map((item) => (item.localId === localId ? { ...item, status: "uploaded" } : item)));
      } catch (requestError) {
        const text = readableError(requestError);
        setUploadedFileChips((prev) =>
          prev.map((item) => (item.localId === localId ? { ...item, status: "failed", error: text } : item)),
        );
        setError(text);
      }
    }
  };

  const handleSend = async () => {
    const content = message.trim();
    if (!content || sending || !selectedProjectId) return;
    setSending(true);
    setError(null);
    try {
      let conversationId = selectedConversationId;
      if (!conversationId) {
        const conversation = await createConversation(selectedProjectId);
        setConversationsByProject((prev) => ({
          ...prev,
          [selectedProjectId]: sortConversations([conversation, ...(prev[selectedProjectId] ?? [])]),
        }));
        conversationId = conversation.id;
        setSelectedConversationId(conversation.id);
      }

      setMessages((prev) => [...prev, { id: `temp-${Date.now()}`, conversation_id: conversationId, role: "user", content, created_at: new Date().toISOString() }]);
      setMessage("");
      requestAnimationFrame(adjustTextareaHeight);

      await requestJson(`/conversations/${conversationId}/messages`, { method: "POST", body: JSON.stringify({ role: "user", content }) });
      await requestJson("/tasks/", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, project_id: selectedProjectId, rag_collection_id: selectedRagId, goal: content, model: selectedModel }),
      });
      await loadMessages(conversationId);
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setSending(false);
    }
  };

  async function bootstrap() {
    setLoading(true);
    setError(null);
    try {
      const [projectList, ragList, modelCatalog] = await Promise.all([
        requestJson<Project[]>("/projects/"),
        requestJson<RagCollection[]>("/rags/"),
        requestJson<ModelCatalogResponse>("/tasks/models"),
      ]);
      const sortedProjects = sortProjects(projectList);
      setRagCollections(sortRags(ragList));
      const customModels = loadCustomModels();
      const mergedModels = mergeModels(modelCatalog.supported_models, customModels);
      setCatalogModels(modelCatalog.supported_models);
      setModels(mergedModels);
      setSelectedModel(modelCatalog.default_model);
      if (sortedProjects.length === 0) {
        const project = await requestJson<Project>("/projects/", { method: "POST", body: JSON.stringify({ name: `New Project ${timestampLabel(new Date())}`, description: null }) });
        const conversation = await createConversation(project.id);
        setProjects([project]);
        setConversationsByProject({ [project.id]: [conversation] });
        setSelectedProjectId(project.id);
        setSelectedConversationId(conversation.id);
      } else {
        setProjects(sortedProjects);
        setSelectedProjectId(sortedProjects[0].id);
      }
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function loadConversations(projectId: string) {
    try {
      const result = await requestJson<Conversation[]>(`/conversations/?project_id=${projectId}`);
      const sorted = sortConversations(result);
      setConversationsByProject((prev) => ({ ...prev, [projectId]: sorted }));
      setSelectedConversationId((current) => {
        if (current && sorted.some((item) => item.id === current)) return current;
        return sorted[0]?.id ?? null;
      });
    } catch (requestError) {
      setError(readableError(requestError));
    }
  }

  async function loadProjectRagBinding(projectId: string) {
    try {
      const binding = await requestJson<ProjectRagBinding>(`/projects/${projectId}/rag`);
      setSelectedRagId(binding.rag_collection_id);
    } catch {
      setSelectedRagId(null);
    }
  }

  async function loadMessages(conversationId: string) {
    try {
      const result = await requestJson<Message[]>(`/conversations/${conversationId}/messages`);
      const sorted = [...result].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
      setMessages(sorted);
    } catch (requestError) {
      setError(readableError(requestError));
    }
  }

  async function createConversation(projectId: string) {
    return requestJson<Conversation>("/conversations/", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, title: `New Conversation ${timestampLabel(new Date())}` }),
    });
  }

  return (
    <div className={styles.workspace} ref={pageRef}>
      {sidebarVisible ? (
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <button className={styles.newChatButton} type="button" onClick={() => void handleCreateProject()}>
              + New project
            </button>
            <button className={styles.iconButtonSmall} type="button" onClick={() => setSidebarVisible(false)}>
              {"<<"}
            </button>
          </div>

          <div className={styles.currentProjectHeader}>
            <div className={styles.historySectionTitle}>Current Project</div>
          </div>
          <div className={styles.chatHistory}>
            {!selectedProject ? <div className={styles.emptyHint}>No current project</div> : (
              <div className={styles.historyRow}>
                {renameTarget?.kind === "project" && renameTarget.id === selectedProject.id ? (
                  <input
                    ref={renameInputRef}
                    data-rename-input
                    className={styles.renameInput}
                    value={renameTarget.value}
                    onChange={(event) => setRenameTarget({ kind: "project", id: selectedProject.id, value: event.target.value })}
                    onBlur={() => { if (!renameSkipCommitRef.current) void commitRename(); renameSkipCommitRef.current = false; }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") { event.preventDefault(); void commitRename(); }
                      if (event.key === "Escape") { event.preventDefault(); renameSkipCommitRef.current = true; setRenameTarget(null); }
                    }}
                  />
                ) : (
                  <button className={`${styles.historyItem} ${styles.historyItemActive}`} type="button" onClick={() => void handleSwitchProject(selectedProject.id)}>
                    {selectedProject.name}
                  </button>
                )}
                <div className={styles.itemActions}>
                  <button data-menu-button className={styles.itemMenuButton} type="button" onClick={() => setMenuTarget((current) => current?.kind === "project" && current.id === selectedProject.id ? null : { kind: "project", id: selectedProject.id })}>⋮</button>
                  {menuTarget?.kind === "project" && menuTarget.id === selectedProject.id ? (
                    <div data-menu-panel className={styles.itemMenu}>
                      <button className={styles.itemMenuEntry} type="button" onClick={() => setRenameTarget({ kind: "project", id: selectedProject.id, value: selectedProject.name })}>Rename</button>
                      <button className={`${styles.itemMenuEntry} ${styles.dangerEntry}`} type="button" onClick={() => void handleDeleteProject(selectedProject.id)}>Delete</button>
                    </div>
                  ) : null}
                </div>
              </div>
            )}

            <div className={styles.currentConversationTitle}>Conversations</div>
            {loading ? <div className={styles.emptyHint}>Loading...</div> : null}
            {!loading && currentProjectConversations.length === 0 ? <div className={styles.emptyHint}>No conversation yet</div> : null}
            {currentProjectConversations.map((item) => (
              <div className={styles.historyRow} key={item.id}>
                {renameTarget?.kind === "conversation" && renameTarget.id === item.id ? (
                  <input
                    ref={renameInputRef}
                    data-rename-input
                    className={styles.renameInput}
                    value={renameTarget.value}
                    onChange={(event) => setRenameTarget({ kind: "conversation", id: item.id, value: event.target.value })}
                    onBlur={() => { if (!renameSkipCommitRef.current) void commitRename(); renameSkipCommitRef.current = false; }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") { event.preventDefault(); void commitRename(); }
                      if (event.key === "Escape") { event.preventDefault(); renameSkipCommitRef.current = true; setRenameTarget(null); }
                    }}
                  />
                ) : (
                  <button className={`${styles.historyItem} ${selectedConversationId === item.id ? styles.historyItemActive : ""}`} type="button" onClick={() => { setSelectedConversationId(item.id); setMenuTarget(null); }}>
                    {item.title}
                  </button>
                )}
                <div className={styles.itemActions}>
                  <button data-menu-button className={styles.itemMenuButton} type="button" onClick={() => setMenuTarget((current) => current?.kind === "conversation" && current.id === item.id ? null : { kind: "conversation", id: item.id })}>⋮</button>
                  {menuTarget?.kind === "conversation" && menuTarget.id === item.id ? (
                    <div data-menu-panel className={styles.itemMenu}>
                      <button className={styles.itemMenuEntry} type="button" onClick={() => setRenameTarget({ kind: "conversation", id: item.id, value: item.title })}>Rename</button>
                      <button className={`${styles.itemMenuEntry} ${styles.dangerEntry}`} type="button" onClick={() => void handleDeleteConversation(item)}>Delete</button>
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <button className={styles.sectionToggle} type="button" onClick={() => setOtherProjectsCollapsed((current) => !current)}>
            <span className={styles.historySectionTitle}>Other Projects</span>
            <span className={`${styles.sectionChevron} ${otherProjectsCollapsed ? styles.sectionChevronCollapsed : ""}`}>⌄</span>
          </button>
          {!otherProjectsCollapsed ? (
            <div className={styles.chatHistoryStatic}>
              {allProjectsSorted.map((item) => (
                <div className={styles.historyRow} key={item.id}>
                  <button className={`${styles.historyItem} ${selectedProjectId === item.id ? styles.historyItemActive : ""}`} type="button" onClick={() => void handleSwitchProject(item.id)}>{item.name}</button>
                  <div className={styles.itemActions}>
                    <button data-menu-button className={styles.itemMenuButton} type="button" onClick={() => setMenuTarget((current) => current?.kind === "project" && current.id === item.id ? null : { kind: "project", id: item.id })}>⋮</button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </aside>
      ) : null}

      <main className={styles.mainContent}>
        {!sidebarVisible ? <button className={styles.reopenSidebarButton} type="button" onClick={() => setSidebarVisible(true)}>{">>"}</button> : null}
        <div className={styles.chatScreen}>
          <div className={styles.chatHeader}><div className={styles.chatHeaderText}>{selectedProject ? selectedProject.name : "Chat"}</div></div>
          <div className={styles.chatBody} ref={messageListRef}>
            {error ? <div className={styles.errorBanner}>{error}</div> : null}
            {messages.length === 0 ? (
              <div className={styles.emptyState}>
                <h1 className={styles.greeting}>What can I help you with?</h1>
                <div className={styles.suggestions}>
                  {suggestions.map((item) => (
                    <button className={styles.suggestionCard} key={item} type="button" onClick={() => { setMessage(item); requestAnimationFrame(adjustTextareaHeight); }}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className={styles.messageList}>
                {messages.map((item) => (
                  <div key={item.id} className={`${styles.messageRow} ${item.role === "user" ? styles.messageUser : styles.messageAssistant}`}>
                    <div className={`${styles.messageBubble} ${item.role === "user" ? styles.bubbleUser : styles.bubbleAssistant}`}>{item.content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.composerDock}>
            <div className={styles.inputContainer}>
              {uploadedFileChips.length > 0 ? (
                <div className={styles.fileChips}>
                  {uploadedFileChips.map((chip) => (
                    <div className={`${styles.fileChip} ${chip.status === "failed" ? styles.fileChipError : chip.status === "uploading" ? styles.fileChipUploading : ""}`} key={chip.localId}>
                      <span>{chip.name}</span><span className={styles.fileChipStatus}>{chip.status}</span>
                      <button className={styles.fileChipRemove} type="button" onClick={() => setUploadedFileChips((prev) => prev.filter((item) => item.localId !== chip.localId))}>x</button>
                    </div>
                  ))}
                </div>
              ) : null}

              <textarea
                ref={textareaRef}
                className={styles.inputTextarea}
                placeholder={selectedConversationId ? "Message..." : "Start a conversation..."}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onInput={adjustTextareaHeight}
                onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void handleSend(); } }}
              />

              <div className={styles.inputToolbar}>
                <div className={styles.toolsLeft}>
                  <button className={styles.toolButton} type="button" onClick={() => fileInputRef.current?.click()}>Upload</button>
                  <input ref={fileInputRef} hidden type="file" multiple onChange={(event) => void handleFilesPicked(event)} />
                  <button className={`${styles.toolButton} ${toolState.search ? styles.toolButtonActive : ""}`} type="button" onClick={() => toggleTool("search")}>Search</button>
                  <button className={`${styles.toolButton} ${toolState.code ? styles.toolButtonActive : ""}`} type="button" onClick={() => toggleTool("code")}>Code</button>

                  <div className={styles.popoverWrap}>
                    <button data-rag-button className={styles.toolButton} type="button" onClick={() => void handleToggleRagMenu()}>
                      RAG: {selectedRag ? selectedRag.name : "None"} ⌄
                    </button>
                    {ragMenuOpen ? (
                      <div data-rag-popover className={styles.selectorPopover}>
                        <button className={styles.selectorCreate} type="button" onClick={() => void handleCreateRag()}>
                          + Create RAG
                        </button>
                        <button className={styles.selectorItem} type="button" onClick={() => void handleBindRag(null)}>None</button>
                        {ragCollections.map((item) => (
                          <button key={item.id} className={`${styles.selectorItem} ${selectedRagId === item.id ? styles.selectorItemActive : ""}`} type="button" onClick={() => void handleBindRag(item.id)}>{item.name}</button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className={styles.toolsRight}>
                  <div className={styles.popoverWrap}>
                    <button data-model-button className={styles.toolButton} type="button" onClick={() => { setModelMenuOpen((current) => !current); setRagMenuOpen(false); }}>
                      Model: {selectedModel} ⌄
                    </button>
                    {modelMenuOpen ? (
                      <div data-model-popover className={styles.selectorPopover}>
                        <button className={styles.selectorCreate} type="button" onClick={handleCreateModel}>
                          + Create Model
                        </button>
                        {models.map((item) => (
                          <button key={item} className={`${styles.selectorItem} ${selectedModel === item ? styles.selectorItemActive : ""}`} type="button" onClick={() => { setSelectedModel(item); setModelMenuOpen(false); }}>{item}</button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <button className={styles.sendButton} type="button" onClick={() => void handleSend()} disabled={sending || !message.trim()}>{">"}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function readableError(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Unexpected request error";
}

function timestampLabel(value: Date) {
  const yyyy = value.getFullYear();
  const mm = String(value.getMonth() + 1).padStart(2, "0");
  const dd = String(value.getDate()).padStart(2, "0");
  const hh = String(value.getHours()).padStart(2, "0");
  const mi = String(value.getMinutes()).padStart(2, "0");
  return `${yyyy}${mm}${dd}-${hh}${mi}`;
}

function sortProjects(items: Project[]) {
  return [...items].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
}

function sortConversations(items: Conversation[]) {
  return [...items].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
}

function sortRags(items: RagCollection[]) {
  return [...items].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
}
