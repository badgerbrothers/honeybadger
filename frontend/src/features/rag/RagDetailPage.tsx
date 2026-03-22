"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { useRag } from "./RagContext";

function bytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function isTextLike(mimeType: string, name: string) {
  if (mimeType.startsWith("text/")) return true;
  const lower = name.toLowerCase();
  return lower.endsWith(".md") || lower.endsWith(".txt") || lower.endsWith(".json");
}

export function RagDetailPage({ ragId }: { ragId: string }) {
  const { rags, selectRag, ragFilesByRag, activeFileIdByRag, selectFile } = useRag();
  const [previewFileId, setPreviewFileId] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    selectRag(ragId);
  }, [ragId, selectRag]);

  const rag = useMemo(() => rags.find((r) => r.id === ragId) ?? null, [rags, ragId]);
  const files = ragFilesByRag[ragId] ?? [];
  const activeFileId = activeFileIdByRag[ragId] ?? null;
  const activeFile = files.find((f) => f.id === activeFileId) ?? files[0] ?? null;
  const previewFile = files.find((f) => f.id === previewFileId) ?? null;

  useEffect(() => {
    if (!activeFile) return;
    if (activeFileId === activeFile.id) return;
    selectFile(ragId, activeFile.id);
  }, [activeFile, activeFileId, ragId, selectFile]);

  useEffect(() => {
    if (!previewFileId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPreviewFileId(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [previewFileId]);

  if (!rag) {
    return (
      <>
        <header className="manus-page-header">
          <h1 className="manus-page-title">RAG Not Found</h1>
          <div />
        </header>
        <div className="manus-content-area">
          <div className="rag-muted">This RAG id does not exist in local mock data.</div>
        </div>
      </>
    );
  }

  return (
    <>
      <header className="manus-page-header">
        <h1 className="manus-page-title" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontSize: "1.25rem" }}>
          {rag.name}
        </h1>
        <div style={{ color: "#71717a", fontSize: "0.9rem" }}>{files.length} files</div>
      </header>

      <div className="manus-content-area fluid">
        <div className="rag-detail-grid">
          <div className="rag-card">
            <div className="rag-card-header">
              <div className="rag-card-title">Overview</div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <button
                  className="manus-btn"
                  type="button"
                  title="Upload"
                  aria-label="Upload"
                  onClick={() => uploadInputRef.current?.click()}
                >
                  Upload
                </button>
                <button className="manus-btn" type="button" title="Refresh (mock)" aria-label="Refresh (mock)">
                  Refresh
                </button>
              </div>
            </div>
            <div className="rag-card-body">
              <input
                ref={uploadInputRef}
                type="file"
                multiple
                style={{ display: "none" }}
                onChange={(event) => {
                  // Local mock phase: only open system file picker for now.
                  // Reset value so selecting the same file again still triggers onChange.
                  event.currentTarget.value = "";
                }}
              />
              <div className="rag-muted" style={{ marginBottom: "0.9rem" }}>{rag.description}</div>
              <div className="rag-overview-kv">
                <div className="rag-overview-k">Status</div>
                <div className="rag-overview-v">{rag.status}</div>
                <div className="rag-overview-k">Files</div>
                <div className="rag-overview-v">{files.length}</div>
                <div className="rag-overview-k">Updated</div>
                <div className="rag-overview-v">{new Date(rag.updatedAt).toLocaleString()}</div>
              </div>
            </div>
          </div>

          <div className="rag-card">
            <div className="rag-card-header">
              <div className="rag-card-title">Files</div>
              <div style={{ color: "#71717a", fontSize: "0.85rem" }}>{files.length} items</div>
            </div>
            <div className="rag-card-body">
              {files.length === 0 ? (
                <div className="rag-muted">No files yet.</div>
              ) : (
                files.map((f) => {
                  const active = activeFile?.id === f.id;
                  return (
                    <div
                      key={f.id}
                      className={`rag-file-row ${active ? "active" : ""}`}
                      role="group"
                      aria-label={`File ${f.name}`}
                    >
                      <div
                        className="rag-file-main"
                        role="button"
                        tabIndex={0}
                        onClick={() => selectFile(ragId, f.id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectFile(ragId, f.id);
                          }
                        }}
                      >
                        <div className="rag-file-name">{f.name}</div>
                        <div className="rag-file-meta">
                          <span>{bytes(f.size)}</span>
                          <span>{new Date(f.updatedAt).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="rag-file-actions">
                        <button
                          type="button"
                          className="manus-btn"
                          aria-label={`View ${f.name}`}
                          title="View"
                          onClick={() => setPreviewFileId(f.id)}
                        >
                          查看
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {previewFile ? (
        <div
          className="rag-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="File preview dialog"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setPreviewFileId(null);
          }}
        >
          <div className="rag-modal">
            <div className="rag-modal-header">
              <div style={{ minWidth: 0 }}>
                <div className="rag-modal-title">{previewFile.name}</div>
                <div className="rag-muted" style={{ fontSize: "0.85rem" }}>{previewFile.mimeType}</div>
              </div>
              <button
                type="button"
                className="rag-icon-btn"
                aria-label="Close preview"
                title="Close"
                onClick={() => setPreviewFileId(null)}
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 6l12 12M18 6l-12 12" />
                </svg>
              </button>
            </div>
            <div className="rag-modal-body">
              {isTextLike(previewFile.mimeType, previewFile.name) ? (
                <pre className="rag-preview-pre">{previewFile.previewText ?? "No preview text in mock."}</pre>
              ) : (
                <div className="rag-muted">
                  This file type is not previewed in the UI right now. Path:{" "}
                  <strong>{previewFile.path}</strong>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
