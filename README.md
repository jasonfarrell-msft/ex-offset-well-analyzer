# Drill Run History & Drill Advisor

A synthetic-data proof of concept for exploring historical drilling summaries
and comparing fictional offset wells with Microsoft Fabric and Foundry.

**Hosted POC:** [Open Drill Advisor](https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io/)
([Offset well analysis](https://ca-drill-advisor-wfrd-mx01.icytree-3fa8fc52.centralus.azurecontainerapps.io/?view=offset))

> [!IMPORTANT]
> All well, section, run, target, configuration, and event data in this POC are
> fictional. Results are descriptive examples—not predictions, drilling
> recommendations, or a basis for operational decisions.

## What it does

- **Historical chat** answers natural-language questions about summary-level
  drilling history.
- **Offset well analysis** lets a user choose a planned target, filter and
  select candidate wells, compare them, and choose a reference well for a
  qualitative evidence brief. Candidates are filtered by surface distance;
  the reference is an explicit human choice, not an automatically recommended
  well.

The application is a same-origin React 19 client and ASP.NET Core .NET 10 host
running in Azure Container Apps. Chat calls a Foundry agent, which reaches a
protected Fabric Data Agent MCP relay. Offset analysis uses a separate API and
the Fabric SQL serving views. Cloud credentials stay on the backend; visitors
do not sign in or provide tokens.

```text
Browser → Azure Container Apps (React + ASP.NET Core)
             ├─ /api/chat → Foundry agent → protected MCP relay → Fabric Data Agent
             └─ /api/offset-analysis → Fabric SQL serving views
                                                       ↓
                                              Fabric Lakehouse
```

## Evidence scope and limitations

- Offset metrics cover the same **matching whole sections**; footage is not
  prorated by measured depth.
- Run-configuration and operational-event context is aggregated **by well**,
  not restricted to those matching sections. Do not treat it as same-run or
  same-section evidence.
- The reference brief is descriptive. It does not transfer a reference well's
  footage, duration, or ft/hour to the target, predict target performance, or
  recommend drilling parameters. Missing information remains unavailable
  rather than being inferred.
- Planned targets use fictional surface coordinates in a local feet-based
  frame. Surface proximity does not establish subsurface proximity or
  geological equivalence.

## Run locally

Prerequisites: Python 3.13, Node.js 24, and the .NET 10 SDK. The API-backed
application also needs backend configuration; see
[`src/app/README.md`](src/app/README.md). Never commit local environment files
or credentials.

The root `.gitignore` excludes local dataset releases, virtual environments,
dependency/build outputs, caches, test reports, and secrets. Sanitized
`.env.example`, `.env.sample`, and `.env.template` files may be versioned.
Deployment plans and evidence under `.azure/` remain eligible for versioning;
review snapshots and logs for credentials and personal information before
staging them. Ignore rules do not remove files already tracked by Git.

From the repository root, install the client dependencies and start the API:

```bash
cd src/app
npm ci --prefix client
npm run dev:server
```

In another terminal:

```bash
cd src/app
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API requests
to the local ASP.NET Core server on port 8080.

To generate a new synthetic v1.2.0 release:

```bash
python3.13 generate_dataset.py --config config/generator_config_v1.2.0.json
```

The generator preserves existing releases and requires the local, immutable
`v1.0.0` reference archive; release files are not tracked in Git. See
[`docs/data-transformation-contract.md`](docs/data-transformation-contract.md)
and the generator tests for release details.

## Validate

From the repository root:

```bash
python3.13 -m pytest -q
```

From `src/app`:

```bash
npm test
npm run lint
npm run typecheck
npm run build
```

## Repository map

| Path | Contents |
| --- | --- |
| `generate_dataset.py`, `src/drillrun_synth/`, `config/` | Deterministic synthetic release generator and versioned configurations |
| `fabric/`, `scripts/` | Fabric notebook, SQL serving views, and supporting tools |
| `src/app/` | Containerized web application, APIs, client, and app-specific setup |
| `docs/`, `tests/` | Data/analysis contracts and project validation |

For the API contract and offset workflow details, see
[`docs/contracts/offset-well-analysis-v2.md`](docs/contracts/offset-well-analysis-v2.md)
and [`src/app/client/README.md`](src/app/client/README.md). The hosted app is
deployed separately; a repository change is not live until it has been
validated and deployed.
