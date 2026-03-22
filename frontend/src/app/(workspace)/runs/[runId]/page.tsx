"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { artifactsApi, runsApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/AuthContext";
import { downloadBlob } from "@/lib/download";
import { connectRunStream } from "@/lib/ws/runStream";
import type { ApiArtifact } from "@/lib/api/types";

function formatTime(value: string | null | undefined) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.valueOf())) return value;
  return d.toLocaleString();
}

function EventLine({ event }: { event: Record<string, unknown> }) {
  const type = typeof event.type === "string" ? event.type : "event";
  const timestamp =
    typeof event.timestamp === "string" ? formatTime(event.timestamp) : "";
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "0.75rem",
        padding: "0.6rem 0.75rem",
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: "0.6rem" }}>
        <strong style={{ fontSize: "0.88rem" }}>{type}</strong>
        <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>{timestamp}</span>
      </div>
      <pre
        style={{
          marginTop: "0.45rem",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontSize: "0.78rem",
          color: "#374151",
        }}
      >
        {JSON.stringify(event, null, 2)}
      </pre>
    </div>
  );
}

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const qc = useQueryClient();
  const { accessToken } = useAuth();

  const [streamEvents, setStreamEvents] = useState<Array<Record<string, unknown>>>([]);
  const [streamState, setStreamState] = useState<"idle" | "open" | "closed" | "error">("idle");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [downloadingArtifactId, setDownloadingArtifactId] = useState<string | null>(null);

  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => runsApi.get(runId),
    refetchInterval: 6_000,
  });

  const artifactsQuery = useQuery({
    queryKey: ["runArtifacts", runId],
    queryFn: () => runsApi.artifacts(runId),
    refetchInterval: 10_000,
  });

  const run = runQuery.data;
  const runStatus = run?.status ?? "pending";
  const initialLogs = useMemo(() => run?.logs ?? [], [run?.logs]);

  const mergedEvents = useMemo(() => {
    const base = initialLogs.map((x) => (typeof x === "object" && x ? (x as Record<string, unknown>) : { raw: String(x) }));
    return [...base, ...streamEvents];
  }, [initialLogs, streamEvents]);

  useEffect(() => {
    if (!runId || !accessToken) return;
    const stop = connectRunStream(runId, accessToken, {
      onOpen: () => {
        setStreamState("open");
        setStreamError(null);
      },
      onEvent: (event) => {
        setStreamEvents((prev) => [...prev, event]);
      },
      onClose: (evt) => {
        setStreamState("closed");
        if (evt.code === 4401) setStreamError("Session expired. Please login again.");
      },
      onError: () => {
        setStreamState("error");
        setStreamError("Realtime stream connection failed.");
      },
    });
    return () => stop();
  }, [accessToken, runId]);

  const canCancel = runStatus === "pending" || runStatus === "running";

  return (
    <main className="main-content" style={{ padding: "1rem 1.25rem", overflow: "auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
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
          <h1 className="header-title" style={{ margin: 0 }}>
            Run {runId}
          </h1>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span className="pill" style={{ fontSize: "0.85rem" }}>
            Status: <strong>{runStatus}</strong>
          </span>
          <button
            type="button"
            className="btn"
            disabled={!canCancel}
            onClick={async () => {
              await runsApi.cancel(runId);
              await qc.invalidateQueries({ queryKey: ["run", runId] });
            }}
          >
            Cancel
          </button>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: "0.9rem" }}>
        <section
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "1rem",
            background: "#fafafa",
            minHeight: "55vh",
            padding: "0.9rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.6rem" }}>
            <strong>Run Events</strong>
            <span style={{ fontSize: "0.8rem", color: "#6b7280" }}>
              stream: {streamState}
            </span>
          </div>
          {streamError ? (
            <div style={{ color: "#991b1b", fontSize: "0.85rem", marginBottom: "0.6rem" }}>
              {streamError}
            </div>
          ) : null}
          <div style={{ display: "grid", gap: "0.55rem" }}>
            {mergedEvents.length === 0 ? (
              <div style={{ color: "#6b7280", fontSize: "0.9rem" }}>No events yet.</div>
            ) : (
              mergedEvents.map((evt, idx) => <EventLine key={`${idx}-${String(evt.type ?? "event")}`} event={evt} />)
            )}
          </div>
        </section>

        <aside
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: "1rem",
            background: "#fff",
            minHeight: "55vh",
            padding: "0.9rem",
          }}
        >
          <strong>Artifacts</strong>
          <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.65rem" }}>
            {(artifactsQuery.data ?? []).map((artifact: ApiArtifact) => (
              <div
                key={artifact.id}
                style={{
                  border: "1px solid #e5e7eb",
                  borderRadius: "0.8rem",
                  padding: "0.65rem",
                  background: "#fafafa",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "0.88rem", wordBreak: "break-all" }}>
                  {artifact.name}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#6b7280", marginTop: "0.2rem" }}>
                  {artifact.artifact_type} · {Math.ceil(artifact.size / 1024)} KB
                </div>
                <button
                  type="button"
                  className="btn"
                  style={{ marginTop: "0.5rem" }}
                  disabled={downloadingArtifactId === artifact.id}
                  onClick={async () => {
                    setDownloadingArtifactId(artifact.id);
                    try {
                      const blob = await artifactsApi.downloadBlob(artifact.id);
                      downloadBlob(blob, artifact.name);
                    } finally {
                      setDownloadingArtifactId(null);
                    }
                  }}
                >
                  Download
                </button>
              </div>
            ))}
            {(artifactsQuery.data ?? []).length === 0 ? (
              <div style={{ color: "#6b7280", fontSize: "0.9rem" }}>No artifacts yet.</div>
            ) : null}
          </div>
          <div style={{ marginTop: "0.9rem", fontSize: "0.78rem", color: "#6b7280" }}>
            Started: {formatTime(run?.started_at)} <br />
            Completed: {formatTime(run?.completed_at)}
          </div>
        </aside>
      </div>
    </main>
  );
}
