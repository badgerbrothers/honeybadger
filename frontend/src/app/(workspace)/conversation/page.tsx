"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth/AuthContext";
import { projectsApi, ragsApi, tasksApi } from "@/lib/api/endpoints";
import { ConversationComposer } from "@/features/conversations/ConversationComposer";
import { ConversationExecutionPanel } from "@/features/conversations/ConversationExecutionPanel";
import { useWorkspace } from "@/features/workspace/WorkspaceContext";
import { connectRunStream, type RunEvent } from "@/lib/ws/runStream";
import {
  describeProjectUploadError,
  validateProjectKnowledgeFiles,
} from "@/lib/fileUpload";
import {
  DEFAULT_MULTIPART_UPLOAD_CONCURRENCY,
  uploadMultipartFileParts,
} from "@/lib/browserMultipartUpload";

const suggestions = [
  { color: "#ea580c", label: "Summarize my recent tasks" },
  { color: "#2563eb", label: "Write a python script" },
  { color: "#16a34a", label: "Analyze data from CSV" },
];

function timestampOf(value: string | null | undefined) {
  if (!value) return 0;
  const result = new Date(value).valueOf();
  return Number.isFinite(result) ? result : 0;
}

function eventKey(event: RunEvent) {
  return `${String(event.type ?? "event")}:${String(event.timestamp ?? "")}:${JSON.stringify(event)}`;
}

