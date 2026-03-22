"use client";

import { useEffect, useMemo } from "react";

export interface NewTaskDraft {
  title: string;
  tags: string;
  meta: string;
}

export interface NewTaskResult {
  title: string;
  tags: string[];
  meta?: string;
}

interface NewTaskModalProps {
  open: boolean;
  draft: NewTaskDraft;
  onChange: (next: NewTaskDraft) => void;
  onCancel: () => void;
  onCreate: (result: NewTaskResult) => void;
}

function parseTags(raw: string) {
  return raw
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function NewTaskModal({
  open,
  draft,
  onChange,
  onCancel,
  onCreate,
}: NewTaskModalProps) {
  const canCreate = useMemo(() => draft.title.trim().length > 0, [draft.title]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="New task"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.28)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1.5rem",
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        style={{
          width: "min(820px, 100%)",
          background: "white",
          border: "1px solid #e5e5e5",
          borderRadius: "1rem",
          boxShadow: "0 24px 70px rgba(0,0,0,0.18)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid #e5e5e5",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            background: "#fafafa",
          }}
        >
          <div style={{ fontSize: "1rem", fontWeight: 700, color: "#111827" }}>
            New Task
          </div>
          <button
            type="button"
            className="icon-btn-small"
            aria-label="Close"
            title="Close"
            onClick={onCancel}
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div style={{ padding: "1.25rem", display: "grid", gap: "1rem" }}>
          <div style={{ display: "grid", gap: "0.35rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#374151" }}>
              Title
            </label>
            <input
              value={draft.title}
              onChange={(e) => onChange({ ...draft, title: e.target.value })}
              placeholder="Task title..."
              style={{
                width: "100%",
                padding: "0.75rem 0.85rem",
                borderRadius: "0.75rem",
                border: "1px solid #d4d4d8",
                outline: "none",
                fontSize: "0.95rem",
              }}
              autoFocus
            />
          </div>

          <div style={{ display: "grid", gap: "0.35rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#374151" }}>
              Tags (comma separated)
            </label>
            <input
              value={draft.tags}
              onChange={(e) => onChange({ ...draft, tags: e.target.value })}
              placeholder="e.g. Frontend, Web Search"
              style={{
                width: "100%",
                padding: "0.75rem 0.85rem",
                borderRadius: "0.75rem",
                border: "1px solid #d4d4d8",
                outline: "none",
                fontSize: "0.95rem",
              }}
            />
          </div>

          <div style={{ display: "grid", gap: "0.35rem" }}>
            <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#374151" }}>
              Notes
            </label>
            <textarea
              value={draft.meta}
              onChange={(e) => onChange({ ...draft, meta: e.target.value })}
              placeholder="Optional notes..."
              style={{
                width: "100%",
                minHeight: "160px",
                padding: "0.75rem 0.85rem",
                borderRadius: "0.75rem",
                border: "1px solid #d4d4d8",
                outline: "none",
                fontSize: "0.95rem",
                resize: "vertical",
              }}
            />
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "0.75rem",
              paddingTop: "0.25rem",
            }}
          >
            <button
              type="button"
              className="btn"
              style={{ background: "white", border: "1px solid #d4d4d8" }}
              onClick={onCancel}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canCreate}
              onClick={() => {
                const title = draft.title.trim();
                if (!title) return;
                const tags = parseTags(draft.tags);
                const meta = draft.meta.trim() ? draft.meta.trim() : undefined;
                onCreate({ title, tags, meta });
              }}
            >
              Create (Schedule)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

