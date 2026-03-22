"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ragStatusLabel, useRag } from "./RagContext";

function statusClass(status: string) {
  if (status === "indexing") return "rag-status-dot rag-status-indexing";
  if (status === "error") return "rag-status-dot rag-status-error";
  return "rag-status-dot rag-status-ready";
}

export function RagSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { rags, createRag } = useRag();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rags;
    return rags.filter((r) => {
      const hay = (r.name + " " + r.description).toLowerCase();
      return hay.includes(q);
    });
  }, [rags, query]);

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
            const name = window.prompt("Create RAG name", "New RAG")?.trim();
            if (!name) return;
            const created = await createRag(name);
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
          return (
            <Link
              key={r.id}
              href={`/rag/${r.id}`}
              className={`rag-item ${active ? "active" : ""}`}
              role="listitem"
              onClick={() => {
                // Let the router handle it; this also keeps the app snappy on slow devices.
              }}
            >
              <span className="rag-item-label">
                <div className="rag-item-name">{r.name}</div>
                <div className="rag-item-meta">
                  <span>{r.fileCount} files</span>
                  <span>{ragStatusLabel(r.status)}</span>
                </div>
              </span>
              <span className={statusClass(r.status)} aria-hidden="true" />
            </Link>
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
