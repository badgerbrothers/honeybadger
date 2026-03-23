"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import type { SkillTool } from "@/features/workspace/skills";
import type { WorkspaceRoleDoc } from "@/features/workspace/roles";
import { tasksApi } from "@/lib/api/endpoints";

type ToolId = "browser" | "shell" | "python" | "fileio";
type IconKind = "browser" | "terminal" | "python" | "file";
type TabId = "tools" | "skills" | "roles";
type DocKind = "skill" | "role";

type ToolItem = {
  id: ToolId;
  name: string;
  title: string;
  description: string;
  status: string;
  iconKind: IconKind;
  actionLabel: string;
};

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "tools", label: "工具 (Tools)" },
  { id: "skills", label: "技能 (Skills)" },
  { id: "roles", label: "角色 (Roles)" },
];

const toolItems: ToolItem[] = [
  {
    id: "browser",
    name: "网络浏览器 (Web Browser)",
    title: "Browser",
    description:
      "赋予 Agent 搜索互联网、访问特定 URL 并提取网页内容的能力，用于获取最新信息或查阅文档。",
    status: "✓ 运行正常",
    iconKind: "browser",
    actionLabel: "设置",
  },
  {
    id: "shell",
    name: "终端命令行 (Shell)",
    title: "Shell",
    description:
      "允许 Agent 在安全的沙盒环境中执行 Shell 命令。适用于项目构建、依赖安装或系统状态查询。",
    status: "沙盒环境: Docker Base",
    iconKind: "terminal",
    actionLabel: "设置",
  },
  {
    id: "python",
    name: "Python 代码执行",
    title: "Python",
    description:
      "Agent 可以编写并直接运行 Python 脚本，常用于数据分析、图表生成、复杂计算或自动化任务。",
    status: "Python 3.11",
    iconKind: "python",
    actionLabel: "设置",
  },
  {
    id: "fileio",
    name: "文件读写 (File I/O)",
    title: "File I/O",
    description:
      "允许 Agent 读取本地工作区的文件内容，进行编辑、替换或创建新文件，是协助编写代码的核心能力。",
    status: "已授权工作区目录",
    iconKind: "file",
    actionLabel: "权限设置",
  },
];

const skillToolLabel: Record<string, string> = {
  browser: "Web Browser",
  shell: "Shell",
  python: "Python",
  fileio: "File I/O",
};

type SkillDoc = {
  id: string;
  name: string;
  summary: string;
  iconKind: IconKind;
  tools: SkillTool[];
  markdown: string;
};

type PreviewDoc = {
  kind: DocKind;
  id: string;
  name: string;
  markdown: string;
};

