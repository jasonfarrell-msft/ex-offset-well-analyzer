# Drill Advisor client

React 19, Vite, and TypeScript client for the public Drill Advisor POC. The
compiled `dist` directory is copied into the ASP.NET Core host's `wwwroot` by
`src/app/Dockerfile`, so the UI and API use one Azure Container Apps origin.

Visitors do not sign in. The client has no MSAL dependency and never acquires,
stores, or sends an access token. The protected MCP relay is server-to-server
only.

## Local development

Start the .NET 10 server on port 8080, then run:

```bash
cd src/app
npm --prefix client ci
npm run dev
```

Browse `http://localhost:5173`. Vite proxies `/api/*` to
`http://localhost:8080`. No client `.env` file or Entra SPA registration is
required.

## Browser API contract

The client sends an anonymous same-origin request:

```http
POST /api/chat
Accept: application/json
Content-Type: application/json
```

```json
{
  "message": "Compare average ROP by formation",
  "conversationId": "optional-existing-conversation-id"
}
```

No `Authorization` or custom token header is sent, and a `401` does not start
an interactive authentication flow. The UI limits prompts to 2,000 characters
and displays safe rate-limit and availability errors.

Markdown/GFM, `kpi-grid`, `bar-chart`, and `data-table` visuals remain
supported. Foundry conversation IDs are reused for subsequent turns.
Conversations remain in browser `localStorage` under
`drill-advisor:conversations:v1`.

The offset workspace uses:

```http
POST /api/offset-analysis
Accept: application/json
Content-Type: application/json
```

with the contract-defined operations:

- `targets`
- `candidates`
- `compare`

`/api/chat` remains available for historical chat and accepts optional
`offsetContext` (`contractVersion`, `releaseId`, and `context`) for context-tied
follow-up narrative after comparison.

In the workspace nav, **Offset well analysis** (`?view=offset`) is the live API
flow (`targets` → `candidates` → `compare` → `choose reference` → target
expectation evidence brief → optional follow-up chat). Candidate and comparison
data are never served from a local snapshot fallback.
During offset dataset loads (`targets`, `candidates`, and `compare`), the UI now
shows a full-viewport blocking loader with phase-specific status text and a
reduced-motion-safe spinner. The overlay prevents pointer and keyboard
interaction with underlying controls (including workspace navigation) until the
active dataset request chain resolves, errors, or returns empty.
After a successful `compare`, the primary content pane advances from selection to a
dedicated results view. In that view, users explicitly choose one compared well as
the planning reference before generating a qualitative brief. The brief remains
descriptive and evidence-scoped (no target performance prediction, no operational
recommendations). “Back to selection” / “Edit selection” returns to the picker while
preserving the current target, filters, and selected wells unless context invalidation
occurs.
The comparison results also surface optional planned target intent
(`plannedBitType`, `plannedBhaType`, `plannedMudType`) separately from observed
offset run tuples (`runConfigContext.runTuples`) and synthetic operational
events (`eventContext` totals/by-type/by-subtype). Missing optional fields are
shown as unavailable without inferred defaults, and a visible disclosure
clarifies these synthetic comparisons are not telemetry or drilling
recommendations.
Run/event context blocks are well-wide aggregates by `wellId` and are explicitly
broader than matching-section metric scope (`MATCHING_WHOLE_SECTIONS`); users
should not sum those context counts to infer matching-run coverage.
The existing Result provenance panel displays available evidence source views,
grain, units, denominators, and quality caveats exactly as returned by the API.
Correlation IDs (`toolCallId`, `resultId`, `contextHash`) are shown only when
present and otherwise reported as unavailable.

## Validation

```bash
npm test
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```
