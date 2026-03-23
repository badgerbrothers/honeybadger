import Link from "next/link";

export function RagEmptyState() {
  return (
    <>
      <div className="manus-page-header">
        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
          <h1 className="manus-page-title">RAG</h1>
          <div style={{ color: "#71717a", fontSize: "0.9rem" }}>
            Select a RAG from the left, or click the + button to create one.
          </div>
        </div>
        <Link className="manus-btn" href="/conversation" aria-label="Back to conversation" title="Back to conversation">
          返回会话
        </Link>
      </div>
      <div className="manus-content-area fluid" style={{ display: "flex", minHeight: "calc(100vh - 70px)" }}>
        <div className="rag-card" style={{ width: "100%" }}>
          <div className="rag-card-body">
            <div className="rag-muted">No RAG selected yet.</div>
          </div>
        </div>
      </div>
    </>
  );
}
