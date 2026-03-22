"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { projectsApi, tasksApi } from "@/lib/api/endpoints";
import { useWorkspace } from "@/features/workspace/WorkspaceContext";

const suggestions = [
  { color: "#ea580c", label: "Summarize my recent tasks" },
  { color: "#2563eb", label: "Write a python script" },
  { color: "#16a34a", label: "Analyze data from CSV" },
];

export default function ConversationPage() {
  const router = useRouter();
  const {
    activeProjectId,
    activeConversation,
    sendMessage,
    messageDraft,
    setMessageDraft,
  } = useWorkspace();

  const messages = activeConversation?.messages ?? [];
  const empty = messages.length === 0;
  const canSend = messageDraft.trim().length > 0;

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const modelBtnRef = useRef<HTMLButtonElement | null>(null);
  const ragBtnRef = useRef<HTMLButtonElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [ragMenuOpen, setRagMenuOpen] = useState(false);
  const [ragSources, setRagSources] = useState<string[]>([
    "Project Files",
    "RAG Collection",
    "Web Search (hybrid)",
  ]);
  const [selectedModel, setSelectedModel] = useState<string>("Model");
  const [dropdownPosition, setDropdownPosition] = useState<{ left: number; top: number } | null>(null);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modelCatalogQuery = useQuery({
    queryKey: ["modelCatalog"],
    queryFn: tasksApi.models,
  });

  useEffect(() => {
    if (!modelCatalogQuery.data) return;
    setSelectedModel((prev) => (prev === "Model" ? modelCatalogQuery.data.default_model : prev));
  }, [modelCatalogQuery.data]);

  const models = modelCatalogQuery.data?.supported_models ?? [];

  const placeholder = useMemo(() => {
    return activeConversation ? "Message..." : "Create a conversation to start";
  }, [activeConversation]);

  const adjustTextareaHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(Math.max(el.scrollHeight, 56), 200)}px`;
  };

  useEffect(() => {
    adjustTextareaHeight();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const placeDropdown = (anchorEl: HTMLElement) => {
    const pad = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const width = 260;
    const estimatedHeight = 280;
    const rect = anchorEl.getBoundingClientRect();

    let left = rect.right - width;
    if (left < pad) left = pad;
    if (left + width > vw - pad) left = vw - pad - width;

    let top = rect.top - estimatedHeight - 6;
    if (top < pad) top = rect.bottom + 6;
    if (top + estimatedHeight > vh - pad) top = vh - pad - estimatedHeight;

    setDropdownPosition({ left, top });
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModelMenuOpen(false);
        setRagMenuOpen(false);
      }
    };
    const onMouseDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest("#modelBtn") || target.closest("#ragBtn")) return;
      if (target.closest("#dropdownMenu")) return;
      setModelMenuOpen(false);
      setRagMenuOpen(false);
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
      const res = await sendMessage(messageDraft, { model: selectedModel });
      if (res?.runId) router.push(`/runs/${res.runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  return (
    <main className="main-content">
      <div className="top-bar">
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
      </div>

      <div className="welcome-center">
        <div className="welcome-body">
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
              {messages.map((m) => (
                <div key={m.id} className={`chat-row ${m.role === "user" ? "user" : "assistant"}`}>
                  <div className="chat-bubble">{m.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="composer">
          <div className="input-container">
            <textarea
              ref={textareaRef}
              className="input-textarea"
              placeholder={placeholder}
              value={messageDraft}
              onChange={(event) => setMessageDraft(event.target.value)}
              onInput={adjustTextareaHeight}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void doSend();
                }
              }}
            />

            {error ? (
              <div style={{ padding: "0.5rem 0.75rem", color: "#991b1b", fontSize: "0.9rem" }}>
                {error}
              </div>
            ) : null}

            <div className="input-toolbar">
              <div className="tools-left">
                <input
                  ref={uploadInputRef}
                  type="file"
                  style={{ display: "none" }}
                  onChange={async (event) => {
                    const files = Array.from(event.currentTarget.files ?? []);
                    event.currentTarget.value = "";
                    if (!activeProjectId || files.length === 0) return;
                    setUploading(true);
                    setError(null);
                    try {
                      // Upload one by one to keep it simple and show deterministic behavior.
                      for (const f of files) {
                        await projectsApi.uploadFile(activeProjectId, f);
                      }
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Upload failed");
                    } finally {
                      setUploading(false);
                    }
                  }}
                />
                <button
                  className={`tool-btn ${uploading ? "active" : ""}`}
                  type="button"
                  title="Add attachment"
                  aria-label="Add attachment"
                  onClick={() => uploadInputRef.current?.click()}
                  disabled={!activeProjectId || uploading}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>

                <button className="tool-btn active" type="button" title="Web Search" aria-label="Web search">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                  Search
                </button>

                <button
                  className={`tool-btn ${ragMenuOpen ? "active" : ""}`}
                  id="ragBtn"
                  ref={ragBtnRef}
                  type="button"
                  title="RAG"
                  aria-label="RAG"
                  onClick={() => {
                    setModelMenuOpen(false);
                    const next = !ragMenuOpen;
                    setRagMenuOpen(next);
                    if (next && ragBtnRef.current) placeDropdown(ragBtnRef.current);
                  }}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h10M4 18h16" />
                  </svg>
                  RAG
                </button>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                <button
                  className="tool-btn"
                  id="modelBtn"
                  ref={modelBtnRef}
                  type="button"
                  title="Model"
                  aria-label="Model"
                  onClick={() => {
                    setRagMenuOpen(false);
                    const next = !modelMenuOpen;
                    setModelMenuOpen(next);
                    if (next && modelBtnRef.current) placeDropdown(modelBtnRef.current);
                  }}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5h6M9 19h6M5 9h14M7 15h10" />
                  </svg>
                  <span id="modelBtnLabel">{selectedModel}</span>
                </button>

                <button
                  className="send-btn"
                  title="Send message"
                  aria-label="Send message"
                  type="button"
                  onClick={() => void doSend()}
                  disabled={!canSend || sending}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {(modelMenuOpen || ragMenuOpen) ? (
        <div
          className="dropdown"
          id="dropdownMenu"
          style={dropdownPosition ? { left: dropdownPosition.left, top: dropdownPosition.top } : { right: 24, bottom: 140 }}
        >
          <div className="dropdown-top">
            <div className="dropdown-title" id="dropdownTitle">
              {modelMenuOpen ? "Models" : "RAG"}
            </div>
            <button
              className="dropdown-add"
              type="button"
              id="dropdownAdd"
              title="Add"
              aria-label="Add"
              onClick={() => {
                const label = window.prompt(modelMenuOpen ? "Add model" : "Add RAG source", "")?.trim();
                if (!label) return;
                if (modelMenuOpen) {
                  // Models are backend-driven; allow local temporary add for exploration only.
                  setSelectedModel(label);
                } else setRagSources((prev) => [label, ...prev]);
              }}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 18, height: 18 }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
              </svg>
            </button>
          </div>
          <div className="dropdown-list" id="dropdownList">
            {(modelMenuOpen ? models : ragSources).map((opt) => (
              <button
                key={opt}
                type="button"
                className="dropdown-item"
                onClick={() => {
                  if (modelMenuOpen) setSelectedModel(opt);
                  setModelMenuOpen(false);
                  setRagMenuOpen(false);
                }}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </main>
  );
}

