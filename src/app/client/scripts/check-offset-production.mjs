import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";

const dist = fileURLToPath(new URL("../dist", import.meta.url));
const args = process.argv.slice(2);
assert(args.length === 0 || (args.length === 1 && args[0] === "--enabled"), "Usage: node check-offset-production.mjs [--enabled]");
const enabled = args[0] === "--enabled";
const forbidden = [
  "OFFLINE SYNTHETIC PREVIEW",
  "SYN-TARGET-",
  "offline-section-summaries-v1",
  "904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d",
  "Fictional Aurora Field",
];
let checked = 0;
const javascript = [];
const assets = [];
let previewSources = 0;
function inspect(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) inspect(path);
    else {
      const content = readFileSync(path, "utf8");
      assets.push(entry.name);
      if (!enabled) {
        assert(!/snapshot|DevWorkspace|OffsetPreview/.test(entry.name), `Preview asset emitted: ${path}`);
        for (const text of forbidden) assert(!content.includes(text), `Preview fixture/content emitted in ${path}: ${text}`);
      }
      if (entry.name.endsWith(".js")) {
        javascript.push(content);
        for (const text of ["/@vite/client", "/@react-refresh", "react-refresh/runtime", "__vite_plugin_react_preamble_installed__", "http://localhost:5173", "SYN-RUN-"]) {
          assert(!content.includes(text), `Development runtime or raw run data emitted in ${path}: ${text}`);
        }
      }
      if (enabled && entry.name.endsWith(".js.map")) {
        const map = JSON.parse(content);
        map.sources.forEach((source, index) => {
          if (!source.includes("/offset-preview/")) return;
          assert(/\/(?:model\.ts|OffsetPreview\.tsx|DevWorkspace\.tsx)$/.test(source), `Unexpected preview source: ${source}`);
          const code = map.sourcesContent[index];
          assert(typeof code === "string", `Missing inspectable preview source: ${source}`);
          assert(!/\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(/.test(code), `Network client in preview: ${source}`);
          previewSources++;
        });
      }
      checked++;
    }
  }
}
inspect(dist);
assert(checked > 0, "Production output is empty");
if (enabled) {
  const code = javascript.join("\n");
  for (const text of [...forbidden, "not connected to Fabric", "Live offset chat is unavailable", "offset-preview"]) {
    assert(code.includes(text), `Enabled preview content missing: ${text}`);
  }
  assert(!/LOCAL ONLY|LOCAL DEVELOPMENT|DEVELOPMENT \/ OFFSET/.test(code), "Misleading local-only label in hosted preview");
  assert(assets.some((name) => /^DevWorkspace-.*\.js$/.test(name)), "Missing preview entry asset");
  assert(assets.some((name) => /^DevWorkspace-.*\.css$/.test(name)), "Missing preview styles");
  assert.equal(previewSources, 3, "Expected only the three static preview modules");
  const snapshot = JSON.parse(readFileSync(new URL("../src/offset-preview/snapshot.json", import.meta.url), "utf8"));
  assert.deepEqual(Object.keys(snapshot).sort(), ["provenance", "sections", "targets", "wells"]);
  for (const [collection, id, count] of [["targets", "target_id", 12], ["wells", "well_id", 100], ["sections", "section_id", 274]]) {
    assert.equal(snapshot[collection].length, count, `Unexpected snapshot ${collection} count`);
    for (const row of snapshot[collection]) assert(code.includes(row[id]), `Missing published ${collection} row: ${row[id]}`);
  }
  console.log(`PASS: ${checked} production files include the opted-in static preview (12 targets / 100 wells / 274 sections), disclosures and no development runtime or raw runs`);
} else {
  console.log(`PASS: ${checked} production files (including source maps) contain no preview fixtures or entry assets`);
}
