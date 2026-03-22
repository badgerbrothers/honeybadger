"use client";

import type { RefObject } from "react";

import { ChevronIcon, CollapseIcon, DotsVerticalIcon, PlusIcon } from "../icons";
import type { Conversation, MenuState, Project, RenameState } from "../types";
import styles from "../ChatScreen.module.css";

interface WelcomeSidebarProps {
  loading: boolean;
  selectedProject: Project | null;
  selectedProjectId: string | null;
  selectedConversationId: string | null;
  currentProjectConversations: Conversation[];
  orderedProjects: Project[];
  otherProjectsCollapsed: boolean;
  openMenu: MenuState;
  renaming: RenameState;
  renameInputRef: RefObject<HTMLInputElement>;
  onCreateProject: () => void;
  onHideSidebar: () => void;
  onToggleOtherProjects: () => void;
  onSwitchProject: (projectId: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onToggleMenu: (kind: "project" | "conversation", id: string) => void;
  onStartRenameProject: (project: Project) => void;
  onStartRenameConversation: (conversation: Conversation) => void;
  onRenameValueChange: (value: string) => void;
  onRenameBlur: (kind: "project" | "conversation", id: string) => void;
  onCancelRename: () => void;
  onDeleteProject: (project: Project) => void;
  onDeleteConversation: (conversation: Conversation) => void;
}

interface RenameInputProps {
  renameInputRef: RefObject<HTMLInputElement>;
  value: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  onCancel: () => void;
}

function RenameInput({ renameInputRef, value, onChange, onBlur, onCancel }: RenameInputProps) {
  return (
    <input
      ref={renameInputRef}
      className={styles.renameInput}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onBlur={onBlur}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          event.currentTarget.blur();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          onCancel();
        }
      }}
    />
  );
}

