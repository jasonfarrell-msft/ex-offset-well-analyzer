import { useEffect, useRef } from "react";
import type { ConversationMessage } from "../types";
import { Icon } from "./Icon";
import { MarkdownContent } from "./MarkdownContent";
import { ResponseDetails } from "./ResponseDetails";
import { Visuals } from "./Visuals";

const suggestions = [
  "Summarize all 100 synthetic wells with headline KPIs and a supported visual",
  "Compare accepted and quarantined run counts with a bar chart",
  "Show the top 10 wells by total accepted footage in a table",
  "Summarize all data-quality issues by severity and issue category in a table",
];

interface ConversationViewProps {
  busy: boolean;
  messages: ConversationMessage[];
  onSuggestion: (prompt: string) => void;
}

export function ConversationView({
  busy,
  messages,
  onSuggestion,
}: ConversationViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);

  useEffect(() => {
    if (shouldAutoScroll.current) {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, busy]);

  return (
    <div
      ref={scrollRef}
      className="conversation-scroll"
      onScroll={(event) => {
        const element = event.currentTarget;
        const distanceFromBottom =
          element.scrollHeight - element.scrollTop - element.clientHeight;
        shouldAutoScroll.current = distanceFromBottom < 120;
      }}
    >
      {messages.length === 0 ? (
        <EmptyState onSuggestion={onSuggestion} />
      ) : (
        <div className="transcript" role="log" aria-label="Conversation">
          {messages.map((message) => (
            <article
              className={`message message--${message.role}`}
              key={message.id}
              aria-label={`${message.role === "user" ? "You" : "Drill Advisor"} at ${formatTime(message.createdAtUtc)}`}
            >
              <div className="message-avatar" aria-hidden="true">
                <Icon name={message.role === "user" ? "user" : "advisor"} />
              </div>
              <div className="message-content">
                <header>
                  <strong>
                    {message.role === "user" ? "You" : "Drill Advisor"}
                  </strong>
                  <time dateTime={message.createdAtUtc}>
                    {formatTime(message.createdAtUtc)}
                  </time>
                </header>
                {message.role === "user" ? (
                  <p className="user-text">{message.text}</p>
                ) : (
                  <>
                    <MarkdownContent markdown={message.markdown} />
                    <Visuals visuals={message.visuals} />
                    <ResponseDetails
                      toolCalls={message.toolCalls}
                      sources={message.sources}
                      {...(message.usage ? { usage: message.usage } : {})}
                      {...(message.latencyMs !== undefined
                        ? { latencyMs: message.latencyMs }
                        : {})}
                    />
                  </>
                )}
              </div>
            </article>
          ))}
          {busy && <BusyIndicator />}
        </div>
      )}
      {messages.length === 0 && busy && <BusyIndicator />}
    </div>
  );
}

function EmptyState({
  onSuggestion,
}: {
  onSuggestion: (prompt: string) => void;
}) {
  return (
    <section className="empty-state" aria-labelledby="empty-title">
      <div className="empty-state__graphic" aria-hidden="true">
        <span className="graphic-ring graphic-ring--outer" />
        <span className="graphic-ring graphic-ring--inner" />
        <Icon name="advisor" size={38} />
      </div>
      <span className="eyebrow">Drill-run intelligence</span>
      <h1 id="empty-title">
        Turn run history into
        <br /> a clearer next move.
      </h1>
      <p>
        Ask for historical comparisons, performance patterns, and traceable
        summaries grounded in the available drill-run data.
      </p>
      <div className="suggestion-grid" aria-label="Suggested questions">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSuggestion(suggestion)}
          >
            <span className="suggestion-number">
              {(index + 1).toString().padStart(2, "0")}
            </span>
            <span>{suggestion}</span>
            <Icon name="chevron" size={18} />
          </button>
        ))}
      </div>
    </section>
  );
}

function BusyIndicator() {
  return (
    <div
      className="message message--assistant message--busy"
      role="status"
      aria-live="polite"
      aria-label="Analyzing drill-run history"
    >
      <div className="message-avatar" aria-hidden="true">
        <Icon name="advisor" />
      </div>
      <div className="analysis-status">
        <div className="analysis-indicator" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div>
          <strong>Analyzing drill-run history…</strong>
          <small>Reviewing verified historical context</small>
        </div>
      </div>
    </div>
  );
}

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}
