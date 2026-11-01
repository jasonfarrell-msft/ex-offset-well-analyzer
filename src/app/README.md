# Drill Advisor application

Drill Advisor is one Azure Container Apps-ready application: an ASP.NET Core
.NET 10 LTS host serves the compiled React 19 SPA and both API routes on the
same origin. The browser does not sign in or acquire a token.

The previous .NET 8 isolated Azure Functions source remains under `api/` for
rollback. The new host links its framework-neutral Foundry, Fabric, identity,
limit, model, and serialization source files rather than maintaining divergent
copies. Function entry points and their SWA/Easy Auth behavior are not used by
the container host.

## Current deployed state

The Container App is live at
`https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io`.
Foundry connection `fabric-dataagent-mi-bridge` targets its protected
`/api/mcp/fabric-dataagent` route with `ProjectManagedIdentity` and audience
`api://0e956ed5-6da6-477a-b508-3c6cdf5b2861`.

`welladvisor-fabric-orchestrator` version **7** is active/latest. It was cloned
from version 4 with only the MCP `server_url` changed to the Container App;
version 4 remains available for rollback. Direct Foundry and public
`POST /api/chat` validation returned the exact disclosure, 100 wells, five
quarantined runs, completed MCP list/call evidence, and a typed `kpi-grid`.
Conversation reuse also passed. Anonymous access to the MCP route returns
`401`.

## Architecture

```text
anonymous browser
  -> ACA ingress :8080
  -> ASP.NET Core static files / SPA fallback
  -> anonymous POST /api/chat
  -> user-assigned managed identity
  -> Microsoft Foundry agent v7
  -> bearer-authenticated /api/mcp/fabric-dataagent
  -> federated Fabric application exchange
  -> fixed Fabric Data Agent MCP endpoint
```

`POST /api/chat` is intentionally anonymous. It accepts a message and optional
Foundry continuation ID and returns Markdown, typed visuals, MCP tool details,
sources, usage, and the next conversation ID. The total Foundry operation
timeout is 210 seconds so the host can return a safe response before a longer
ACA ingress timeout.

`GET|POST|DELETE /api/mcp/fabric-dataagent` is not public. ASP.NET Core JWT
bearer authentication validates the Microsoft Entra signing key, tenant issuer,
token lifetime, configured audience, `Mcp.Invoke` app role, expected Foundry
managed-identity object ID, and the expected client ID when that claim and
configuration value are available. The relay never accepts a caller-selected
target or forwards the inbound bearer token.

## Anonymous POC controls

`PUBLIC_CHAT_ENABLED` is a fail-closed kill switch and defaults to `false`.
Admitted calls are limited to:

- 2,000 prompt characters;
- 3 requests per source IP per rolling minute;
- 1 concurrent request per source IP;
- 60 requests per rolling minute globally;
- 10 concurrent requests globally; and
- 500 Foundry calls per UTC day.

Source IPs are salted and hashed for accounting. Prompts, tokens, raw IPs, and
upstream results are not logged. Rejections use safe `429` or `503` problem
responses and `Retry-After`.

All counters, including the daily quota, are process memory only. They reset
when the container restarts and do not coordinate across replicas. Keep ACA
maximum replicas at **1** for this POC. Use a durable shared counter before
scaling out or treating the daily quota as a billing control.

## ACA configuration

Assign the existing user-assigned managed identity to the Container App and set
the following environment variables or secret references. None are baked into
the image.

| Setting | Required value or purpose |
| --- | --- |
| `ENTRA_TENANT_ID` | Tenant containing the managed identities and Fabric app |
| `MANAGED_IDENTITY_CLIENT_ID` | Existing UAMI client ID; used for Foundry and the Fabric assertion |
| `FOUNDRY_PROJECT_ENDPOINT` | Fixed HTTPS Foundry project endpoint |
| `FOUNDRY_AGENT_NAME` | Foundry agent reference name; currently resolves to active/latest version 7 |
| `FABRIC_APP_CLIENT_ID` | Federated Fabric application client ID |
| `FABRIC_TOKEN_SCOPE` | Exactly `https://api.fabric.microsoft.com/.default` or `https://analysis.windows.net/powerbi/api/.default` |
| `FABRIC_DATA_AGENT_MCP_ENDPOINT` | Fixed HTTPS Fabric Data Agent streamable HTTP endpoint |
| `MCP_AUDIENCE` | `api://0e956ed5-6da6-477a-b508-3c6cdf5b2861` |
| `MCP_REQUIRED_ROLE` | Optional; if set, must be `Mcp.Invoke` |
| `FOUNDRY_PROJECT_PRINCIPAL_ID` | `f9b86896-cc12-4a2f-92ff-edf9d5e570ef` |
| `FOUNDRY_PROJECT_CLIENT_ID` | Foundry project managed-identity client ID, when known |
| `OFFSET_SQL_SERVER` | Fabric SQL endpoint host (for example `*.datawarehouse.fabric.microsoft.com`) |
| `OFFSET_SQL_DATABASE` | Fabric SQL database name (for example `lh_drillrun_summary`) |
| `OFFSET_SQL_COMMAND_TIMEOUT_SECONDS` | Optional SQL timeout; defaults to `30` (allowed `5`–`300`) |
| `PUBLIC_CHAT_ENABLED` | `true` only after the end-to-end path is approved |

