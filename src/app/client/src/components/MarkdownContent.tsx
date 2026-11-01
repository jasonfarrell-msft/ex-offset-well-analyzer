import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { extractDisclosure } from "../lib/disclosure";

interface MarkdownContentProps {
  markdown: string;
}

export function MarkdownContent({ markdown }: MarkdownContentProps) {
  const { disclosure, body } = extractDisclosure(markdown);

  return (
    <div className="markdown-shell">
      {disclosure && (
        <div className="synthetic-banner" role="note" aria-label="Data disclosure">
          <span className="synthetic-banner__mark" aria-hidden="true">
            !
          </span>
          <strong>{disclosure}</strong>
        </div>
      )}
      {body && (
        <div className="markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ children, href, ...props }) => (
                <a
                  {...props}
                  href={href}
                  rel="noreferrer noopener"
                  target="_blank"
                >
                  {children}
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
              ),
              table: ({ children, ...props }) => (
                <div className="markdown-table-scroll" tabIndex={0}>
                  <table {...props}>{children}</table>
                </div>
              ),
              code: ({ children, className, ...props }) => (
                <code className={className} {...props}>
                  {children}
                </code>
              ),
            }}
          >
            {body}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}
