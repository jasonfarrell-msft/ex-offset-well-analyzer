import { Icon } from "./Icon";

interface HeaderProps {
  hasConversation: boolean;
  onClear: () => void;
  onMenu: () => void;
  onNewChat: () => void;
}

export function Header({
  hasConversation,
  onClear,
  onMenu,
  onNewChat,
}: HeaderProps) {
  return (
    <header className="app-header">
      <div className="header-brand-group">
        <button
          id="conversation-history-trigger"
          className="icon-button mobile-menu"
          type="button"
          onClick={onMenu}
          aria-label="Open conversation history"
        >
          <Icon name="bars" />
        </button>
        <a className="brand" href="/" aria-label="Drill Advisor home">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>
            <strong>Drill</strong> Advisor
          </span>
        </a>
        <span className="environment">
          <i aria-hidden="true" />
          Development
        </span>
      </div>

      <div className="header-actions">
        <button className="header-button" type="button" onClick={onNewChat}>
          <Icon name="new" size={18} />
          <span>New chat</span>
        </button>
        <button
          className="header-button header-button--quiet"
          type="button"
          onClick={onClear}
          disabled={!hasConversation}
        >
          <Icon name="trash" size={17} />
          <span>Clear</span>
        </button>
        <span className="header-divider" aria-hidden="true" />
        <div className="auth-state" aria-label="Public access">
          <span className="auth-state__dot auth-state__dot--online" aria-hidden="true" />
          <span className="auth-state__label">Public POC</span>
        </div>
      </div>
    </header>
  );
}
