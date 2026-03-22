"use client";

import type { ChangeEvent, RefObject } from "react";

import { ArrowRightIcon, AttachmentIcon, CodeIcon, GlobeIcon, ModelIcon, RagIcon } from "../icons";
import type { ToolKey, ToolState } from "../types";
import styles from "../ChatScreen.module.css";

interface WelcomeComposerProps {
  textareaRef: RefObject<HTMLTextAreaElement>;
  fileInputRef: RefObject<HTMLInputElement>;
  message: string;
  selectedConversationId: string | null;
  uploadingFile: boolean;
  toolState: ToolState;
  modelMenuOpen: boolean;
  selectedModel: string;
  supportedModels: string[];
  sending: boolean;
  onMessageChange: (value: string) => void;
  onTextareaInput: () => void;
  onSend: () => void;
  onToggleTool: (tool: ToolKey) => void;
  onOpenFilePicker: () => void;
  onAttachmentChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onToggleModelMenu: () => void;
  onSelectModel: (model: string) => void;
}

export function WelcomeComposer({
  textareaRef,
  fileInputRef,
  message,
  selectedConversationId,
  uploadingFile,
  toolState,
  modelMenuOpen,
  selectedModel,
  supportedModels,
  sending,
  onMessageChange,
  onTextareaInput,
  onSend,
  onToggleTool,
  onOpenFilePicker,
  onAttachmentChange,
  onToggleModelMenu,
  onSelectModel,
}: WelcomeComposerProps) {
  return (
    <div className={styles.composerDock}>
      <div className={styles.inputContainer}>
        <textarea
          ref={textareaRef}
          className={styles.inputTextarea}
          placeholder={selectedConversationId ? "Message..." : "Start a conversation..."}
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          onInput={onTextareaInput}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSend();
            }
          }}
        />

        <div className={styles.inputToolbar}>
          <div className={styles.toolsLeft}>
            <button
              className={`${styles.toolButton} ${uploadingFile ? styles.toolButtonActive : ""}`}
              title="Add attachment"
              type="button"
              onClick={onOpenFilePicker}
              disabled={uploadingFile}
            >
              <AttachmentIcon className={styles.inlineIcon} />
            </button>
            <button
              className={`${styles.toolButton} ${toolState.search ? styles.toolButtonActive : ""}`}
              title="Web Search"
              type="button"
              onClick={() => onToggleTool("search")}
            >
              <GlobeIcon className={styles.inlineIcon} />
              Search
            </button>
            <button
              className={`${styles.toolButton} ${toolState.code ? styles.toolButtonActive : ""}`}
              title="Python / Code Execution"
              type="button"
              onClick={() => onToggleTool("code")}
            >
              <CodeIcon className={styles.inlineIcon} />
              Code
            </button>
            <button
              className={`${styles.toolButton} ${toolState.rag ? styles.toolButtonActive : ""}`}
              title="RAG Retrieval"
              type="button"
              onClick={() => onToggleTool("rag")}
            >
              <RagIcon className={styles.inlineIcon} />
              RAG
            </button>
          </div>
          <div className={styles.toolbarRight}>
            <div className={styles.modelPicker} data-model-anchor="true">
              <button className={styles.modelButton} title="Choose model" type="button" onClick={onToggleModelMenu}>
                <ModelIcon className={styles.inlineIcon} />
                <span className={styles.modelLabel}>{selectedModel}</span>
              </button>
              {modelMenuOpen ? (
                <div className={styles.modelMenu}>
                  {supportedModels.map((model) => (
                    <button
                      className={`${styles.modelMenuEntry} ${selectedModel === model ? styles.modelMenuEntryActive : ""}`}
                      key={model}
                      type="button"
                      onClick={() => onSelectModel(model)}
                    >
                      {model}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
            <button
              className={styles.sendButton}
              title="Send message"
              type="button"
              onClick={onSend}
              disabled={sending || !message.trim()}
            >
              <ArrowRightIcon className={styles.inlineIcon} />
            </button>
          </div>
        </div>
        <input
          ref={fileInputRef}
          className={styles.hiddenFileInput}
          type="file"
          onChange={(event) => onAttachmentChange(event)}
        />
      </div>
    </div>
  );
}