export function WelcomeSidebar({
  loading,
  selectedProject,
  selectedProjectId,
  selectedConversationId,
  currentProjectConversations,
  orderedProjects,
  otherProjectsCollapsed,
  openMenu,
  renaming,
  renameInputRef,
  onCreateProject,
  onHideSidebar,
  onToggleOtherProjects,
  onSwitchProject,
  onSelectConversation,
  onToggleMenu,
  onStartRenameProject,
  onStartRenameConversation,
  onRenameValueChange,
  onRenameBlur,
  onCancelRename,
  onDeleteProject,
  onDeleteConversation,
}: WelcomeSidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <button className={styles.newChatButton} type="button" onClick={onCreateProject}>
          <PlusIcon className={styles.inlineIcon} />
          New project
        </button>
        <button className={styles.iconButtonSmall} title="Collapse sidebar" type="button" onClick={onHideSidebar}>
          <CollapseIcon className={styles.inlineIcon} />
        </button>
      </div>

      <div className={styles.currentProjectHeader}>
        {selectedProject && renaming?.kind === "project" && renaming.id === selectedProject.id ? (
          <RenameInput
            renameInputRef={renameInputRef}
            value={renaming.value}
            onChange={onRenameValueChange}
            onBlur={() => onRenameBlur("project", selectedProject.id)}
            onCancel={onCancelRename}
          />
        ) : (
          <div className={styles.historySectionTitle}>
            {selectedProject ? selectedProject.name : "Current Project"}
          </div>
        )}
        {selectedProject ? (
          <div className={styles.itemActions} data-menu-anchor="true">
            <button
              className={styles.itemMenuButton}
              type="button"
              onClick={() => onToggleMenu("project", selectedProject.id)}
            >
              <DotsVerticalIcon className={styles.inlineIcon} />
            </button>
            {openMenu?.kind === "project" && openMenu.id === selectedProject.id ? (
              <div className={styles.itemMenu}>
                <button className={styles.itemMenuEntry} type="button" onClick={() => onStartRenameProject(selectedProject)}>
                  Rename
                </button>
                <button
                  className={`${styles.itemMenuEntry} ${styles.itemMenuEntryDanger}`}
                  type="button"
                  onClick={() => onDeleteProject(selectedProject)}
                >
                  Delete
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className={styles.chatHistory}>
        {loading ? <div className={styles.emptyHint}>Loading...</div> : null}
        {!loading && currentProjectConversations.length === 0 ? (
          <div className={styles.emptyHint}>No conversation yet</div>
        ) : null}
        {currentProjectConversations.map((item) => (
          <div className={styles.historyRow} key={item.id}>
            {renaming?.kind === "conversation" && renaming.id === item.id ? (
              <RenameInput
                renameInputRef={renameInputRef}
                value={renaming.value}
                onChange={onRenameValueChange}
                onBlur={() => onRenameBlur("conversation", item.id)}
                onCancel={onCancelRename}
              />
            ) : (
              <button
                className={`${styles.historyItem} ${selectedConversationId === item.id ? styles.historyItemActive : ""}`}
                type="button"
                onClick={() => onSelectConversation(item.id)}
              >
                {item.title}
              </button>
            )}
            <div className={styles.itemActions} data-menu-anchor="true">
              <button className={styles.itemMenuButton} type="button" onClick={() => onToggleMenu("conversation", item.id)}>
                <DotsVerticalIcon className={styles.inlineIcon} />
              </button>
              {openMenu?.kind === "conversation" && openMenu.id === item.id ? (
                <div className={styles.itemMenu}>
                  <button className={styles.itemMenuEntry} type="button" onClick={() => onStartRenameConversation(item)}>
                    Rename
                  </button>
                  <button
                    className={`${styles.itemMenuEntry} ${styles.itemMenuEntryDanger}`}
                    type="button"
                    onClick={() => onDeleteConversation(item)}
                  >
                    Delete
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <button className={styles.sectionToggle} type="button" onClick={onToggleOtherProjects}>
        <span className={styles.historySectionTitle}>Other Projects</span>
        <span className={`${styles.sectionChevron} ${otherProjectsCollapsed ? styles.sectionChevronCollapsed : ""}`}>
          <ChevronIcon className={styles.inlineIcon} />
        </span>
      </button>
      <div className={`${styles.chatHistoryStatic} ${otherProjectsCollapsed ? styles.chatHistoryStaticCollapsed : ""}`}>
        {orderedProjects.length === 0 ? <div className={styles.emptyHint}>No project</div> : null}
        {orderedProjects.map((item) => (
          <div className={styles.historyRow} key={item.id}>
            {renaming?.kind === "project" && renaming.id === item.id && item.id !== selectedProjectId ? (
              <RenameInput
                renameInputRef={renameInputRef}
                value={renaming.value}
                onChange={onRenameValueChange}
                onBlur={() => onRenameBlur("project", item.id)}
                onCancel={onCancelRename}
              />
            ) : (
              <button
                className={`${styles.historyItem} ${selectedProjectId === item.id ? styles.historyItemActive : ""}`}
                type="button"
                onClick={() => onSwitchProject(item.id)}
              >
                {item.name}
              </button>
            )}
            <div className={styles.itemActions} data-menu-anchor="true">
              <button className={styles.itemMenuButton} type="button" onClick={() => onToggleMenu("project", item.id)}>
                <DotsVerticalIcon className={styles.inlineIcon} />
              </button>
              {openMenu?.kind === "project" && openMenu.id === item.id ? (
                <div className={styles.itemMenu}>
                  <button className={styles.itemMenuEntry} type="button" onClick={() => onStartRenameProject(item)}>
                    Rename
                  </button>
                  <button
                    className={`${styles.itemMenuEntry} ${styles.itemMenuEntryDanger}`}
                    type="button"
                    onClick={() => onDeleteProject(item)}
                  >
                    Delete
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <div className={styles.sidebarFooter}>
        <button className={styles.userProfile} type="button">
          <div className={styles.avatarSmall}>U</div>
          <span className={styles.userLabel}>User Workspace</span>
        </button>
      </div>
    </aside>
  );
}