function ToolIcon({ kind }: { kind: IconKind }) {
  if (kind === "browser") {
    return (
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
        />
      </svg>
    );
  }

  if (kind === "terminal") {
    return (
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
        />
      </svg>
    );
  }

  if (kind === "python") {
    return (
      <svg fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M14.228 16.591h-4.456v-1.74h4.456v1.74zm0-3.136h-4.456v-1.739h4.456v1.739zm3.56-4.665c0-1.741-1.36-3.155-3.036-3.155h-5.504c-1.676 0-3.036 1.414-3.036 3.155v2.859c0 1.742 1.36 3.156 3.036 3.156h5.504c1.676 0 3.036-1.414 3.036-3.156v-2.859zm-1.5 2.859c0 .878-.731 1.591-1.631 1.591H9.349c-.9 0-1.631-.713-1.631-1.591v-2.859c0-.877.731-1.591 1.631-1.591h5.808c.9 0 1.631.714 1.631 1.591v2.859z" />
      </svg>
    );
  }

  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

export default function ToolsSkillsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("tools");
  const [toolEnabled, setToolEnabled] = useState<Record<ToolId, boolean>>({
    browser: true,
    shell: true,
    python: true,
    fileio: true,
  });
  const [catalogSkills, setCatalogSkills] = useState<SkillDoc[]>([]);
  const [customSkills, setCustomSkills] = useState<SkillDoc[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [skillsLoadError, setSkillsLoadError] = useState<string | null>(null);
  const [catalogRoles, setCatalogRoles] = useState<WorkspaceRoleDoc[]>([]);
  const [customRoles, setCustomRoles] = useState<WorkspaceRoleDoc[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesLoadError, setRolesLoadError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<PreviewDoc | null>(null);
  const importSkillsRef = useRef<HTMLInputElement | null>(null);
  const importRolesRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!previewDoc) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPreviewDoc(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [previewDoc]);

  useEffect(() => {
    let cancelled = false;
    const loadSkills = async () => {
      setSkillsLoading(true);
      setSkillsLoadError(null);
      try {
        const skills = await tasksApi.listSkills();
        if (!cancelled) setCatalogSkills(skills);
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Failed to load skills catalog";
        setCatalogSkills([]);
        setSkillsLoadError(message);
      } finally {
        if (!cancelled) setSkillsLoading(false);
      }
    };

    void loadSkills();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadRoles = async () => {
      setRolesLoading(true);
      setRolesLoadError(null);
      try {
        const roles = await tasksApi.listRoles();
        if (!cancelled) setCatalogRoles(roles);
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Failed to load roles catalog";
        setCatalogRoles([]);
        setRolesLoadError(message);
      } finally {
        if (!cancelled) setRolesLoading(false);
      }
    };

    void loadRoles();
    return () => {
      cancelled = true;
    };
  }, []);

  const allSkills: SkillDoc[] = useMemo(() => {
    return [...catalogSkills, ...customSkills];
  }, [catalogSkills, customSkills]);

  const allRoles: WorkspaceRoleDoc[] = useMemo(() => {
    return [...catalogRoles, ...customRoles];
  }, [catalogRoles, customRoles]);

  const importMarkdownFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return [];
    const list = Array.from(files);
    const texts = await Promise.all(
      list.map(
        (f) =>
          new Promise<{ file: File; text: string }>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve({ file: f, text: String(reader.result ?? "") });
            reader.onerror = () => reject(new Error("Failed to read file"));
            reader.readAsText(f);
          }),
      ),
    );
    return texts;
  };

  const markdownTitle = (markdown: string, fallback: string) => {
    const lines = markdown.split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith("#")) return trimmed.replace(/^#+\s*/, "").trim() || fallback;
    }
    return fallback;
  };

  const markdownSummary = (markdown: string) => {
    const lines = markdown.split(/\r?\n/);
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith("#")) continue;
      if (trimmed.startsWith(">")) continue;
      if (trimmed.startsWith("-")) continue;
      return trimmed.length > 80 ? `${trimmed.slice(0, 80)}...` : trimmed;
    }
    return "Markdown 文档";
  };

  const parseSkillTools = (markdown: string): SkillTool[] => {
    const lower = markdown.toLowerCase();
    const tools: SkillTool[] = [];
    const add = (t: SkillTool) => {
      if (!tools.includes(t)) tools.push(t);
    };

    // Heuristic: if doc mentions tool names, infer them. Falls back to fileio.
    if (lower.includes("web browser") || lower.includes("browser") || lower.includes("网络浏览器")) add("browser");
    if (lower.includes("shell") || lower.includes("终端")) add("shell");
    if (lower.includes("python")) add("python");
    if (lower.includes("file i/o") || lower.includes("fileio") || lower.includes("文件")) add("fileio");
    return tools.length > 0 ? tools : ["fileio"];
  };

  const content = useMemo(() => {
    if (activeTab === "tools") {
      return (
        <>
          <div className="ws-tools-section-title">
            内置 Agent 工具
            <span className="ws-tools-section-note">
              开启后，Agent 可以在对话中自主决定是否调用这些能力。
            </span>
          </div>

          <div className="ws-tools-grid">
            {toolItems.map((tool) => {
              const enabled = toolEnabled[tool.id];
              return (
                <article className="ws-tools-card" key={tool.id}>
                  <div className="ws-tools-card-header">
                    <div className={`ws-tools-icon ws-tools-icon-${tool.iconKind}`}>
                      <ToolIcon kind={tool.iconKind} />
                    </div>
                    <label className="ws-tools-toggle" aria-label={`${tool.title} toggle`}>
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(event) => {
                          const next = event.target.checked;
                          setToolEnabled((prev) => ({ ...prev, [tool.id]: next }));
                        }}
                      />
                      <span className="ws-tools-slider" />
                    </label>
                  </div>

                  <div className="ws-tools-title">{tool.name}</div>
                  <div className="ws-tools-desc">{tool.description}</div>

                  <div className="ws-tools-footer">
                    <span className={`ws-tools-status ${enabled ? "is-enabled" : "is-disabled"}`}>
                      {enabled ? tool.status : "已关闭"}
                    </span>
                    <button className="manus-btn" type="button">
                      {tool.actionLabel}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      );
    }

    if (activeTab === "skills") {
      return (
        <>
          <div className="ws-tools-section-title">
            自定义技能 (Skills)
            <span className="ws-tools-section-note">点击卡片查看 Markdown 文档内容。</span>
          </div>

          {skillsLoading ? <div className="ws-tools-section-note">Loading skills catalog...</div> : null}
          {skillsLoadError ? <div className="ws-tools-section-note">Failed to load skills: {skillsLoadError}</div> : null}

          <div className="ws-tools-grid">
            {allSkills.map((skill) => (
              <article
                className="ws-tools-card ws-tools-card-clickable"
                key={skill.id}
                role="button"
                tabIndex={0}
                onClick={() =>
                  setPreviewDoc({
                    kind: "skill",
                    id: skill.id,
                    name: skill.name,
                    markdown: skill.markdown,
                  })
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setPreviewDoc({
                      kind: "skill",
                      id: skill.id,
                      name: skill.name,
                      markdown: skill.markdown,
                    });
                  }
                }}
              >
                <div className="ws-tools-card-header">
                  <div className={`ws-tools-icon ws-tools-icon-${skill.iconKind}`}>
                    <ToolIcon kind={skill.iconKind} />
                  </div>
                  <span className="ws-tools-chip">{skill.tools.length} tools</span>
                </div>

                <div className="ws-tools-title">{skill.name}</div>
                <div className="ws-tools-desc">{skill.summary}</div>

                <div className="ws-tools-footer">
                  <span className="ws-tools-skill-tools">
                    {skill.tools.map((tool) => skillToolLabel[tool] ?? tool).join(" · ")}
                  </span>
                  <span className="ws-tools-link-hint">查看</span>
                </div>
              </article>
            ))}

            <button
              type="button"
              className="ws-tools-card ws-tools-card-add"
              aria-label="Add skill"
              onClick={() => {
                importSkillsRef.current?.click();
              }}
            >
              <div className="ws-tools-add-inner">
                <div className="ws-tools-add-plus">+</div>
                <div className="ws-tools-add-label">导入 Skill</div>
              </div>
            </button>
          </div>
        </>
      );
    }

    return (
      <>
        <div className="ws-tools-section-title">
          角色 (Roles)
          <span className="ws-tools-section-note">点击卡片查看 Markdown 文档内容。</span>
        </div>

        {rolesLoading ? <div className="ws-tools-section-note">Loading roles catalog...</div> : null}
        {rolesLoadError ? <div className="ws-tools-section-note">Failed to load roles: {rolesLoadError}</div> : null}

        <div className="ws-tools-grid">
          {allRoles.map((role) => (
            <article
              className="ws-tools-card ws-tools-card-clickable"
              key={role.id}
              role="button"
              tabIndex={0}
              onClick={() =>
                setPreviewDoc({
                  kind: "role",
                  id: role.id,
                  name: role.name,
                  markdown: role.markdown,
                })
              }
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setPreviewDoc({
                    kind: "role",
                    id: role.id,
                    name: role.name,
                    markdown: role.markdown,
                  });
                }
              }}
            >
              <div className="ws-tools-card-header">
                <div className={`ws-tools-icon ws-tools-icon-${role.iconKind}`}>
                  <ToolIcon kind={role.iconKind} />
                </div>
                <span className="ws-tools-chip">role</span>
              </div>

              <div className="ws-tools-title">{role.name}</div>
              <div className="ws-tools-desc">{role.summary}</div>

              <div className="ws-tools-footer">
                <span className="ws-tools-skill-tools">Markdown</span>
                <span className="ws-tools-link-hint">查看</span>
              </div>
            </article>
          ))}

          <button
            type="button"
            className="ws-tools-card ws-tools-card-add"
            aria-label="Add role"
            onClick={() => {
              importRolesRef.current?.click();
            }}
          >
            <div className="ws-tools-add-inner">
              <div className="ws-tools-add-plus">+</div>
              <div className="ws-tools-add-label">导入 Role</div>
            </div>
          </button>
        </div>
      </>
    );
  }, [activeTab, toolEnabled, allSkills, allRoles, skillsLoading, skillsLoadError, rolesLoading, rolesLoadError]);

  return (
    <main className="main-content ws-tools-main">
      <header className="header ws-tools-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <h1 className="header-title">工具与技能</h1>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <Link className="manus-btn" href="/conversation" aria-label="Back to conversation" title="Back to conversation">
            返回会话
          </Link>
        </div>
      </header>

      <div className="content-area ws-tools-page">
        <div className="ws-tools-tabs" role="tablist" aria-label="Tools and skills tabs">
          {tabs.map((tab) => {
            const active = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                className={`ws-tools-tab ${active ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {content}
      </div>

      {/* Importers (open system file picker) */}
      <input
        ref={importSkillsRef}
        type="file"
        accept=".md,.markdown,text/markdown,text/plain"
        multiple
        style={{ display: "none" }}
        onChange={async (event) => {
          const picked = await importMarkdownFiles(event.currentTarget.files);
          // Reset so picking the same file again still triggers onChange.
          event.currentTarget.value = "";
          if (picked.length === 0) return;

          const docs: SkillDoc[] = picked.map(({ file, text }) => {
            const base = file.name.replace(/\.(md|markdown)$/i, "");
            const name = markdownTitle(text, base);
            const id = `skill-${base.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`;
            return {
              id,
              name,
              summary: markdownSummary(text),
              iconKind: "file",
              tools: parseSkillTools(text),
              markdown: text,
            };
          });
          setCustomSkills((prev) => [...docs, ...prev]);
          const first = docs[0];
          if (first) setPreviewDoc({ kind: "skill", id: first.id, name: first.name, markdown: first.markdown });
        }}
      />
      <input
        ref={importRolesRef}
        type="file"
        accept=".md,.markdown,text/markdown,text/plain"
        multiple
        style={{ display: "none" }}
        onChange={async (event) => {
          const picked = await importMarkdownFiles(event.currentTarget.files);
          event.currentTarget.value = "";
          if (picked.length === 0) return;

          const docs: WorkspaceRoleDoc[] = picked.map(({ file, text }) => {
            const base = file.name.replace(/\.(md|markdown)$/i, "");
            const name = markdownTitle(text, base);
            const id = `role-${base.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now()}`;
            return {
              id,
              name,
              summary: markdownSummary(text),
              iconKind: "file",
              markdown: text,
            };
          });
          setCustomRoles((prev) => [...docs, ...prev]);
          const first = docs[0];
          if (first) setPreviewDoc({ kind: "role", id: first.id, name: first.name, markdown: first.markdown });
        }}
      />

      {previewDoc ? (
        <div
          className="ws-tools-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Markdown preview dialog"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setPreviewDoc(null);
          }}
        >
          <div className="ws-tools-modal">
            <div className="ws-tools-modal-header">
              <div style={{ minWidth: 0 }}>
                <div className="ws-tools-modal-title">{previewDoc.name}</div>
                <div className="ws-tools-modal-subtitle">
                  {previewDoc.kind === "skill" ? "Skill Markdown" : "Role Markdown"}
                </div>
              </div>
              <button
                type="button"
                className="ws-tools-modal-close"
                aria-label="Close preview"
                title="Close"
                onClick={() => setPreviewDoc(null)}
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 6l12 12M18 6l-12 12" />
                </svg>
              </button>
            </div>
            <div className="ws-tools-modal-body">
              <pre className="ws-tools-preview-pre">{previewDoc.markdown}</pre>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

