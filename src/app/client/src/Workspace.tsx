import { useEffect, useState } from "react";
import { App } from "./App";
import { OffsetAnalysis } from "./offset-live/OffsetAnalysis";
import "./offset-preview/preview.css";

type View = "chat" | "offset";

function currentView(): View {
  return new URLSearchParams(window.location.search).get("view") === "offset"
    ? "offset"
    : "chat";
}

export function Workspace() {
  const [view, setView] = useState<View>(currentView);

  useEffect(() => {
    const sync = () => setView(currentView());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const navigate = (next: View) => {
    const url = new URL(window.location.href);
    if (next === "offset") url.searchParams.set("view", "offset");
    else url.searchParams.delete("view");
    window.history.pushState(null, "", url);
    setView(next);
  };

  return (
    <div className="dev-workspace">
      <nav className="dev-nav" aria-label="Drill Advisor workspace">
        <span className="dev-brand">
          DRILL ADVISOR <small>HISTORICAL CHAT + LIVE OFFSET ANALYSIS</small>
        </span>
        <div>
          <button
            type="button"
            aria-current={view === "chat" ? "page" : undefined}
            onClick={() => navigate("chat")}
          >
            Historical chat
          </button>
          <button
            type="button"
            aria-current={view === "offset" ? "page" : undefined}
            onClick={() => navigate("offset")}
          >
            Offset well analysis
          </button>
        </div>
      </nav>
      <div className="dev-content">{view === "offset" ? <OffsetAnalysis /> : <App />}</div>
    </div>
  );
}