Configure external ingress to target port `8080`, an ingress/request timeout
greater than 210 seconds, and maximum replicas `1`. Recommended HTTP probes:

| Probe | Path | Suggested timing |
| --- | --- | --- |
| Liveness | `/healthz` | initial delay 5s, period 30s |
| Readiness | `/readyz` | initial delay 2s, period 10s |

Both probe responses expose only a status word. Startup option validation keeps
an incorrectly configured revision from becoming ready.

## Build and local development

### Live Offset Well Analysis workspace

The workspace navigation now exposes two live views: **Historical chat** and
**Offset well analysis**. Offset analysis issues real requests to
`/api/offset-analysis` and optional follow-up chat requests to `/api/chat`
using the contract-aligned `offsetContext` envelope. Results render only from
successful API responses; there is no snapshot fallback path for live requests.

Start the server and Vite for local end-to-end behavior:

```bash
# From the repository root (dependencies already installed in this checkout)
npm --prefix src/app/client run dev
```

Open **http://localhost:5173/?view=offset** or use **Offset well analysis** in
the workspace navigation. Browser refresh/back/forward keeps `?view=offset`
state. The backend remains keyless for visitors; managed identity is backend-only.

Workflow: choose one of the **12 planned targets**, set a surface radius
(default **10,000 ft**, allowed **0–3,000,000 ft**, up to six decimal places),
apply same-section canonical formation/hole-size criteria (both on by default),
optionally enable strict MD overlap (off by default), manually select **1–5**
eligible historical wells, then explicitly **Compare selected**. The complete
candidate set is ordered by unrounded squared distance then well ID and
displayed 25 per page. Selection is never automatic; target/filter changes
clear selection and comparison, and selection changes clear comparison.

All metrics cover the identical matching **whole sections**, without MD
prorating. Accepted runs are PASS/WARNING; ERROR metrics are excluded while
warning/quarantine coverage remains visible. Footage/run divides accepted
footage by accepted run count. **Historical summary ft/hour** divides accepted
footage by accepted duration, not instantaneous ROP or an average of run rates.
Ratios retain six-decimal half-up precision; missing results are not zero.
Targets contain planning fields only and never enter historical totals.

The offset view keeps the **SYNTHETIC DATA • v1.1.0** disclosure and provenance
panel. Locations
are fictional surface wellheads in abstract local frame `SYN-LOCAL-FT-V1`
(ft); proximity establishes no subsurface/geologic equivalence or operational
advice. There are no predictions or realized target outcomes.
This is not completion/acceptance of the end-to-end feature. The unresolved
current-generator/source-fingerprint mismatch is not repaired or waived here.

#### Retained offline snapshot provenance and verification

`client/src/offset-preview/snapshot.json` is a compact summary snapshot of
immutable `data/releases/v1.1.0/`: **12 targets, 100 wells, 274 section-grain
accepted summaries**; no individual run rows are shipped. Release ID:

```text
v1.1.0:904a5b293fdf0654fb1c5b4d28dd79d1c9cfaaac612f71d8f297ec874f4d284d
```

The suffix is the SHA-256 of the release manifest. That manifest pins all 11
archive members; the snapshot includes those hashes, its source version and
the release-recorded generator fingerprint
`197d65dd19ff59c6ba9ab93fdb1f5cce7020836bec9f6e80550ff07a328b893f`.
This fingerprint describes the recorded release, not verified current generator
source. `client/scripts/offset_snapshot.py` uses stdlib CSV/Decimal,
verifies manifest/member SHA-256 before deriving section sums, deduplicates
neither runs nor issues, and preserves independent warning/quarantine counts.
It reads release bytes only; it never regenerates or edits a release or imports
generator code. Check it from repository root:

```bash
python3 src/app/client/scripts/offset_snapshot.py --check
# Explicitly re-derive only the client snapshot from the same immutable bytes:
python3 src/app/client/scripts/offset_snapshot.py
```

