import Link from "next/link";

import type { ApiTask, ApiTaskRun } from "@/lib/api/types";
import type { RunEvent } from "@/lib/ws/runStream";

function formatTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

function titleize(value: string | null | undefined) {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function summarize(value: unknown, maxLength = 320) {
  if (value == null) return "";
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function eventKey(event: RunEvent) {
  return `${String(event.type ?? "event")}:${String(event.timestamp ?? "")}:${JSON.stringify(event)}`;
}

function eventTone(type: string) {
  if (type === "run_completed" || type === "artifact_created") return "success";
  if (type === "run_failed" || type === "skill_missing") return "danger";
  if (type === "tool_call" || type === "tool_result") return "accent";
  return "neutral";
}

function queueStatusLabel(status: ApiTask["queue_status"] | null | undefined) {
  if (!status) return "Pending";
  if (status === "in_progress") return "In progress";
  return titleize(status);
}

function runStatusLabel(status: ApiTaskRun["status"] | null | undefined) {
  return status ? titleize(status) : "Not started";
}

function describeEvent(event: RunEvent) {
  const type = typeof event.type === "string" ? event.type : "event";
  const toolName = typeof event.tool_name === "string" ? event.tool_name : "";

  if (type === "tool_call") {
    return {
      title: `Tool Call${toolName ? ` - ${toolName}` : ""}`,
      detail: "The agent requested a tool execution.",
      code: summarize(event.arguments, 900),
    };
  }

  if (type === "tool_result") {
    const success = event.success === true;
    return {
      title: `Tool Result${toolName ? ` - ${toolName}` : ""}`,
      detail: success ? "Tool execution succeeded." : "Tool execution failed.",
      code: summarize(success ? event.output : event.error, 900),
    };
  }

  if (type === "artifact_created") {
    return {
      title: `Artifact Created - ${String(event.name ?? "Artifact")}`,
      detail: typeof event.artifact_type === "string" ? `Type: ${event.artifact_type}` : "",
    };
  }

  if (type === "step") {
    return {
      title: titleize(typeof event.message === "string" ? event.message : "step"),
      detail: summarize(
        Object.fromEntries(
          Object.entries(event).filter(([key]) => !["type", "timestamp", "message"].includes(key)),
        ),
        220,
      ),
    };
  }

  if (type === "run_started") {
    return {
      title: "Run Started",
      detail: typeof event.status === "string" ? `Status: ${titleize(event.status)}` : "",
    };
  }

  if (type === "run_completed") {
    return {
      title: "Run Completed",
      detail: "The run finished successfully.",
      code: summarize(event.result, 900),
    };
  }

  if (type === "run_failed") {
    return {
      title: "Run Failed",
      detail: summarize(event.error, 240),
    };
  }

  if (type === "run_cancelled") {
    return {
      title: "Run Cancelled",
      detail: "The run was cancelled.",
    };
  }

  return {
    title: titleize(type),
    detail: summarize(
      Object.fromEntries(Object.entries(event).filter(([key]) => !["type", "timestamp"].includes(key))),
      260,
    ),
  };
}

type StreamState = "idle" | "open" | "closed" | "error";

interface ConversationExecutionPanelProps {
  hasConversation: boolean;
  selectedTask: ApiTask | null;
  selectedRun: ApiTaskRun | null;
  mergedEvents: RunEvent[];
  ragChunkCount: number;
  tasksLoading: boolean;
  runsLoading: boolean;
  streamState: StreamState;
  streamError: string | null;
}

export function ConversationExecutionPanel({
  hasConversation,
  selectedTask,
  selectedRun,
  mergedEvents,
  ragChunkCount,
  tasksLoading,
  runsLoading,
  streamState,
  streamError,
}: ConversationExecutionPanelProps) {
  return (
    <aside className="conversation-side-pane" aria-label="Plan and actions">
      <div className="conversation-side-header">
        <div>
          <div className="conversation-side-eyebrow">Execution</div>
          <h2 className="conversation-side-title">Plan &amp; Actions</h2>
        </div>
        {selectedRun ? (
          <Link className="conversation-side-link" href={`/runs/${selectedRun.id}`}>
            Open run
          </Link>
        ) : null}
      </div>

      <div className="conversation-side-body">
        {!hasConversation ? (
          <div className="conversation-side-empty">Select or create a conversation to inspect its execution plan.</div>
        ) : null}
        {hasConversation && !selectedTask && tasksLoading ? (
          <div className="conversation-side-empty">Loading tasks for this conversation...</div>
        ) : null}
        {hasConversation && !selectedTask && !tasksLoading ? (
          <div className="conversation-side-empty">
            No task has been created for this conversation yet. Send a message to start a run.
          </div>
        ) : null}

        {selectedTask ? (
          <>
            <section className="execution-card">
              <div className="execution-card-label">Current plan</div>
              <div className="execution-card-title">{selectedTask.goal}</div>
              <div className="execution-meta-grid">
                <div className="execution-meta-item">
                  <span>Task status</span>
                  <strong>{queueStatusLabel(selectedTask.queue_status)}</strong>
                </div>
                <div className="execution-meta-item">
                  <span>Run status</span>
                  <strong>{runStatusLabel(selectedRun?.status)}</strong>
                </div>
                <div className="execution-meta-item">
                  <span>Model</span>
                  <strong>{selectedTask.model}</strong>
                </div>
                <div className="execution-meta-item">
                  <span>Skill</span>
                  <strong>{selectedTask.skill ?? "None"}</strong>
                </div>
              </div>
              <div className="execution-plan-points">
                <div className="execution-plan-point">
                  <span className="execution-plan-dot" />
                  <div>
                    <strong>Objective</strong>
                    <p>Track the latest task for this conversation and surface its live execution steps.</p>
                  </div>
                </div>
                <div className="execution-plan-point">
                  <span className="execution-plan-dot" />
                  <div>
                    <strong>Context</strong>
                    <p>{ragChunkCount > 0 ? `${ragChunkCount} RAG chunks loaded into working memory.` : "No RAG context loaded for this run."}</p>
                  </div>
                </div>
                <div className="execution-plan-point">
                  <span className="execution-plan-dot" />
                  <div>
                    <strong>Updated</strong>
                    <p>{formatTime(selectedRun?.updated_at ?? selectedTask.updated_at)}</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="execution-card">
              <div className="execution-section-head">
                <div>
                  <div className="execution-card-label">Actions</div>
                  <div className="execution-section-subtitle">
                    {mergedEvents.length} event{mergedEvents.length === 1 ? "" : "s"}
                  </div>
                </div>
                <div className={`execution-stream-badge is-${streamState}`}>
                  {selectedRun?.status === "running" || selectedRun?.status === "pending"
                    ? `Live - ${streamState}`
                    : runStatusLabel(selectedRun?.status)}
                </div>
              </div>
              {streamError ? <div className="execution-inline-error">{streamError}</div> : null}
              {runsLoading && !selectedRun ? (
                <div className="conversation-side-empty">Loading run details...</div>
              ) : null}
              {!runsLoading && !selectedRun ? (
                <div className="conversation-side-empty">This task has no run records yet.</div>
              ) : null}
              {selectedRun ? (
                <div className="execution-timeline">
                  {mergedEvents.length === 0 ? (
                    <div className="conversation-side-empty">No execution events yet.</div>
                  ) : (
                    mergedEvents.map((event) => {
                      const info = describeEvent(event);
                      const type = typeof event.type === "string" ? event.type : "event";
                      return (
                        <article key={eventKey(event)} className="execution-event">
                          <div className={`execution-event-dot is-${eventTone(type)}`} aria-hidden="true" />
                          <div className="execution-event-body">
                            <div className="execution-event-head">
                              <strong>{info.title}</strong>
                              <span>{formatTime(typeof event.timestamp === "string" ? event.timestamp : null)}</span>
                            </div>
                            {info.detail ? <div className="execution-event-detail">{info.detail}</div> : null}
                            {info.code ? <pre className="execution-event-code">{info.code}</pre> : null}
                          </div>
                        </article>
                      );
                    })
                  )}
                </div>
              ) : null}
            </section>
          </>
        ) : null}
      </div>
    </aside>
  );
}
