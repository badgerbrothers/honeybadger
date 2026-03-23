import { useRef, type KeyboardEvent, type MutableRefObject } from "react";

interface ConversationComposerProps {
  empty: boolean;
  placeholder: string;
  draft: string;
  setDraft: (value: string) => void;
  textareaRef: MutableRefObject<HTMLTextAreaElement | null>;
  onTextareaInput: () => void;
  onSend: () => void;
  error: string | null;
  canUpload: boolean;
  uploading: boolean;
  onUploadFiles: (files: File[]) => Promise<void>;
  ragMenuOpen: boolean;
  selectedRagName: string;
  selectedModel: string;
  ragBtnRef: MutableRefObject<HTMLButtonElement | null>;
  modelBtnRef: MutableRefObject<HTMLButtonElement | null>;
  onRagToggle: () => void;
  onModelToggle: () => void;
  canSend: boolean;
  sending: boolean;
}

export function ConversationComposer({
  empty,
  placeholder,
  draft,
  setDraft,
  textareaRef,
  onTextareaInput,
  onSend,
  error,
  canUpload,
  uploading,
  onUploadFiles,
  ragMenuOpen,
  selectedRagName,
  selectedModel,
  ragBtnRef,
  modelBtnRef,
  onRagToggle,
  onModelToggle,
  canSend,
  sending,
}: ConversationComposerProps) {
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className={`composer ${empty ? "" : "has-messages"}`}>
      <div className="input-container">
        <textarea
          ref={textareaRef}
          className="input-textarea"
          placeholder={placeholder}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onInput={onTextareaInput}
          onKeyDown={handleKeyDown}
        />
        {error ? <div style={{ padding: "0.5rem 0.75rem", color: "#991b1b", fontSize: "0.9rem" }}>{error}</div> : null}
        <div className="input-toolbar">
          <div className="tools-left">
            <input
              ref={uploadInputRef}
              type="file"
              style={{ display: "none" }}
              onChange={async (event) => {
                const files = Array.from(event.currentTarget.files ?? []);
                event.currentTarget.value = "";
                if (files.length === 0) return;
                await onUploadFiles(files);
              }}
            />
            <button
              className={`tool-btn ${uploading ? "active" : ""}`}
              type="button"
              title="Add attachment"
              aria-label="Add attachment"
              onClick={() => uploadInputRef.current?.click()}
              disabled={!canUpload || uploading}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            <button className="tool-btn active" type="button" title="Web Search" aria-label="Web search">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              Search
            </button>
            <button
              className={`tool-btn ${ragMenuOpen ? "active" : ""}`}
              id="ragBtn"
              ref={ragBtnRef}
              type="button"
              title="RAG"
              aria-label="RAG"
              onClick={onRagToggle}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h10M4 18h16" />
              </svg>
              {selectedRagName}
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
            <button
              className="tool-btn"
              id="modelBtn"
              ref={modelBtnRef}
              type="button"
              title="Model"
              aria-label="Model"
              onClick={onModelToggle}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5h6M9 19h6M5 9h14M7 15h10" />
              </svg>
              <span id="modelBtnLabel">{selectedModel}</span>
            </button>
            <button className="send-btn" title="Send message" aria-label="Send message" type="button" onClick={onSend} disabled={!canSend || sending}>
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
