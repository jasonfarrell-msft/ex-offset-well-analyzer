import { useEffect, useRef, useState } from "react";
import type { StoredConversation } from "../types";
import { Icon } from "./Icon";

interface HistorySidebarProps {
  conversations: StoredConversation[];
  currentId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
  onRename: (id: string, title: string) => void;
  onSelect: (id: string) => void;
}

export function HistorySidebar({
  conversations,
  currentId,
  isOpen,
  onClose,
  onDelete,
  onNewChat,
  onRename,
  onSelect,
}: HistorySidebarProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen) closeButtonRef.current?.focus();
  }, [isOpen]);

  const closeAndRestoreFocus = () => {
    onClose();
    window.requestAnimationFrame(() => {
      document.getElementById("conversation-history-trigger")?.focus();
    });
  };

  return (
    <>
      <button
        className={`drawer-scrim${isOpen ? " drawer-scrim--open" : ""}`}
        type="button"
        aria-label="Close conversation history"
        tabIndex={isOpen ? 0 : -1}
        onClick={closeAndRestoreFocus}
      />
      <aside
        className={`history-sidebar${isOpen ? " history-sidebar--open" : ""}`}
        aria-label="Conversation history"
      >
        <div className="history-sidebar__header">
          <div>
            <span className="eyebrow">Workspace</span>
            <h2>Conversations</h2>
          </div>
          <button
            ref={closeButtonRef}
            className="icon-button sidebar-close"
            type="button"
            onClick={closeAndRestoreFocus}
            aria-label="Close conversation history"
          >
            <Icon name="close" />
          </button>
        </div>

        <button
          className="new-chat-button"
          type="button"
          onClick={() => {
            onNewChat();
            closeAndRestoreFocus();
          }}
        >
          <Icon name="new" />
          Start new analysis
        </button>

        <nav className="history-nav" aria-label="Previous conversations">
          {conversations.length === 0 ? (
            <p className="history-empty">
              Your drill-run questions will appear here.
            </p>
          ) : (
            <ul>
              {conversations.map((conversation) => (
                <HistoryItem
                  key={conversation.localId}
                  conversation={conversation}
                  active={conversation.localId === currentId}
                  onDelete={onDelete}
                  onRename={onRename}
                  onSelect={(id) => {
                    onSelect(id);
                    closeAndRestoreFocus();
                  }}
                />
              ))}
            </ul>
          )}
        </nav>

        <footer className="sidebar-footer">
          <span className="sidebar-footer__icon" aria-hidden="true">
            DA
          </span>
          <p>
            <strong>Drill Advisor</strong>
            <span>Historical run intelligence</span>
          </p>
        </footer>
      </aside>
    </>
  );
}

function HistoryItem({
  conversation,
  active,
  onDelete,
  onRename,
  onSelect,
}: {
  conversation: StoredConversation;
  active: boolean;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onSelect: (id: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(conversation.title);

  const save = () => {
    const nextTitle = title.trim();
    if (nextTitle) onRename(conversation.localId, nextTitle);
    else setTitle(conversation.title);
    setEditing(false);
  };

  return (
    <li className={`history-item${active ? " history-item--active" : ""}`}>
      {editing ? (
        <form
          className="history-rename"
          onSubmit={(event) => {
            event.preventDefault();
            save();
          }}
        >
          <label className="sr-only" htmlFor={`rename-${conversation.localId}`}>
            Rename conversation
          </label>
          <input
            id={`rename-${conversation.localId}`}
            value={title}
            maxLength={80}
            autoFocus
            onChange={(event) => setTitle(event.target.value)}
            onBlur={save}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setTitle(conversation.title);
                setEditing(false);
              }
            }}
          />
        </form>
      ) : (
        <button
          className="history-item__select"
          type="button"
          onClick={() => onSelect(conversation.localId)}
          aria-current={active ? "page" : undefined}
        >
          <span>{conversation.title}</span>
          <time dateTime={conversation.updatedAtUtc}>
            {formatHistoryDate(conversation.updatedAtUtc)}
          </time>
        </button>
      )}
      <div className="history-item__actions">
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label={`Rename ${conversation.title}`}
        >
          <Icon name="edit" size={15} />
        </button>
        <button
          type="button"
          onClick={() => onDelete(conversation.localId)}
          aria-label={`Delete ${conversation.title}`}
        >
          <Icon name="trash" size={15} />
        </button>
      </div>
    </li>
  );
}

function formatHistoryDate(value: string): string {
  const date = new Date(value);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}