The tests additionally compare candidate sets, ordering, section scopes and
every metric against the existing independent Decimal oracle for all 12
targets, all eight section-filter combinations, zero radius and maximum
radius (120 contexts). The grader-only bridge
`client/scripts/offset_oracle_cases.py` is never imported by the application.
Local preview calculations use exact fixed-point sums/radius comparisons.

The retained offline preview assets are gated by
**`import.meta.env.DEV || import.meta.env.VITE_ENABLE_OFFSET_PREVIEW === 'true'`**.
Development behavior is unchanged. Only the exact build-time string `true` opts in; unset, `false`,
`TRUE`, `1` and whitespace-padded values fail closed. A query string never
enables an unopted build. This is a public build setting, not a credential or
runtime server environment setting. Check both modes (repository root):

```bash
npm --prefix src/app/client test
npm --prefix src/app/client run lint
VITE_ENABLE_OFFSET_PREVIEW=false npm --prefix src/app/client run build
node src/app/client/scripts/check-offset-production.mjs
VITE_ENABLE_OFFSET_PREVIEW=true npm --prefix src/app/client run build
node src/app/client/scripts/check-offset-production.mjs --enabled
python3 src/app/client/scripts/offset_snapshot.py --check
python3 -m unittest discover -s tests -p test_offset_analysis.py
```

The default production artifact check includes source maps and rejects emitted
preview fixture identifiers, release pins and preview entry assets. Its explicit
`--enabled` mode instead requires the intended static preview modules, styles,
all 12/100/274 snapshot identifiers and offline disclosures, and rejects
development-server runtime code, misleading local-only labels, raw run
identifiers and network clients in the preview sources.

#### Explicit opt-in hosted preview assets

After review, build the authorized preview image using the existing app context:

```bash
# From the repository root; builds only, does not publish or deploy.
docker build --build-arg VITE_ENABLE_OFFSET_PREVIEW=true \
  --tag acrdrilladvisormx01.azurecr.io/drill-advisor:offline-preview src/app
```

Omit the build arg (default `false`) for the normal image. The arg is scoped
to the client build stage and does not change runtime settings, authentication,
identity or API behavior. Changing it requires rebuilding the image; setting a
Container App environment variable cannot enable the preview assets.

Once that explicitly enabled image has been deployed to the existing app, open:

**https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io/?view=offset**

The root URL still starts with historical chat; use **Offset well analysis** to
switch workspaces. This URL is the intended hosted access path, not evidence
that a rollout has completed. Hosted preview content is public static synthetic
summary data from the same reviewed snapshot (no individual run rows). It does
not replace or bypass live API behavior.

Prerequisites: Node.js 24 LTS, npm, .NET 10 SDK, Docker, and Azure CLI for an
optional real local Foundry call.

Run Vite and ASP.NET Core in separate terminals:

```bash
cd src/app
npm --prefix client ci
npm run dev:server
```

```bash
cd src/app
npm run dev
```

Vite listens on `http://localhost:5173` and proxies `/api` to ASP.NET Core on
`http://localhost:8080`. Export the settings in the table before starting the
server. Outside ACA, the server uses the current Azure CLI credential; it never
uses a browser-provided token.

Build and run the production image:

```bash
cd src/app
npm run container:build
docker run --rm --name drill-advisor-local \
  --publish 8080:8080 \
  --env-file .env.container.local \
  drill-advisor:local
```

Keep `.env.container.local` local and untracked. The runtime image is the .NET
10 Ubuntu chiseled ASP.NET image, runs as its non-root `app` user, has no
package-manager installation step, and listens on port 8080.

## Validation

```bash
npm --prefix client test
npm --prefix client run lint
npm --prefix client run typecheck
npm --prefix client run build
npm --prefix client audit --audit-level=high

dotnet test server/DrillAdvisor.Web.Tests/DrillAdvisor.Web.Tests.csproj
dotnet build server/DrillAdvisor.Web/DrillAdvisor.Web.csproj
dotnet format server/DrillAdvisor.Web.Tests/DrillAdvisor.Web.Tests.csproj \
  --verify-no-changes --no-restore
dotnet list server/DrillAdvisor.Web.Tests/DrillAdvisor.Web.Tests.csproj \
  package --vulnerable --include-transitive

DOTNET_ROLL_FORWARD=Major \
  dotnet test api/DrillAdvisor.Api.Tests/DrillAdvisor.Api.Tests.csproj
```

The server integration suite covers anonymous chat, typed responses and
conversation reuse, kill switch and request limits, direct JWT validation and
MCP method authorization, fixed relay target, probes, static assets, and SPA
fallback.
