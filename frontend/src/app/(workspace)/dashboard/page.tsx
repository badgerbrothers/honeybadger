"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";

import { NewTaskModal } from "@/features/tasks/NewTaskModal";
import { useWorkspace } from "@/features/workspace/WorkspaceContext";
import type { Task, TaskStatus } from "@/features/workspace/WorkspaceContext";

const ITEM_TYPE = "KANBAN_TASK";

const COLUMNS: Array<{ status: TaskStatus; label: string; dot: string; dotRing?: boolean }> = [
  { status: "schedule", label: "Schedule", dot: "#a1a1aa" },
  { status: "queue", label: "Queue", dot: "#a1a1aa" },
  { status: "inprogress", label: "In Progress", dot: "#3b82f6", dotRing: true },
  { status: "done", label: "Done", dot: "#10b981" },
];

interface DragTaskItem {
  taskId: string;
  from: TaskStatus;
}

function tagClass(label: string) {
  const lower = label.toLowerCase();
  if (lower.includes("web")) return "tag tag-blue";
  if (lower.includes("frontend")) return "tag tag-purple";
  if (lower.includes("success")) return "tag tag-green";
  if (lower.includes("python")) return "tag tag-gray";
  if (lower.includes("doc")) return "tag tag-gray";
  return "tag tag-gray";
}

function nextStatusForQuickMove(status: TaskStatus): TaskStatus {
  if (status === "schedule") return "queue";
  if (status === "queue") return "inprogress";
  return status;
}

