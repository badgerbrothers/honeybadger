"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ragStatusLabel, useRag } from "./RagContext";

function statusClass(status: string) {
  if (status === "indexing") return "rag-status-dot rag-status-indexing";
  if (status === "error") return "rag-status-dot rag-status-error";
  return "rag-status-dot rag-status-ready";
}

export function RagSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { rags, createRag, renameRag, deleteRag } = useRag();
  const [query, setQuery] = useState("");
  const [editingRagId, setEditingRagId] = useState<string | null>(null);
  const [editingRagName, setEditingRagName] = useState("");
  const [menuRagId, setMenuRagId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rags;
    return rags.filter((r) => {
      const hay = (r.name + " " + r.description).toLowerCase();
      return hay.includes(q);
    });
  }, [rags, query]);

  const beginRagRename = (ragId: string, currentName: string) => {
    setEditingRagId(ragId);
    setEditingRagName(currentName);
  };

  const finishRagRename = async (ragId: string, currentName: string) => {
    const trimmed = editingRagName.trim();
    setEditingRagId(null);
    if (!trimmed || trimmed === currentName) return;
    await renameRag(ragId, trimmed);
  };

  const closeMenu = () => setMenuRagId(null);

  useEffect(() => {
    if (!menuRagId) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };
    const onMouseDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest(".rag-item-menu-wrap")) return;
      closeMenu();
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [menuRagId]);

  return (
    <aside className="manus-sidebar rag-sidebar" aria-label="RAG list">
      <div className="rag-sidebar-top">
        <div className="rag-sidebar-title">RAG</div>
        <button
          type="button"
          className="rag-icon-btn"
          title="Create RAG"
          aria-label="Create RAG"
          onClick={async () => {
            const created = await createRag();
            setQuery("");
            beginRagRename(created.id, created.name);
            router.push(`/rag/${created.id}`);
          }}
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
          </svg>
        </button>
      </div>

      <div className="rag-search">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search RAGs..."
          aria-label="Search RAGs"
        />
      </div>

      <div className="rag-list" role="list">
        {filtered.map((r) => {
          const active = pathname === `/rag/${r.id}` || pathname.startsWith(`/rag/${r.id}/`);
          if (editingRagId === r.id) {
            return (
              <div key={r.id} className={`rag-item ${active ? "active" : ""}`} role="listitem">
                <span className="rag-item-label">
                  <input
                    className="rag-item-input"
                    value={editingRagName}
                    onClick={(event) => event.stopPropagation()}
                    onChange={(event) => setEditingRagName(event.target.value)}
                    onBlur={() => {
                      void finishRagRename(r.id, r.name);
                    }}
                    onKeyDown={(event) => {
                      event.stopPropagation();
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void finishRagRename(r.id, r.name);
                      } else if (event.key === "Escape") {
                        event.preventDefault();
                        setEditingRagId(null);
                        setEditingRagName("");
                      }
                    }}
                    autoFocus
                    aria-label="Rename RAG"
                  />
                  <div className="rag-item-meta">
                    <span>{r.fileCount} files</span>
                    <span>{ragStatusLabel(r.status)}</span>
                  </div>
                </span>
                <div style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem" }}>
                  <span className={statusClass(r.status)} aria-hidden="true" />
                  <button
                    type="button"
                    className="rag-item-menu-btn"
                    aria-label="RAG menu"
                    title="RAG menu"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setMenuRagId((prev) => (prev === r.id ? null : r.id));
                    }}
                  >
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v.01M12 12v.01M12 18v.01" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          }
          return (
            <div key={r.id} className={`rag-item ${active ? "active" : ""}`} role="listitem">
              <Link href={`/rag/${r.id}`} className="rag-item-main">
                <span className="rag-item-label">
                  <div className="rag-item-name">{r.name}</div>
                  <div className="rag-item-meta">
                    <span>{r.fileCount} files</span>
                    <span>{ragStatusLabel(r.status)}</span>
                  </div>
                </span>
              </Link>
              <div className="rag-item-menu-wrap">
                <span className={statusClass(r.status)} aria-hidden="true" />
                <button
                  type="button"
                  className="rag-item-menu-btn"
                  aria-label="RAG menu"
                  title="RAG menu"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    setMenuRagId((prev) => (prev === r.id ? null : r.id));
                  }}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v.01M12 12v.01M12 18v.01" />
                  </svg>
                </button>
                {menuRagId === r.id ? (
                  <div className="rag-item-menu" role="menu" aria-label="RAG item actions">
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        beginRagRename(r.id, r.name);
                        closeMenu();
                      }}
                    >
                      重命名
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="danger"
                      onClick={async () => {
                        const ok = window.confirm(`Delete RAG: "${r.name}"?`);
                        if (!ok) {
                          closeMenu();
                          return;
                        }
                        await deleteRag(r.id);
                        if (pathname === `/rag/${r.id}` || pathname.startsWith(`/rag/${r.id}/`)) {
                          router.push("/rag");
                        }
                        closeMenu();
                      }}
                    >
                      删除
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
        {filtered.length === 0 ? (
          <div className="rag-muted" style={{ padding: "0.5rem" }}>
            No results.
          </div>
        ) : null}
      </div>
    </aside>
  );
}