export default function ConversationPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { accessToken } = useAuth();
  const { activeProjectId, activeConversation, sendMessage, messageDraft, setMessageDraft } = useWorkspace();

  const messages = activeConversation?.messages ?? [];
  const empty = messages.length === 0;
  const canSend = messageDraft.trim().length > 0;

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const modelBtnRef = useRef<HTMLButtonElement | null>(null);
  const ragBtnRef = useRef<HTMLButtonElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [ragMenuOpen, setRagMenuOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<"model" | "rag" | null>(null);
  const [selectedModel, setSelectedModel] = useState("Model");
  const [selectedRagName, setSelectedRagName] = useState("RAG");
  const [dropdownPosition, setDropdownPosition] = useState<{ left: number; top: number } | null>(null);
  const [dropdownListMaxHeight, setDropdownListMaxHeight] = useState<number | null>(null);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [bindingRag, setBindingRag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamEvents, setStreamEvents] = useState<RunEvent[]>([]);
  const [streamState, setStreamState] = useState<"idle" | "open" | "closed" | "error">("idle");
  const [streamError, setStreamError] = useState<string | null>(null);

  const modelCatalogQuery = useQuery({
    queryKey: ["modelCatalog"],
    queryFn: tasksApi.models,
  });
  const ragsQuery = useQuery({
    queryKey: ["rags"],
    queryFn: ragsApi.list,
  });
  const projectRagBindingQuery = useQuery({
    queryKey: ["projectRagBinding", activeProjectId],
    queryFn: () => projectsApi.getRagBinding(activeProjectId!),
    enabled: !!activeProjectId,
  });
  const conversationTasksQuery = useQuery({
    queryKey: ["conversationTasks", activeConversation?.id],
    queryFn: () => tasksApi.list({ conversationId: activeConversation!.id }),
    enabled: !!activeConversation?.id,
    refetchInterval: 6_000,
  });

  useEffect(() => {
    if (!modelCatalogQuery.data) return;
    setSelectedModel((prev) => (prev === "Model" ? modelCatalogQuery.data.default_model : prev));
  }, [modelCatalogQuery.data]);

  const ragOptions = useMemo(() => ragsQuery.data ?? [], [ragsQuery.data]);

  useEffect(() => {
    if (!activeProjectId) {
      setSelectedRagName("RAG");
      return;
    }
    const bindingId = projectRagBindingQuery.data?.rag_collection_id ?? null;
    const hit = bindingId ? ragOptions.find((item) => item.id === bindingId) : null;
    setSelectedRagName(hit?.name ?? "RAG");
  }, [activeProjectId, projectRagBindingQuery.data, ragOptions]);

  const placeholder = useMemo(() => {
    if (!activeProjectId) return "Message... (first send creates project and conversation)";
    if (!activeConversation) return "Message... (first send creates conversation)";
    return "Message...";
  }, [activeConversation, activeProjectId]);

  const conversationTasks = useMemo(() => {
    const tasks = [...(conversationTasksQuery.data ?? [])];
    tasks.sort((left, right) => {
      const activeDelta = Number(Boolean(right.current_run_id)) - Number(Boolean(left.current_run_id));
      if (activeDelta !== 0) return activeDelta;
      return timestampOf(right.updated_at) - timestampOf(left.updated_at);
    });
    return tasks;
  }, [conversationTasksQuery.data]);

  const selectedTask = conversationTasks[0] ?? null;

  const taskRunsQuery = useQuery({
    queryKey: ["taskRuns", selectedTask?.id],
    queryFn: () => tasksApi.runs(selectedTask!.id),
    enabled: !!selectedTask?.id,
    refetchInterval: 6_000,
  });

  const selectedRun = useMemo(() => {
    if (!selectedTask) return null;
    const runs = taskRunsQuery.data ?? [];
    if (selectedTask.current_run_id) {
      return runs.find((run) => run.id === selectedTask.current_run_id) ?? null;
    }
    return runs[0] ?? null;
  }, [selectedTask, taskRunsQuery.data]);

  const mergedEvents = useMemo(() => {
    const combined = [...(selectedRun?.logs ?? []), ...streamEvents] as RunEvent[];
    const seen = new Set<string>();
    return combined.filter((event) => {
      const key = eventKey(event);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [selectedRun?.logs, streamEvents]);

  useEffect(() => {
    setStreamEvents([]);
    setStreamState("idle");
    setStreamError(null);
  }, [selectedRun?.id]);

  useEffect(() => {
    if (!selectedRun?.id || !accessToken) return;
    if (selectedRun.status !== "pending" && selectedRun.status !== "running") return;
    const stop = connectRunStream(selectedRun.id, accessToken, {
      onOpen: () => {
        setStreamState("open");
        setStreamError(null);
      },
      onEvent: (event) => setStreamEvents((prev) => [...prev, event]),
      onClose: () => setStreamState("closed"),
      onError: () => {
        setStreamState("error");
        setStreamError("Realtime stream connection failed.");
      },
    });
    return () => stop();
  }, [accessToken, selectedRun?.id, selectedRun?.status]);

  const adjustTextareaHeight = () => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(Math.max(element.scrollHeight, 56), 200)}px`;
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, []);

  const placeDropdown = (anchorEl: HTMLElement, menuEl?: HTMLElement | null) => {
    const pad = 8;
    const gap = 6;
    const viewportWidth = window.innerWidth;
    const menuRect = menuEl?.getBoundingClientRect();
    const width = Math.max(260, Math.ceil(menuRect?.width ?? 0) || 260);
    const height = Math.max(180, Math.ceil(menuRect?.height ?? 0) || 280);
    const rect = anchorEl.getBoundingClientRect();
    const availableAbove = Math.max(140, Math.floor(rect.top - pad - gap));
    const renderHeight = Math.min(height, availableAbove);

    let left = rect.right - width;
    if (left < pad) left = pad;
    if (left + width > viewportWidth - pad) left = viewportWidth - pad - width;

    let top = rect.top - renderHeight - gap;
    if (top < pad) top = pad;

    setDropdownPosition({ left, top });
    const headerEl = menuEl?.querySelector(".dropdown-top") as HTMLElement | null;
    const headerHeight = Math.ceil(headerEl?.getBoundingClientRect().height ?? 42);
    setDropdownListMaxHeight(Math.max(96, availableAbove - headerHeight - 8));
  };

  useEffect(() => {
    if (!modelMenuOpen && !ragMenuOpen) return;
    const anchorEl = menuAnchor === "rag" ? ragBtnRef.current : modelBtnRef.current;
    if (!anchorEl) return;
    const reposition = () => placeDropdown(anchorEl, dropdownRef.current);
    const frameId = window.requestAnimationFrame(reposition);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [menuAnchor, modelMenuOpen, ragMenuOpen, ragOptions.length, ragsQuery.isLoading]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModelMenuOpen(false);
        setRagMenuOpen(false);
        setMenuAnchor(null);
      }
    };
    const onMouseDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest("#modelBtn") || target.closest("#ragBtn") || target.closest("#dropdownMenu")) return;
      setModelMenuOpen(false);
      setRagMenuOpen(false);
      setMenuAnchor(null);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, []);

  const doSend = async () => {
    if (!canSend || sending) return;
    setSending(true);
    setError(null);
    try {
      const result = await sendMessage(messageDraft, { model: selectedModel });
      await qc.invalidateQueries({ queryKey: ["conversationTasks"] });
      if (result?.taskId) await qc.invalidateQueries({ queryKey: ["taskRuns", result.taskId] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  const handleUploadFiles = async (files: File[]) => {
    if (!activeProjectId || files.length === 0) return;
    const validationError = validateProjectKnowledgeFiles(files);
    if (validationError) {
      setError(validationError);
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await Promise.all(
        files.map(async (file) => {
          let initialized: Awaited<ReturnType<typeof projectsApi.createMultipartUpload>> | null = null;
          try {
            initialized = await projectsApi.createMultipartUpload(activeProjectId, {
              file_name: file.name,
              file_size: file.size,
              mime_type: file.type || null,
            });
            const session = initialized;
            const parts = await uploadMultipartFileParts({
              file,
              partSize: session.part_size,
              parts: session.parts,
              contentType: file.type || "application/octet-stream",
              concurrency: DEFAULT_MULTIPART_UPLOAD_CONCURRENCY,
            });
            await projectsApi.completeMultipartUpload(activeProjectId, {
              upload_session_id: session.upload_session_id,
              parts,
            });
          } catch (error) {
            if (initialized?.upload_session_id) {
              try {
                await projectsApi.abortMultipartUpload(activeProjectId, initialized.upload_session_id);
              } catch {
                // best effort cleanup
              }
            }
            throw error;
          }
        }),
      );
    } catch (err) {
      setError(describeProjectUploadError(err));
    } finally {
      setUploading(false);
    }
  };

  const applyProjectRagBinding = async (ragId: string | null, ragName?: string) => {
    if (!activeProjectId) {
      setError("Please create or select a project before binding a RAG collection.");
      setModelMenuOpen(false);
      setRagMenuOpen(false);
      setMenuAnchor(null);
      return;
    }
    setBindingRag(true);
    setError(null);
    try {
      await projectsApi.putRagBinding(activeProjectId, ragId);
      setSelectedRagName(ragId ? (ragName ?? "RAG") : "RAG");
      await qc.invalidateQueries({ queryKey: ["projectRagBinding", activeProjectId] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "RAG binding failed");
    } finally {
      setBindingRag(false);
      setModelMenuOpen(false);
      setRagMenuOpen(false);
      setMenuAnchor(null);
    }
  };

  const ragChunkCount = Array.isArray(selectedRun?.working_memory?.rag_context)
    ? selectedRun.working_memory.rag_context.length
    : 0;

  return (
    <main className="main-content conversation-page">
      <div className="top-bar">
        <Link className="top-text-link" href="/settings">
          Settings
        </Link>
        <Link className="top-icon-link" href="/rag" title="RAG" aria-label="RAG">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3l8 4-8 4-8-4 8-4zM4 13l8 4 8-4M4 17l8 4 8-4" />
          </svg>
        </Link>
        <Link className="top-icon-link" href="/tools-skills" title="Tools & Skills" aria-label="Tools and Skills">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.7 6.3a2 2 0 112.8 2.8l-6.9 6.9a2 2 0 11-2.8-2.8l6.9-6.9zM10 19l-5 2 2-5" />
          </svg>
        </Link>
        <Link className="top-icon-link" href="/dashboard" title="Dashboard" aria-label="Dashboard">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4h7v7H4V4zm9 0h7v4h-7V4zM4 13h7v7H4v-7zm9 6h7v-11h-7v11z" />
          </svg>
        </Link>
        <Link className="top-icon-link" href="/settings" title="Model Settings" aria-label="Model settings">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Link>
      </div>

      <div className="conversation-layout">
        <section className="conversation-main-pane">
          <div className={`welcome-center ${empty ? "" : "has-messages"}`}>
            <div className={`welcome-body ${empty ? "" : "has-messages"}`}>
              {empty ? (
                <>
                  <svg className="logo-large" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  <h1 className="greeting">What can I help you with?</h1>
                  <div className="suggestions">
                    {suggestions.map((item) => (
                      <div
                        key={item.label}
                        className="suggestion-card"
                        role="button"
                        tabIndex={0}
                        onClick={() => {
                          setMessageDraft(item.label);
                          requestAnimationFrame(adjustTextareaHeight);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setMessageDraft(item.label);
                            requestAnimationFrame(adjustTextareaHeight);
                          }
                        }}
                      >
                        <svg style={{ color: item.color }} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        {item.label}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="chat-thread" aria-label="Conversation messages">
                  {messages.map((message) => (
                    <div key={message.id} className={`chat-row ${message.role === "user" ? "user" : "assistant"}`}>
                      <div className="chat-bubble">{message.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <ConversationComposer
              empty={empty}
              placeholder={placeholder}
              draft={messageDraft}
              setDraft={setMessageDraft}
              textareaRef={textareaRef}
              onTextareaInput={adjustTextareaHeight}
              onSend={() => void doSend()}
              error={error}
              canUpload={!!activeProjectId}
              uploading={uploading}
              onUploadFiles={handleUploadFiles}
              ragMenuOpen={ragMenuOpen}
              selectedRagName={selectedRagName}
              selectedModel={selectedModel}
              ragBtnRef={ragBtnRef}
              modelBtnRef={modelBtnRef}
              onRagToggle={() => {
                setModelMenuOpen(false);
                const next = !ragMenuOpen;
                setRagMenuOpen(next);
                if (next) {
                  setMenuAnchor("rag");
                  if (ragBtnRef.current) placeDropdown(ragBtnRef.current);
                } else setMenuAnchor(null);
              }}
              onModelToggle={() => {
                setRagMenuOpen(false);
                const next = !modelMenuOpen;
                setModelMenuOpen(next);
                if (next) {
                  setMenuAnchor("model");
                  if (modelBtnRef.current) placeDropdown(modelBtnRef.current);
                } else setMenuAnchor(null);
              }}
              canSend={canSend}
              sending={sending}
            />
          </div>
        </section>

        <ConversationExecutionPanel
          hasConversation={!!activeConversation}
          selectedTask={selectedTask}
          selectedRun={selectedRun}
          mergedEvents={mergedEvents}
          ragChunkCount={ragChunkCount}
          tasksLoading={conversationTasksQuery.isLoading}
          runsLoading={taskRunsQuery.isLoading}
          streamState={streamState}
          streamError={streamError}
        />
      </div>

      {modelMenuOpen || ragMenuOpen ? (
        <div ref={dropdownRef} className="dropdown" id="dropdownMenu" style={dropdownPosition ? { left: dropdownPosition.left, top: dropdownPosition.top } : { right: 24, bottom: 140 }}>
          <div className="dropdown-top">
            <div className="dropdown-title" id="dropdownTitle">{modelMenuOpen ? "Models" : "RAG"}</div>
            <button
              className="dropdown-add"
              type="button"
              id="dropdownAdd"
              title={modelMenuOpen ? "Add model" : "Go to RAG page"}
              aria-label={modelMenuOpen ? "Add model" : "Go to RAG page"}
              onClick={() => {
                if (modelMenuOpen) {
                  const label = window.prompt("Add model", "")?.trim();
                  if (!label) return;
                  setSelectedModel(label);
                  return;
                }
                setModelMenuOpen(false);
                setRagMenuOpen(false);
                setMenuAnchor(null);
                router.push("/rag");
              }}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 18, height: 18 }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
              </svg>
            </button>
          </div>
          <div className="dropdown-list" id="dropdownList" style={dropdownListMaxHeight ? { maxHeight: dropdownListMaxHeight } : undefined}>
            {modelMenuOpen ? (
              (modelCatalogQuery.data?.supported_models ?? []).map((option) => (
                <button key={option} type="button" className="dropdown-item" onClick={() => {
                  setSelectedModel(option);
                  setModelMenuOpen(false);
                  setRagMenuOpen(false);
                  setMenuAnchor(null);
                }}>
                  {option}
                </button>
              ))
            ) : (
              <>
                <button type="button" className="dropdown-item" disabled={bindingRag} onClick={() => void applyProjectRagBinding(null)}>None</button>
                {ragsQuery.isLoading ? <div style={{ padding: "0.55rem 0.6rem", color: "#71717a", fontSize: "0.9rem" }}>Loading RAGs...</div> : null}
                {ragOptions.map((rag) => (
                  <button key={rag.id} type="button" className="dropdown-item" disabled={bindingRag} onClick={() => void applyProjectRagBinding(rag.id, rag.name)}>
                    {rag.name}
                  </button>
                ))}
                {!ragsQuery.isLoading && ragOptions.length === 0 ? (
                  <div style={{ padding: "0.55rem 0.6rem", color: "#71717a", fontSize: "0.9rem" }}>No RAG collections yet. Create one in the RAG page first.</div>
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : null}
    </main>
  );
}
