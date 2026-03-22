export function RagEmptyState() {
  return (
    <div className="manus-page-header" style={{ justifyContent: "flex-start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <h1 className="manus-page-title">RAG</h1>
        <div style={{ color: "#71717a", fontSize: "0.9rem" }}>
          Select a RAG from the left, or click the + button to create one.
        </div>
      </div>
    </div>
  );
}

