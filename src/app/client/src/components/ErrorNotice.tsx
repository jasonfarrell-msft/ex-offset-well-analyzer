interface ErrorNoticeProps {
  message: string;
  retryable: boolean;
  onDismiss: () => void;
  onRetry: () => void;
}

export function ErrorNotice({
  message,
  retryable,
  onDismiss,
  onRetry,
}: ErrorNoticeProps) {
  return (
    <div className="error-notice" role="alert">
      <span className="error-notice__mark" aria-hidden="true">
        !
      </span>
      <div>
        <strong>Analysis interrupted</strong>
        <p>{message}</p>
      </div>
      <div className="error-notice__actions">
        {retryable && (
          <button type="button" onClick={onRetry}>
            Retry
          </button>
        )}
        <button type="button" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