function TaskCard({
  task,
  onMove,
}: {
  task: Task;
  onMove: (taskId: string, next: TaskStatus) => void;
}) {
  const movable = task.status === "schedule" || task.status === "queue";
  const [{ isDragging }, dragRef] = useDrag(
    () => ({
      type: ITEM_TYPE,
      item: { taskId: task.id, from: task.status } satisfies DragTaskItem,
      canDrag: movable,
      collect: (monitor) => ({ isDragging: monitor.isDragging() }),
    }),
    [task.id, task.status, movable],
  );

  const style: React.CSSProperties = useMemo(() => {
    if (task.highlight === "warn") {
      return { borderLeft: "3px solid #eab308", backgroundColor: "#fefce8" };
    }
    if (task.status === "inprogress") return { borderLeft: "3px solid #3b82f6" };
    if (task.status === "done") return { opacity: 0.7 };
    return {};
  }, [task.highlight, task.status]);

  return (
    <div
      ref={(node) => {
        dragRef(node);
      }}
      className="task-card"
      style={{
        ...style,
        opacity: isDragging ? 0.5 : style.opacity,
        cursor: movable ? "grab" : "default",
      }}
      role="article"
      aria-label={`Task ${task.id}`}
    >
      <div className="task-header">
        <span className="task-id">#{task.id}</span>
        <button
          type="button"
          style={{
            border: "none",
            background: "none",
            cursor: movable ? "pointer" : "not-allowed",
            color: movable ? "#a1a1aa" : "#d4d4d8",
          }}
          aria-label="Task menu"
          disabled={!movable}
          onClick={() => {
            if (!movable) return;
            const next = nextStatusForQuickMove(task.status);
            if (next !== task.status) onMove(task.id, next);
          }}
        >
          <svg viewBox="0 0 24 24" style={{ width: 16, height: 16 }}>
            <path
              fill="currentColor"
              d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
            />
          </svg>
        </button>
      </div>

      <div className="task-title">{task.title}</div>

      {task.tags.length > 0 ? (
        <div className="task-tags">
          {task.tags.map((tag) => (
            <span key={tag} className={tagClass(tag)}>
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      {task.meta ? (
        <div
          style={{
            fontSize: "0.8rem",
            color: task.highlight === "warn" ? "#854d0e" : "#4a4a4a",
            marginBottom: "0.5rem",
            fontWeight: task.highlight === "warn" ? 500 : 400,
          }}
        >
          {task.meta}
        </div>
      ) : null}

      {typeof task.progress === "number" ? (
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${Math.max(0, Math.min(100, task.progress))}%` }}
          />
        </div>
      ) : null}

      <div
        className="task-footer"
        style={task.progress ? { borderTop: "none", paddingTop: 0 } : undefined}
      >
        <div className="agent-info">
          <div
            className="agent-avatar"
            style={{ backgroundColor: task.status === "inprogress" ? "#3b82f6" : "#64748b" }}
          >
            {task.agentInitials}
          </div>
          {task.agentLabel}
        </div>
        <span
          style={{
            fontSize: "0.75rem",
            color: task.status === "inprogress" ? "#3b82f6" : "#a1a1aa",
          }}
        >
          {task.status === "inprogress"
            ? "In Progress"
            : task.status === "done"
              ? "Done"
              : "Queued"}
        </span>
      </div>
    </div>
  );
}

function KanbanColumn({
  status,
  label,
  dot,
  dotRing,
  tasks,
  onMove,
  highlighted,
  onQueuePushAll,
  paused,
  onTogglePause,
  maximized,
  hidden,
  onToggleMaximize,
}: {
  status: TaskStatus;
  label: string;
  dot: string;
  dotRing?: boolean;
  tasks: Task[];
  onMove: (taskId: string, next: TaskStatus) => void;
  highlighted: boolean;
  onQueuePushAll: () => void;
  paused: boolean;
  onTogglePause: () => void;
  maximized: boolean;
  hidden: boolean;
  onToggleMaximize: () => void;
}) {
  return (
    <section
      className={`kanban-column ${highlighted ? "drop-active" : ""} ${maximized ? "is-maximized" : ""} ${hidden ? "is-hidden" : ""}`}
      aria-label={`${label} column`}
    >
      <div className="column-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 0 }}>
          <span
            style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: dot,
              boxShadow: dotRing ? "0 0 0 2px #bfdbfe" : undefined,
              flex: "0 0 auto",
            }}
          />
          <span style={{ whiteSpace: "nowrap" }}>{label}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <button
            type="button"
            className="btn"
            style={{
              padding: "0.2rem",
              border: "1px solid #d4d4d8",
              background: maximized ? "#f4f4f5" : "white",
              width: "1.9rem",
              height: "1.9rem",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            onClick={onToggleMaximize}
            title={maximized ? "Restore columns" : "Maximize this column"}
            aria-label={maximized ? "Restore columns" : `Maximize ${label}`}
          >
            {maximized ? (
              <svg
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
                style={{ width: 14, height: 14 }}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.2"
                  d="M7 9l3 3-3 3M17 9l-3 3 3 3M10 12h4"
                />
              </svg>
            ) : (
              <svg
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
                style={{ width: 14, height: 14 }}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.2"
                  d="M7 9l-3 3 3 3M17 9l3 3-3 3M7 12h10"
                />
              </svg>
            )}
          </button>
          {status === "queue" ? (
            <button
              type="button"
              className="btn"
              style={{
                padding: "0.2rem 0.5rem",
                fontSize: "0.7rem",
                border: "1px solid #d4d4d8",
                background: "white",
              }}
              onClick={onQueuePushAll}
              title="Push all queue tasks to In Progress"
            >
              Push All
            </button>
          ) : null}
          {status === "inprogress" ? (
            <button
              type="button"
              className="btn"
              style={{
                padding: "0.2rem 0.5rem",
                fontSize: "0.7rem",
                border: "1px solid #d4d4d8",
                background: "white",
              }}
              onClick={onTogglePause}
              title="Pause or resume scheduling"
            >
              {paused ? "Resume" : "Pause"}
            </button>
          ) : null}
          <span className="column-count">{tasks.length}</span>
        </div>
      </div>
      <div className="column-content">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onMove={onMove} />
        ))}
      </div>
    </section>
  );
}

function DashboardContent() {
  const {
    activeConversation,
    activeTasks,
    moveTask,
    createTask,
    moveAllQueueToInProgress,
  } = useWorkspace();
  const [paused, setPaused] = useState(false);
  const [hoverStatus, setHoverStatus] = useState<TaskStatus | null>(null);
  const [maximizedStatus, setMaximizedStatus] = useState<TaskStatus | null>(null);
  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [newTaskDraft, setNewTaskDraft] = useState({ title: "", tags: "", meta: "" });
  const boardRef = useRef<HTMLDivElement | null>(null);

  const tasksByStatus = useMemo(() => {
    const map: Record<TaskStatus, Task[]> = {
      schedule: [],
      queue: [],
      inprogress: [],
      done: [],
    };
    for (const t of activeTasks) map[t.status].push(t);
    return map;
  }, [activeTasks]);

  const getStatusFromClientX = useCallback((clientX: number): TaskStatus | null => {
    if (maximizedStatus) return maximizedStatus;
    const board = boardRef.current;
    if (!board) return null;
    const rect = board.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right) return null;
    const relativeX = clientX - rect.left;
    const segment = rect.width / COLUMNS.length;
    const idx = Math.min(
      COLUMNS.length - 1,
      Math.max(0, Math.floor(relativeX / segment)),
    );
    return COLUMNS[idx]?.status ?? null;
  }, [maximizedStatus]);

  const [{ isOverBoard }, boardDropRef] = useDrop(
    () => ({
      accept: ITEM_TYPE,
      hover: (_item: DragTaskItem, monitor) => {
        const point = monitor.getClientOffset();
        if (!point) {
          setHoverStatus(null);
          return;
        }
        const status = getStatusFromClientX(point.x);
        setHoverStatus(status);
      },
      drop: (item: DragTaskItem, monitor) => {
        const point = monitor.getClientOffset();
        if (!point) return;
        const status = getStatusFromClientX(point.x);
        setHoverStatus(null);
        if (!status) return;
        if (item.from !== "schedule" && item.from !== "queue") return;
        moveTask(item.taskId, status);
      },
      collect: (monitor) => ({ isOverBoard: monitor.isOver({ shallow: true }) }),
    }),
    [getStatusFromClientX, moveTask, maximizedStatus],
  );

  useEffect(() => {
    if (!isOverBoard) setHoverStatus(null);
  }, [isOverBoard]);

  return (
    <main className="main-content kanban">
      <header className="header">
        <div className="header-left">
          <Link className="back-btn" href="/conversation" title="Back" aria-label="Back">
            <svg
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
              style={{ width: 18, height: 18 }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M11 5l-7 7 7 7M4 12h16"
              />
            </svg>
          </Link>
          <h1 className="header-title">DASHBOARD</h1>
          <span style={{ fontSize: "0.85rem", color: "#71717a", fontWeight: 500 }}>
            {activeConversation ? activeConversation.title : "No conversation"}
          </span>
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => {
              setNewTaskDraft({ title: "", tags: "", meta: "" });
              setNewTaskOpen(true);
            }}
          >
            + New Task
          </button>
        </div>
      </header>

      <div
        className={`kanban-board ${maximizedStatus ? "is-maximized" : ""}`}
        ref={(node) => {
          boardRef.current = node;
          boardDropRef(node);
        }}
      >
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.status}
            status={col.status}
            label={col.label}
            dot={col.dot}
            dotRing={col.dotRing}
            tasks={tasksByStatus[col.status]}
            onMove={moveTask}
            highlighted={
              maximizedStatus
                ? maximizedStatus === col.status
                : hoverStatus === col.status
            }
            onQueuePushAll={moveAllQueueToInProgress}
            paused={paused}
            onTogglePause={() => setPaused((v) => !v)}
            maximized={maximizedStatus === col.status}
            hidden={!!maximizedStatus && maximizedStatus !== col.status}
            onToggleMaximize={() =>
              setMaximizedStatus((current) =>
                current === col.status ? null : col.status,
              )
            }
          />
        ))}
      </div>

      <NewTaskModal
        open={newTaskOpen}
        draft={newTaskDraft}
        onChange={setNewTaskDraft}
        onCancel={() => setNewTaskOpen(false)}
        onCreate={(result) => {
          createTask(result);
          setNewTaskOpen(false);
        }}
      />
    </main>
  );
}

export default function DashboardPage() {
  return (
    <DndProvider backend={HTML5Backend}>
      <DashboardContent />
    </DndProvider>
  );
}
