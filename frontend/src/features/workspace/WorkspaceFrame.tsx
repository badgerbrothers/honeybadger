"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { RequireAuth } from "@/lib/auth/RequireAuth";

import { WorkspaceProvider, useWorkspace } from "./WorkspaceContext";

type MenuTarget = { kind: "project" | "conversation"; id: string } | null;
type MenuPosition = { left: number; top: number } | null;

function WorkspaceSidebar() {
  const {
    projects,
    activeProjectId,
    activeProject,
    selectProject,
    createProject,
    renameProject,
    deleteProject,
    activeConversations,
    activeConversationId,
    selectConversation,
    createConversation,
    renameConversation,
    deleteConversation,
  } =
    useWorkspace();

  const [collapsed, setCollapsed] = useState(false);
  const [projectsCollapsed, setProjectsCollapsed] = useState(false);
  const [menuTarget, setMenuTarget] = useState<MenuTarget>(null);
  const [menuPosition, setMenuPosition] = useState<MenuPosition>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const activeProjectName = useMemo(() => {
    return activeProject?.name ?? "Untitled";
  }, [activeProject]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuTarget(null);
    };
    const onMouseDown = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest(".item-menu-btn")) return;
      if (menuRef.current && menuRef.current.contains(target)) return;
      setMenuTarget(null);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, []);

  const placePopover = (el: HTMLElement, anchorRect: DOMRect) => {
    const pad = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    el.style.left = "0px";
    el.style.top = "0px";

    const rect = el.getBoundingClientRect();
    let left = anchorRect.right - rect.width;
    if (left < pad) left = pad;
    if (left + rect.width > vw - pad) left = vw - pad - rect.width;

    let top = anchorRect.bottom + 6;
    if (top + rect.height > vh - pad) top = anchorRect.top - rect.height - 6;
    if (top < pad) top = pad;
    if (top + rect.height > vh - pad) top = vh - pad - rect.height;

    return { left, top };
  };

  const openItemMenu = (buttonEl: HTMLElement, target: MenuTarget) => {
    const rect = buttonEl.getBoundingClientRect();
    setMenuTarget(target);
    const fake = document.createElement("div");
    fake.className = "context-menu";
    fake.style.position = "fixed";
    fake.style.left = "-9999px";
    fake.style.top = "-9999px";
    fake.style.visibility = "hidden";
    fake.innerHTML = "<button></button><button></button>";
    document.body.appendChild(fake);
    const pos = placePopover(fake, rect);
    document.body.removeChild(fake);
    setMenuPosition(pos);
  };

  return (
    <>
      {!collapsed ? null : (
        <button
          type="button"
          className="icon-btn-small sidebar-reopen"
          aria-label="Reopen sidebar"
          title="Reopen sidebar"
          onClick={() => setCollapsed(false)}
        >
          <span style={{ fontWeight: 700 }}>&gt;&gt;</span>
        </button>
      )}

      <aside className={`sidebar ${collapsed ? "is-collapsed" : ""}`}>
        <div className="sidebar-header">
          <button className="new-project-btn" type="button" aria-label="New project" onClick={createProject}>
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            New project
          </button>
          <button
            className="icon-btn-small"
            type="button"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            onClick={() => setCollapsed(true)}
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>

        <div className="section-row">
          <div className="section-title">Current project</div>
        </div>
        <div className="project-pill" id="currentProjectName" title="Current project">
          {activeProjectName}
        </div>

        <div className="section-row">
          <div className="section-title">Conversations</div>
          <div className="header-actions">
            <button className="header-plus-btn" type="button" title="New conversation" aria-label="New conversation" onClick={createConversation}>
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 18, height: 18 }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v14m7-7H5" />
              </svg>
            </button>
          </div>
        </div>

        <div className="chat-history" id="conversationList" role="list">
          {activeConversations.map((c) => {
            const active = c.id === activeConversationId;
            return (
              <div
                key={c.id}
                className={`history-item conversation-item ${active ? "active" : ""}`}
                role="listitem"
                tabIndex={0}
                data-kind="conversation"
                onClick={() => selectConversation(c.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    selectConversation(c.id);
                  }
                }}
              >
                <span className="item-label">{c.title}</span>
                <button
                  className="item-menu-btn"
                  type="button"
                  aria-label="Conversation menu"
                  title="Menu"
                  onClick={(event) => {
                    event.stopPropagation();
                    const btn = event.currentTarget as unknown as HTMLElement;
                    openItemMenu(btn, { kind: "conversation", id: c.id });
                  }}
                >
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 18, height: 18 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v.01M12 12v.01M12 18v.01" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>

        <div className="section-row">
          <div className="section-title">Previous days</div>
          <button
            className="section-toggle"
            type="button"
            aria-expanded={!projectsCollapsed}
            title="Collapse/expand"
            aria-label="Collapse or expand projects"
            onClick={() => setProjectsCollapsed((v) => !v)}
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        {!projectsCollapsed ? (
          <div className="chat-history" id="projectsList" style={{ flexGrow: 0 }} role="list">
            {projects.map((p) => {
              const active = p.id === activeProjectId;
              return (
                <div
                  key={p.id}
                  className={`history-item ${active ? "active" : ""}`}
                  role="listitem"
                  tabIndex={0}
                  data-kind="project"
                  onClick={() => selectProject(p.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      selectProject(p.id);
                    }
                  }}
                >
                  <span className="item-label">{p.name}</span>
                  <button
                    className="item-menu-btn"
                    type="button"
                    aria-label="Project menu"
                    title="Menu"
                    onClick={(event) => {
                      event.stopPropagation();
                      const btn = event.currentTarget as unknown as HTMLElement;
                      openItemMenu(btn, { kind: "project", id: p.id });
                    }}
                  >
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true" style={{ width: 18, height: 18 }}>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v.01M12 12v.01M12 18v.01" />
                    </svg>
                  </button>
                </div>
              );
            })}
          </div>
        ) : null}

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar-small">U</div>
            <span style={{ fontSize: "0.9rem", fontWeight: 500 }}>User Workspace</span>
          </div>
        </div>
      </aside>

      {menuTarget && menuPosition ? (
        <div
          ref={menuRef}
          className="context-menu"
          style={{ left: menuPosition.left, top: menuPosition.top }}
        >
          <button
            type="button"
            data-action="rename"
            onClick={() => {
              if (menuTarget.kind === "project") {
                const p = projects.find((item) => item.id === menuTarget.id);
                if (!p) return;
                const next = window.prompt("Rename project", p.name);
                if (next && next.trim()) renameProject(p.id, next);
              } else {
                const c = activeConversations.find((item) => item.id === menuTarget.id) ?? null;
                if (!c) return;
                const next = window.prompt("Rename conversation", c.title);
                if (next && next.trim()) renameConversation(c.id, next);
              }
              setMenuTarget(null);
            }}
          >
            <span>Rename</span>
            <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>R</span>
          </button>
          <button
            type="button"
            className="danger"
            data-action="delete"
            onClick={() => {
              if (menuTarget.kind === "project") {
                const p = projects.find((item) => item.id === menuTarget.id);
                if (!p) return;
                const ok = window.confirm(`Delete project: "${p.name}"?`);
                if (ok) deleteProject(p.id);
              } else {
                const c = activeConversations.find((item) => item.id === menuTarget.id) ?? null;
                if (!c) return;
                const ok = window.confirm(`Delete conversation: "${c.title}"?`);
                if (ok) deleteConversation(c.id);
              }
              setMenuTarget(null);
            }}
          >
            <span>Delete</span>
            <span style={{ color: "inherit", fontSize: "0.8rem" }}>Del</span>
          </button>
        </div>
      ) : null}
    </>
  );
}

function WorkspaceChrome({ children }: { children: ReactNode }) {
  return (
    <>
      <WorkspaceSidebar />
      {children}
    </>
  );
}

export function WorkspaceFrame({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <WorkspaceProvider>
        <WorkspaceChrome>{children}</WorkspaceChrome>
      </WorkspaceProvider>
    </RequireAuth>
  );
}
