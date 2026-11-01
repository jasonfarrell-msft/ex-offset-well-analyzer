import { useEffect, useState } from "react";
import { App } from "../App";
import OffsetPreview from "./OffsetPreview";
import "./preview.css";

function isPreviewUrl() {
  return new URLSearchParams(window.location.search).get("view") === "offset-preview";
}

export default function DevWorkspace() {
  const [preview, setPreview] = useState(isPreviewUrl);
  useEffect(() => {
    const sync = () => setPreview(isPreviewUrl());
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  function navigate(next: boolean) {
    const url = new URL(window.location.href);
    if (next) url.searchParams.set("view", "offset-preview");
    else url.searchParams.delete("view");
    window.history.pushState(null, "", url);
    setPreview(next);
  }

  return (
    <div className="dev-workspace">
      <nav className="dev-nav" aria-label="Drill Advisor workspace">
        <span className="dev-brand">DRILL ADVISOR <small>{import.meta.env.DEV ? "LOCAL DEVELOPMENT" : "OFFLINE SYNTHETIC PREVIEW"}</small></span>
        <div>
          <button type="button" aria-current={!preview ? "page" : undefined} onClick={() => navigate(false)}>Historical chat</button>
          <button type="button" aria-current={preview ? "page" : undefined} onClick={() => navigate(true)}>Offset well preview</button>
        </div>
      </nav>
      <div className="dev-content">{preview ? <OffsetPreview /> : <App />}</div>
    </div>
  );
}
