import type {
  SourceSummary,
  ToolCallSummary,
  UsageSummary,
} from "../types";

interface ResponseDetailsProps {
  toolCalls: ToolCallSummary[];
  sources: SourceSummary[];
  usage?: UsageSummary;
  latencyMs?: number;
}

export function ResponseDetails({
  toolCalls,
  sources,
  usage,
  latencyMs,
}: ResponseDetailsProps) {
  const hasMetadata =
    toolCalls.length > 0 || sources.length > 0 || usage || latencyMs !== undefined;
  if (!hasMetadata) return null;

  return (
    <details className="response-details">
      <summary>
        Sources &amp; analysis details
        {latencyMs !== undefined && (
          <span className="response-details__latency">
            {(latencyMs / 1000).toFixed(1)}s
          </span>
        )}
      </summary>
      <div className="response-details__content">
        {sources.length > 0 && (
          <section aria-labelledby="sources-heading">
            <h3 id="sources-heading">Sources</h3>
            <ol className="source-list">
              {sources.map((source, index) => (
                <li
                  key={`${source.name ?? "semantic-model"}-${index.toString()}`}
                >
                  <strong>{source.name ?? "Semantic model"}</strong>
                  {source.measures.length > 0 && (
                    <p>
                      Measures: <code>{source.measures.join(", ")}</code>
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}

        {toolCalls.length > 0 && (
          <section aria-labelledby="tools-heading">
            <h3 id="tools-heading">Tool activity</h3>
            <ul className="tool-list">
              {toolCalls.map((tool, index) => (
                <li
                  key={tool.id ?? `${tool.type}-${index.toString()}`}
                >
                  <span>
                    <strong>{tool.name ?? labelFromKey(tool.type)}</strong>
                    {(tool.server || tool.toolCount !== undefined) && (
                      <small>
                        {[
                          tool.server,
                          tool.toolCount == null
                            ? undefined
                            : `${tool.toolCount.toString()} tools`,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </small>
                    )}
                  </span>
                  <span className={`tool-status tool-status--${tool.status ?? "completed"}`}>
                    {tool.status ?? "completed"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {(usage || latencyMs !== undefined) && (
          <section aria-labelledby="metadata-heading">
            <h3 id="metadata-heading">Response metadata</h3>
            <dl className="metadata-list">
              {latencyMs !== undefined && (
                <>
                  <dt>Latency</dt>
                  <dd>{latencyMs.toString()} ms</dd>
                </>
              )}
              {usage &&
                Object.entries(usage).map(([key, value]) =>
                  value == null ? null : (
                    <div key={key}>
                      <dt>{labelFromKey(key)}</dt>
                      <dd>{value.toString()}</dd>
                    </div>
                  ),
                )}
            </dl>
          </section>
        )}
      </div>
    </details>
  );
}

function labelFromKey(value: string): string {
  return value
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (letter) => letter.toUpperCase());
}
