import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Icon } from "./Icon";

const maximumMessageLength = 2_000;

interface ComposerProps {
  busy: boolean;
  disabled?: boolean;
  onSend: (message: string) => Promise<void> | void;
  onStop: () => void;
}

export function Composer({
  busy,
  disabled = false,
  onSend,
  onStop,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const message = value.trim();
    if (!message || busy || disabled) return;
    setValue("");
    resetHeight();
    await onSend(message);
    textareaRef.current?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      void submit();
    }
  };

  const resize = () => {
    const input = textareaRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 176).toString()}px`;
  };

  const resetHeight = () => {
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  return (
    <div className="composer-region">
      <form className="composer" onSubmit={(event) => void submit(event)}>
        <label className="sr-only" htmlFor="chat-message">
          Ask about drill-run history
        </label>
        <textarea
          id="chat-message"
          ref={textareaRef}
          rows={1}
          value={value}
          maxLength={maximumMessageLength}
          onChange={(event) => {
            setValue(event.target.value);
            resize();
          }}
          onKeyDown={onKeyDown}
          placeholder={
            disabled
              ? "Drill Advisor is temporarily unavailable"
              : "Ask a question about drill-run history…"
          }
          disabled={disabled || busy}
          aria-describedby="composer-hint"
        />
        {busy ? (
          <button
            className="send-button send-button--stop"
            type="button"
            onClick={onStop}
            aria-label="Stop analysis"
          >
            <Icon name="stop" size={18} />
            <span>Stop</span>
          </button>
        ) : (
          <button
            className="send-button"
            type="submit"
            disabled={disabled || value.trim().length === 0}
          >
            <Icon name="send" size={18} />
            <span>Send</span>
          </button>
        )}
      </form>
      <p id="composer-hint" className="composer-hint">
        Enter to send <span aria-hidden="true">•</span> Shift + Enter for a new
        line <span aria-hidden="true">•</span> 2,000 character limit{" "}
        <span aria-hidden="true">•</span> Verify critical field decisions
      </p>
    </div>
  );
}
