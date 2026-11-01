# Squad Decisions

## Active Decisions

### 2026-10-23T09:33:40.483-04:00: Initialize the approved Weatherford Synthetic Data POC squad
**By:** Weatherford Drilling History Agent
**What:** Initially establish six Solo Leveling specialists plus Scribe, Ralph, Rai, and Fact Checker. Keep the work at approved setup only; do not implement the POC.
**Why:** The source brief defines an exploratory synthetic-data analytical demonstrator and requires a strict distinction between simulated workflow evidence and real-world validation.

### 2026-10-23T09:33:40.483-04:00: Preserve independent evidence review
**By:** Weatherford Drilling History Agent
**What:** Baek Yoonho independently reviews data and model evidence. Rejections invoke reviewer lockout and require a different qualified agent to revise. Rai Red verdicts use the same strict rejection semantics.
**Why:** The POC must not certify its own evidence or turn synthetic results into unsupported operational claims.

### 2026-10-23T13:50:03.369-04:00: Use Microsoft Fabric as the target data platform
**By:** Weatherford Drilling History Agent
**What:** Build the POC for Microsoft Fabric, using a Fabric Lakehouse and OneLake/Delta-oriented architecture. SQL remains an implementation convenience where Fabric supports it, but SQL Server is not the primary platform.
**Why:** The intended outcome is to establish a path into Fabric. Designing directly for Fabric avoids a later platform migration and validates the target operating model during the POC.

### 2026-10-23T13:50:58.101-04:00: Assign Microsoft Fabric ownership to a dedicated specialist
**By:** Weatherford Drilling History Agent
**What:** Add Go Gunhee as Microsoft Fabric & Lakehouse Architect instead of expanding Woo Jinchul's role. Go Gunhee owns Fabric target architecture and Lakehouse platform concerns; Woo Jinchul retains drilling-domain schemas and synthetic-data ownership.
**Why:** Fabric platform architecture requires dedicated ownership while preserving clear boundaries between drilling semantics, platform design, implementation, model methodology, presentation, and independent validation.

### 2026-10-23T13:58:26.155-04:00: Approve the security, agent-engineering, and operations squad expansion
**By:** Weatherford Drilling History Agent
**What:** Add Thomas Andre as Cloud Security, Identity & Data Governance Architect; Beru as Microsoft Foundry Agent & Orchestration Engineer; and Igris as DevSecOps, SRE & FinOps Engineer. Preserve Sung Jinwoo's end-to-end architecture and scope ownership, Go Gunhee's Fabric topology ownership, Woo Jinchul's drilling and synthetic-data semantics, Choi Jong-In's similarity and prediction methodology, Yoo Jinho's backend/API integration, Cha Hae-In's UI and user-facing activity receipt, Baek Yoonho's independent empirical evidence authority, and the existing local Squad state backend.
**Why:** The POC needs explicit specialist ownership for cross-service security and governance, Microsoft Foundry agent engineering, and production-oriented operational controls without diluting existing domain boundaries or independent review.

### 2026-10-23T13:58:26.155-04:00: Set architecture status to CONDITIONAL PASS
**By:** Weatherford Drilling History Agent
**What:** Architecture status is **CONDITIONAL PASS — not approved for implementation**. This expansion authorizes governance and team-definition work only. It does not authorize application implementation or the creation of Azure, Microsoft Fabric, or Microsoft Foundry resources. The synthetic-only evidence guard remains active, and Baek Yoonho retains independent evidence authority.
**Why:** Nine cross-cutting decisions remain unresolved and must be recorded, reviewed, and accepted before implementation can begin.

### 2026-10-23T13:58:26.155-04:00: Require preview acceptance and an exit strategy
**By:** Weatherford Drilling History Agent
**What:** Use current GA capabilities by default. Before any preview capability enters the design, record the business need, risk acceptance, affected dependencies, fallback or replacement path, migration trigger, owner, and exit timeline.
**Why:** Preview dependencies can change or be withdrawn and therefore require explicit acceptance and a practical route back to supported GA behavior.

### 2026-10-23T13:58:26.155-04:00: Select the primary conversational layer before implementation
**By:** Weatherford Drilling History Agent
**What:** Record which approved surface is the primary conversational layer, its user and channel scope, its authentication context, and its handoff contract with the backend before implementation. Start with one orchestrator; every additional agent must be justified against a simpler tool or deterministic service.
**Why:** A single primary layer and one-orchestrator-first design prevent duplicated behavior, fragmented policy enforcement, and unnecessary agent complexity.

### 2026-10-23T13:58:26.155-04:00: Define delegated identity, OBO, and RLS
**By:** Weatherford Drilling History Agent
**What:** Thomas Andre must define the Microsoft Entra application architecture, delegated and on-behalf-of token flow, managed identities, least-privilege RBAC, Conditional Access integration points, token boundaries, and row-level security propagation. Managed identity is the default; secrets are prohibited in code and configuration, and Key Vault is allowed only when identity-based access is unavailable.
**Why:** User identity and authorization must survive each service boundary without shared credentials, privilege expansion, or loss of row-level policy context.

### 2026-10-23T13:58:26.155-04:00: Define a deterministic and versioned prediction tool contract
**By:** Weatherford Drilling History Agent
**What:** Choi Jong-In owns the scoring methodology and version semantics; Yoo Jinho owns the backend transport contract; Beru owns the agent tool contract. Prediction must be produced by a deterministic, versioned scoring tool that returns structured inputs, outputs, model or ruleset version, evidence references, and errors. Agents may invoke and explain it but must never generate the prediction number.
**Why:** Separating deterministic scoring from language generation preserves reproducibility, auditability, and methodological ownership.

### 2026-10-23T13:58:26.155-04:00: Separate the user-visible activity receipt from restricted operational traces
**By:** Weatherford Drilling History Agent
**What:** Cha Hae-In owns a curated, comprehensible user-visible activity receipt. Igris owns access-controlled operational traces used for diagnosis, reliability, and cost analysis. Define the correlation identifiers and safe field mapping between them without exposing hidden prompts, credentials, sensitive telemetry, or internal reasoning.
**Why:** Users need understandable provenance while operators need richer diagnostics; combining the two would either leak sensitive internals or weaken operations.

### 2026-10-23T13:58:26.155-04:00: Define network and region policy
**By:** Weatherford Drilling History Agent
**What:** Thomas Andre and Sung Jinwoo must record approved deployment regions, data-residency constraints, private endpoint and VNet/DNS patterns, public-network access posture, egress allowlists and exfiltration controls, cross-region flow restrictions, and disaster-recovery region rules before implementation.
**Why:** Cross-service boundaries among Entra, Fabric, Foundry, application services, and observability must satisfy security and residency requirements by design.

### 2026-10-23T13:58:26.155-04:00: Set latency and cost budgets
**By:** Weatherford Drilling History Agent
**What:** Igris must define measurable end-to-end and component latency budgets, token/tool/step limits with Beru, capacity and quota assumptions with Go Gunhee, per-question cost measurement, allocation tags, budget alerts, and degradation or refusal behavior before implementation.
**Why:** Agentic and analytical workflows need explicit limits to remain responsive, capacity-aware, and financially governable.

### 2026-10-23T13:58:26.155-04:00: Define evaluation gates
**By:** Weatherford Drilling History Agent
**What:** Baek Yoonho must independently approve measurable evaluation gates for empirical claims; Beru must define agent and tool-contract evaluations; Thomas Andre must define security test gates; Igris must define reliability and release gates. Synthetic-only results cannot satisfy a real-world evidence gate, and rejected evidence remains subject to reviewer lockout.
**Why:** Architecture, agent behavior, analytical evidence, security, and operations require distinct objective gates before promotion.

### 2026-10-23T13:58:26.155-04:00: Define telemetry redaction and retention
**By:** Weatherford Drilling History Agent
**What:** Igris and Thomas Andre must record telemetry data classification, collection minimization, prompt and tool-payload redaction, access controls, retention periods, deletion procedures, residency, auditability, and incident handling before traces are enabled. A dedicated privacy or governance authority may be required when real operator data enters scope.
**Why:** Operational observability must not become an uncontrolled copy of user, drilling, identity, or model data.

### 2026-10-23T14:16:49.015-04:00: Make historical summarization the first milestone
**By:** Weatherford Drilling History Agent
**Revised under reviewer lockout by:** Independent revision owner
**What:** Milestone one is limited to grounded summarization of synthetic historical drilling data in Microsoft Fabric. It includes the data contract, deterministic generator, Fabric ingestion and transformation, governed semantic definitions, summary-question evaluation, citations, synthetic-data disclosure, and a curated activity receipt. Comparable-run retrieval, similarity scoring, and prediction are deferred to later milestones and must not be introduced into milestone-one scope.

Milestone one is not complete until the following objective evidence gate is defined, executed against a frozen build and dataset, and independently approved by Baek Yoonho:

1. Maintain a version-controlled representative question set with question identifiers, scope and authorization context, expected facts, acceptable evidence, deterministic source-query definitions, ambiguity or unanswerability classification, and the dataset/generator version used to establish the expectation.
2. Measure grounded factual correctness by comparing answer claims with the expected facts returned by the deterministic source queries. Report claim-level and question-level results, including mismatches and omissions.
3. Validate every factual citation and provenance reference for resolvability, support of the associated claim, correct source location, and traceability to the exact dataset, generator, semantic-model, and evaluation-set versions.
4. Measure the unsupported-claim/hallucination rate as the number of factual claims not supported by cited deterministic query results divided by all factual claims, with numerator, denominator, and failed examples retained. Use a version-controlled claim-annotation rubric that defines factual-claim boundaries, splits compound claims, handles qualified or hedged statements, distinguishes factual claims from non-factual language, and specifies adjudication and tie-break rules so independent evaluators produce repeatable counts.
5. Measure correct refusal or clarification behavior for questions marked unanswerable, out of scope, or ambiguous. The expected action and any required clarification must be specified per question before execution.
6. Test authorization isolation with positive and negative access cases. Any answer, citation, activity receipt, trace, or error that discloses data prohibited for the evaluated identity is an invariant hard-gate failure: unauthorized disclosure must be zero.
7. Test reproducibility and consistency by repeating each applicable question under a documented fixed configuration and recording whether factual claims, citations, refusal decisions, and material conclusions remain consistent. Runs, settings, and observed variations must be retained.
8. Measure end-to-end latency and per-question cost for every evaluation run, reporting distribution statistics, component timing where available, token/tool usage, capacity assumptions, and the calculation method. Acceptance budgets remain pending the separately approved latency and cost decision.
9. Verify that every user-visible answer and activity receipt derived from synthetic data contains the required synthetic-data disclosure. Missing or misleading labeling is an invariant hard-gate failure.
10. Publish the versioned evaluation inputs, deterministic expected results, run outputs, scoring calculations, failures, and evidence package for independent Baek Yoonho review. Baek's explicit approval is required; self-attestation or aggregate scores without inspectable evidence do not pass.

Weatherford and Baek Yoonho must approve the numerical acceptance thresholds for factual correctness, citation/provenance validity, unsupported-claim rate, refusal/clarification correctness, reproducibility/consistency, latency, and per-question cost before implementation can be declared complete. No Weatherford business-quality threshold is implied by this decision. Until those thresholds and the other applicable architecture decisions are approved, architecture remains **CONDITIONAL PASS — not approved for implementation**, and implementation is unauthorized.
**Why:** Historical summarization provides the smallest end-to-end test of Fabric organization, semantic grounding, authorization, answer quality, provenance, and agent integration without prematurely coupling the POC to predictive methodology or model evidence. The measurable evidence gate prevents a summary-only milestone from being accepted on subjective demonstrations while reserving business-quality thresholds for explicit Weatherford and independent Baek approval.

### 2026-10-23T15:22:42.974-04:00: Authorize the narrow Microsoft Fabric development bootstrap
**By:** Weatherford
**Authorization evidence:** At 2026-10-23T15:02:09.372-04:00, the user explicitly said, "lets proceed with the fabric setup. I have created the fabric capacity and I am admin, the same user is logged in via the azure cli locally. What should our next steps be". After the existing `fabricwelladvisorcusmx01` F8 capacity in Central US was discovered and disclosed, the user selected **Create a shared development workspace now (Recommended)** and later selected **Defer Git integration until after the first data load**.
**Revised under reviewer lockout by:** Independent revision owner
**What:** The user approved setup-only implementation for the following resources on the existing Central US F8 capacity:

- Shared development workspace `ws-welladvisor-drillrunhistory-poc-dev`, ID `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, assigned to existing capacity `fabricwelladvisorcusmx01`, capacity ID `137a8cdc-ae73-4239-b40a-04aee386ca5f`.
- Schema-enabled Lakehouse `lh_drillrun_summary`, ID `964afbf5-6a33-46dc-98c1-be726d0f4999`.
- Provisioned SQL endpoint, ID `7d5ceff0-e27e-4459-9ca7-37043dd3e91c`.
- Bootstrap notebook `nb_00_bootstrap_lakehouse`, ID `84b72b28-9e3e-4554-bc82-af86b945fc15`, attached to the Lakehouse.
- Empty Lakehouse schemas `raw`, `curated`, and `serving`.

The user accepted deferring Git integration until after the first data load. The two failed notebook runs were implementation/debugging attempts. The latest idempotent run, `ea219983-beed-427e-ac3c-ded7afaee3f3`, completed successfully. No data was created or loaded.

This narrow authorization supersedes the earlier no-resource-creation restriction only for the resources and setup actions listed above. The global architecture status remains **CONDITIONAL PASS**. This decision does **not** authorize data loading, synthetic generator implementation, a validation workspace, a deployment pipeline, Fabric IQ or Data Agent, Foundry agents, a custom UI, real operator data, production claims, prediction, or broader Azure resources.

Temporary single-user administrator access is acknowledged as a bootstrap exception. Group-based RBAC and an automation identity must be resolved before collaborative development or CI/CD.

Before the first data load, each of the following must have a recorded and approved decision:

1. Synthetic-data contract and provenance.
2. Permitted fields.
3. Data classification and retention.
4. Confirmation that Central US residency is permitted for the data.
5. Summary measures and questions.
6. Evaluation thresholds.
7. External sharing and egress.
8. Workload and cost limits.
9. Data-load owner.

**Why:** The user's explicit selections authorized a bounded, empty Fabric development foundation on an existing capacity, but did not resolve the governance, data, security, cost, evaluation, or implementation decisions required for loading data or building the POC.

### 2026-10-23T15:46:54.574-04:00: Authorize the narrow local synthetic generator and release
**By:** Weatherford
**Authorization evidence:** The user explicitly authorized proceeding with Fabric setup and selected the shared development workspace. The user then selected **Core drilling summary: wells, sections, runs, footage, duration, formation, bit/BHA, and data-quality counts (Recommended)** as the first dataset scope. After that selection, the coordinator explicitly announced that Woo Jinchul would define the run-level contract and generate the first reproducible 100-well, 10-year synthetic dataset, with Baek Yoonho validation before any Fabric upload. The user did not revoke or narrow that announced action.
**Revised under reviewer lockout by:** Independent revision owner
**What:** This decision narrowly supersedes the earlier implementation prohibition only for local implementation and independent validation of the selected synthetic core-drilling-summary dataset. It authorizes local generator source code and configuration, tests, manifests, schema and data-dictionary artifacts, and an immutable CSV release. It also authorizes Baek Yoonho to independently validate that local release under reviewer lockout.

The completed local release `data/releases/v1.0.0/` contains synthetic summary data only: 100 wells, 274 sections, 937 runs, and 20 intentional data-quality issues. Its scope is run/section-level historical summary data only. It contains no 1 Hz data, prediction, real operator data, or production evidence. Local tests passing 7/7 are implementation evidence, not Baek approval and not evidence of Fabric readiness.

This authorization does **not** authorize uploading data to Microsoft Fabric, building curated or serving tables, Git initialization or integration, creating a validation workspace, building agents or a UI, prediction, real data, or production claims. It creates no additional Fabric or Azure resource authority. The existing setup-only Fabric authorization remains unchanged.

Before any Fabric upload, the following must still be explicitly approved and recorded:

1. Permitted fields and the fictional identifier policy.
2. Data classification and retention.
3. Confirmation that Central US residency is permitted for the data.
4. External sharing and egress policy.
5. The data-load owner.
6. Workload and cost limits.
7. Summary evaluation criteria.
8. Baek Yoonho's explicit approval of release `data/releases/v1.0.0/`.

Architecture remains **CONDITIONAL PASS**. This local authorization does not satisfy or waive any independent evidence, security, cost, residency, or release gate.
**Why:** The user's dataset selection and the coordinator's explicit, unrevoked statement of the next action authorized a bounded local generator/data-contract implementation and independent review, but did not authorize a data load or any downstream Fabric, application, predictive, real-data, or production work.

### 2026-10-23T20:15:21.366-04:00: Approve synthetic-data governance and authorize one cryptographically bounded initial raw load
**By:** Weatherford
**Revised under reviewer lockout by:** Independent revision owner; Sung Jinwoo is locked out of this revision after Thomas Andre's rejection.
**Authorization evidence:** The user explicitly approved Central US storage, the classification **Internal — Synthetic POC; no real operator data**, indefinite retention for reuse, disabled external sharing with exports restricted to project administrators, the current authenticated project administrator as the manual first-load owner, and one bounded load on the existing F8 capacity. The user also confirmed that the existing shared development workspace, capacity, and Lakehouse bootstrap remain narrowly approved.
**What:** The following pre-upload governance decisions are approved:

- **Residency:** Central US is approved for storage of this synthetic POC dataset.
- **Classification:** `Internal — Synthetic POC; no real operator data`.
- **Retention:** Retain indefinitely for reuse.
- **Sharing and export:** External sharing is disabled. Exports are restricted to project administrators.
- **Release approval:** Baek Yoonho independently approved `data/releases/v1.0.0/` as the pre-Git canonical release: 100 wells, 274 sections, 937 runs, 20 controlled quality issues, synthetic-only, with no prediction or 1 Hz data. This authorization is bound to release manifest SHA-256 `f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9`, source inventory SHA-256 `0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4`, and aggregate source fingerprint `1e3abd9659b923948c93ba5e28dade20d3f61ed3c92e0111734c94415852edab`.
- **Data controls:** Baek Yoonho independently approved the permitted fields, fictional identifiers, hashes, and source inventory.
- **Pending evidence gate:** Numerical summary evaluation thresholds remain pending and must be approved before user-facing summary quality or business-performance claims.

The exact authorized upload set and verified SHA-256 values are:

| File | SHA-256 |
|---|---|
| `data_dictionary.md` | `912b9a919d4be6ba2ab95dac78bc69f66deec45aa34662cc6fb2413ac481cd26` |
| `drilling_runs.csv` | `499705406f4479196845eb57ebd360afaacaad83551e360243372d782e23d58e` |
| `generator_config.json` | `62020fd960e8c940cbed9a94be572e8acf113ea0602cf3224d1891bb2a61b944` |
| `quality_issues.csv` | `c71d0e7c9cfeac97f047e5988fa75fb780302783628101fbbcaa050f96f9ec75` |
| `release_manifest.json` | `f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9` |
| `schema.json` | `e269e8540d9513d7c45023d18e8ccb3e5ae52646239b46d1076956fdb58d6965` |
| `sections.csv` | `fd6e9e55ea79d2956437fc1384a580359f1379400789e88a55727b8b8f56679b` |
| `source_fingerprint_inventory.json` | `0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4` |
| `split_assignments.csv` | `cf2a3ee384c7a191c0f18f0af7ca5e3b7a70ba1a5534035d5c00c9a6179e4d41` |
| `wells.csv` | `4a71825bf6b99f33fa3fe8f9b5b571c08723d4d768a2d589a1059f2bfcb3c7f3` |

One manual initial upload is authorized to the development Lakehouse only, subject to all of these bounds:

1. Load only the ten files in the authorized set above into `Files/landing/synthetic/drill_run/v1.0.0/` or an equivalent raw landing path in the already-approved development Lakehouse. Upload them byte-for-byte with no transformation, reserialization, enrichment, renaming, or omission; no other file is authorized.
2. The current authenticated project administrator is the manual first-load owner. An automation identity remains mandatory before CI/CD or automated deployment.
3. Use the existing F8 capacity only. Do not enable autoscale or create capacity. Perform one bounded load and record duration and capacity-unit evidence when available.
4. Do not enable external sharing or load real data. Do not build agents, UI, prediction, a validation workspace, or curated/serving transformations without separate explicit authorization.
5. Because retention is indefinite, every release version must remain identifiable, deletion requires explicit approval, and this policy must not be inherited automatically by future real or confidential data.
6. Git remains deferred only through this first load. Immediately afterward, a local and remote Git baseline is a hard gate before any further transformations, agent work, or UI work.
7. Immediately before upload, from the repository root, run the following check against the bytes that will be uploaded. Upload is prohibited unless it exits successfully. Any authorized file hash difference, missing or extra release file, manifest hash difference, inventory hash difference, manifest-listed hash difference, or aggregate source fingerprint difference rejects the upload:

```bash
python - <<'PY'
from pathlib import Path
import hashlib, json

root = Path("data/releases/v1.0.0")
expected = {
    "data_dictionary.md": "912b9a919d4be6ba2ab95dac78bc69f66deec45aa34662cc6fb2413ac481cd26",
    "drilling_runs.csv": "499705406f4479196845eb57ebd360afaacaad83551e360243372d782e23d58e",
    "generator_config.json": "62020fd960e8c940cbed9a94be572e8acf113ea0602cf3224d1891bb2a61b944",
    "quality_issues.csv": "c71d0e7c9cfeac97f047e5988fa75fb780302783628101fbbcaa050f96f9ec75",
    "release_manifest.json": "f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9",
    "schema.json": "e269e8540d9513d7c45023d18e8ccb3e5ae52646239b46d1076956fdb58d6965",
    "sections.csv": "fd6e9e55ea79d2956437fc1384a580359f1379400789e88a55727b8b8f56679b",
    "source_fingerprint_inventory.json": "0474206f9b9a6400243b3542b5ea97d86ba2b78382f66bc3e56716a4c203c9f4",
    "split_assignments.csv": "cf2a3ee384c7a191c0f18f0af7ca5e3b7a70ba1a5534035d5c00c9a6179e4d41",
    "wells.csv": "4a71825bf6b99f33fa3fe8f9b5b571c08723d4d768a2d589a1059f2bfcb3c7f3",
}
aggregate = "1e3abd9659b923948c93ba5e28dade20d3f61ed3c92e0111734c94415852edab"
actual_files = {p.name for p in root.iterdir() if p.is_file()}
assert actual_files == set(expected), (actual_files - set(expected), set(expected) - actual_files)
actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in expected}
assert actual == expected, {name: (expected[name], actual[name]) for name in expected if actual[name] != expected[name]}
manifest = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
inventory = json.loads((root / "source_fingerprint_inventory.json").read_text(encoding="utf-8"))
manifest_artifacts = {name: digest for name, digest in expected.items() if name != "release_manifest.json"}
assert manifest["sha256"] == manifest_artifacts
assert manifest["source_fingerprint"]["value"] == aggregate
assert inventory["aggregate_source_fingerprint"] == manifest["source_fingerprint"]
assert manifest["source_fingerprint_inventory"] == {
    "artifact": "source_fingerprint_inventory.json",
    "sha256": expected["source_fingerprint_inventory.json"],
}
print("PASS: canonical v1.0.0 upload bytes are cryptographically authorized")
PY
```

8. The load evidence record must capture the verified release manifest SHA-256, the SHA-256 of every uploaded file, the exact Fabric workspace, Lakehouse, and destination path, the uploader principal, upload start and end timestamps, and the result. It must also retain the pre-upload check result and record duration and capacity-unit evidence when available. A partial, transformed, hash-mismatched, or otherwise failed upload is not an authorized successful load.

This decision supersedes the prior no-upload restriction only for the single raw landing load described above. It does not broaden the existing Fabric bootstrap authority or approve downstream implementation. Architecture remains **CONDITIONAL PASS**.
**Why:** The user resolved the outstanding pre-upload residency, classification, retention, sharing, ownership, cost-boundary, and independent-release-review decisions sufficiently to permit one controlled raw-data load. Cryptographically binding the authorization to the verified manifest, inventory, aggregate source fingerprint, and artifact hashes closes the rejected path/count-only identification gap while preserving strict synthetic-only scope, no-transform handling, auditability, capacity limits, and downstream implementation gates.

### 2026-10-24T00:20:36Z: Record verified first raw load and local Git baseline
**By:** Weatherford
**Evidence completion timestamp:** `2026-10-24T00:20:36Z`
**What:** The authorized first raw upload of release `v1.0.0` completed in Fabric workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`), Lakehouse `lh_drillrun_summary` (`964afbf5-6a33-46dc-98c1-be726d0f4999`), at `Files/landing/synthetic/drill_run/v1.0.0`.

The uploaded files were downloaded back and every SHA-256 matched the authorized values. The retained evidence is `evidence/first-fabric-load-v1.0.0.json`. No transformations were performed, and the raw, curated, and serving schemas remain empty of tables.

The local Git repository was initialized on branch `main`, with generated releases remaining ignored. The baseline commit is `24c5923` (`chore: establish Fabric POC baseline`), authored by Project requester using his local noreply identity and including the Copilot co-author trailer.

The user deferred selecting a remote. No Git remote or Fabric Git integration exists yet. The prior Git hard gate is satisfied for local source history only; a private remote and Fabric Git integration remain required before collaborative development or CI/CD.

The next authorized boundary is planning and approval for curated and serving transformations. This record does not authorize or claim completion of those transformations. Architecture remains **CONDITIONAL PASS**, and numerical summary evaluation thresholds remain pending.
**Why:** This records the completed, independently verifiable outcome of the previously authorized bounded raw load and the resulting local source-control baseline without broadening authorization. It preserves the remaining collaboration, CI/CD, transformation, and evaluation gates.

### 2026-10-24T00:28:11Z: Authorize summary-only dev transformations under contract
**By:** Weatherford
**What:** Authorize the building and execution of the `raw` → `curated` → `serving` Delta transformations defined by `docs/data-transformation-contract.md`, only in the existing Fabric development workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`) and existing Lakehouse `lh_drillrun_summary` (`964afbf5-6a33-46dc-98c1-be726d0f4999`). Authorization is limited to historical synthetic summary data from the verified raw release `v1.0.0`.

This authorization does not permit prediction, similarity, agents, UI work, a validation workspace, real data, external sharing, new capacity, or production or business-performance claims. The uploaded `v1.0.0` bytes, hashes, manifest, source inventory, and `evidence/first-fabric-load-v1.0.0.json` remain the authoritative source of truth and must not be replaced, repaired, or silently normalized.

Transformations must be deterministic and idempotent; preserve intentional issues and raw/canonical values explicitly; retain synthetic labels and provenance; route records to accepted, quarantined, or rejected outcomes under the contract; and pass complete count, key, relationship, measure, issue, and hash reconciliation. Baek Yoonho must independently approve the contract and the resulting validation evidence before transformed outputs are treated as approved or any completion claim is made. Reviewer lockout applies to a rejection.

The local Git baseline exists. Any new transformation source must be committed locally after successful validation, with no secrets or generated data committed. A private remote and Fabric Git integration remain separate prerequisites for collaborative development or CI/CD, not for this narrowly authorized dev-only execution.

This decision narrowly supersedes prior implementation and downstream-transformation prohibitions only for the dev-only Delta scope above. All other architecture and evidence gates remain in force, architecture remains **CONDITIONAL PASS**, and pending numerical summary thresholds still block user-facing quality or business-performance claims.
**Why:** The verified raw load and local Git baseline satisfy the prior gates for a bounded transformation milestone. Constraining execution to one existing development Lakehouse, one cryptographically identified synthetic release, deterministic summary-only outputs, explicit issue preservation, reconciliation, independent approval, and post-validation source control permits useful progress without expanding into predictive, real-data, production, sharing, capacity, agent, or UI scope.

### 2026-10-24T02:11:22Z: Record completed summary transformation and SQL serving views
**By:** Weatherford Drilling History Agent
**What:** The authorized synthetic, summary-only transformation for release `v1.0.0` is complete in the existing Fabric development workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`) and Lakehouse `lh_drillrun_summary` (`964afbf5-6a33-46dc-98c1-be726d0f4999`).

The full transformation and publication job `a8268bc5-fe2b-4476-89e3-68c3e8f6d6bd` succeeded, followed by successful idempotent rerun `1cc048c8-97ca-4c18-b334-073c24265558`. The active release is `v1.0.0:f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9` with registry status `READY`. Both publication attempts succeeded, complete evidence rows were persisted using evidence schema `v1.0.0`, and the publication lock was released with null owner fields.

Reconciled counts are: raw 100 wells, 274 sections, 937 runs, 20 quality issues, and 0 rejected records; curated 100 wells, 274 sections, 932 runs, 5 quarantined runs, 20 quality issues, and 0 rejected records; serving 100 well summaries, 1 dataset summary, 4 quality summaries, and 19 category summaries.

The SQL analytics endpoint (`7d5ceff0-e27e-4459-9ca7-37043dd3e91c`) is synchronized. All 17 source-controlled public views are present and all active-release verification counts match. Runtime compatibility commit `4393d2f` and SQL views commit `c37bb53` are applied; the current source contains the final approved publication controls; and the full local suite has 43 tests. Two earlier full jobs failed before publication and created no tables; later temporary diagnostics were cleaned.

Durable evidence is recorded at `evidence/fabric-summary-publication-v1.0.0.json`. This completion is development-only, synthetic, and summary-only. It does not claim or authorize prediction, similarity, agents, a Fabric Data Agent, a Power BI semantic model, a user interface, real data, production readiness, or business performance. Architecture remains **CONDITIONAL PASS**. Numerical summary answer-quality thresholds and remote Git/Fabric Git integration remain pending.
**Why:** This records the verified, idempotent transformation and SQL serving outcome without broadening the approved scope. The retained job, release, reconciliation, publication-control, evidence-hash, SQL inventory, and source-control facts provide durable local audit evidence while preserving the unresolved answer-quality and collaborative source-control gates.

### 2026-10-24T17:51:05Z: Authorize one governed summary semantic model and evaluation proposal
**By:** Weatherford
**Authorization evidence:** After the approved Fabric summary publication was recorded, the user explicitly instructed the team to proceed to the next step and specified the authorized and prohibited scope captured below.
**What:** Authorize local, source-controlled development of one summary-only semantic model and deployment of that single model to the existing Fabric development workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`). The model may use only the verified active-release `serving` SQL analytics endpoint views in endpoint `7d5ceff0-e27e-4459-9ca7-37043dd3e91c`, as evidenced by `evidence/fabric-summary-publication-v1.0.0.json`. Read-only verification queries, model refresh testing, and metadata validation are authorized. Drafting an objective summary-answer question set and proposed numerical evaluation thresholds is also authorized.

The semantic model must:

1. Define every user-facing measure explicitly and include a clear description for each measure and business-facing field; implicit measures are prohibited.
2. Hide technical keys and other implementation-only fields from report-facing use while retaining only the relationships and traceability needed for validation.
3. Preserve conspicuous `Internal — Synthetic POC; no real operator data` labeling and summary-only/development-only scope in model metadata and descriptions.
4. Record traceability to dataset release `v1.0.0`, active release ID `v1.0.0:f27ad627a06a2b554ae359e9aceb682944f1a4becb2de330f5ece629d407fed9`, the semantic-model source version, and any later evaluation-set or release version used.
5. Use only read access to the verified `serving` views for development and validation. This authorization does not permit mutation of published Lakehouse data or expansion to unverified sources.

The existing governance controls remain binding: Central US residency; classification `Internal — Synthetic POC; no real operator data`; indefinite retention for reuse; external sharing disabled; exports restricted to project administrators; and no secrets. This authorization does not permit a Fabric Data Agent, Foundry agents, custom UI, prediction, similarity, a validation workspace, real data, external sharing, new capacity, production-readiness or business-performance claims, or public release.

Baek Yoonho must independently review and explicitly approve both the deployed model and the proposed objective question set and numerical threshold package before any Fabric Data Agent work may be authorized or begun. Reviewer lockout applies to a rejection. Drafting thresholds does not approve them, and no user-facing answer-quality claim is permitted until the applicable thresholds and evidence are approved.

A private remote Git repository and Fabric Git integration remain pending. This narrow authorization permits local source-controlled model development and one bounded dev deployment, but it does not authorize collaborative development, CI/CD, or treating the Fabric workspace as the source of truth.
**Why:** The verified, idempotent summary publication and synchronized serving views provide a bounded source for the next development step. Limiting work to one documented semantic model, explicit measures, hidden technical keys, synthetic labeling, release traceability, read-only validation, and an independently reviewed evaluation proposal advances the summary milestone without entering agent, predictive, real-data, production, sharing, capacity, or public-release scope.

[Personal identity details redacted in sanitized publication snapshot.]

Fabric import succeeded after parser compatibility, relationship cardinality, relationship endpoint, object name-collision, and synthetic-label corrections. Live DAX reconciliation returned 100 wells, 274 sections, 937 source runs, 932 accepted runs, 5 quarantined runs, 0 rejected records, 20 data-quality issues, 909010.2 total footage, 22358.76 total duration, and label `SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`. Durable metadata and reconciliation evidence is retained at `evidence/fabric-semantic-model-v1.0.0.json`.

Weatherford approved these provisional gates for a future evaluation: zero critical factual, scope, or security failures; at least 95% citation validity; at least 90% correct clarification or refusal behavior; 100% repeat consistency; and end-to-end p95 latency no greater than 15 seconds. Per-question cost must be measured before a ceiling is approved.

This records metadata and DAX reconciliation only. It does not claim that model or agent evaluation has been executed or passed. No report, Fabric Data Agent, Foundry agent, custom UI, similarity capability, or prediction capability was created. Architecture remains **CONDITIONAL PASS**.
**Why:** Recording the exact deployed resource, source boundary, source commits, corrected import history, deterministic live results, and approved provisional gates creates durable audit evidence without converting deployment verification into an unsupported answer-quality, production-readiness, or business-performance claim.

### 2026-10-24T19:12:37Z: Approve the semantic model and governed evaluation package
**By:** Weatherford Drilling History Agent
**Independent reviewer:** Baek Yoonho — **APPROVE**
**What:** Record completion and independent approval of the bounded semantic-model/evaluation phase. The deployed model is `sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`) in workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. It remains DirectQuery and uses only `serving.well_summary`, `serving.dataset_summary`, `serving.quality_summary`, and `serving.category_summary`.

Live DAX remains reconciled at 100 wells, 274 sections, 937 source runs, 932 accepted runs, 5 quarantined runs, 0 rejected records, 20 issues, 909010.2 accepted footage, 22358.76 accepted duration, and label `SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY`. Final semantic source history runs through commit `21cd98f`; the repository log is authoritative for the preceding parser, relationship, collision, and label corrections.

The final governed evaluation set is commit `b65bc6a619a50d22cc931fd4c480d809063941f7`. It contains 36 balanced cases (12 answerable, 12 clarify, and 12 refuse/security), 102 authorized source references with zero unresolved references, and exact hashed governance provenance. Validation passed with 77 tests plus 51 subtests and successful official TOM/TMDL validation. Durable approval evidence is `evidence/summary-evaluation-approval-v1.0.0.json`.

The approved thresholds remain provisional calibration gates: zero critical factual, scope, or security failures; citation validity at least 95%; clarification/refusal correctness at least 90%; repeat consistency 100%; and p95 end-to-end latency no greater than 15 seconds. Per-question cost must be measured during calibration before a ceiling is approved.

This approval covers the deployed semantic model and the governed evaluation package; it is not evidence that a Fabric Data Agent has been created or calibrated. No Fabric Data Agent, Foundry agent, report, UI, prediction capability, or real data exists. Architecture remains **CONDITIONAL PASS**. The next authorization boundary is either Fabric Data Agent creation and calibration or remote Git/Fabric Git integration.
**Why:** The deployed model, deterministic reconciliation, balanced evaluation contract, citation allowlists, immutable governance provenance, validation results, and independent approval satisfy the authorized semantic-model/evaluation milestone while preserving the separate authorization required for agent creation, calibration, collaborative source control, and any broader capability or production claim.

### 2026-10-24T20:37:52Z: Authorize one bounded Fabric Data Agent and calibration
**By:** Weatherford
**Authorization evidence:** The user explicitly selected creation and calibration of a Fabric Data Agent against the approved semantic model `sm_drillrun_summary`.
**What:** Authorize creation of exactly one Fabric Data Agent in the existing development workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`), connected only to semantic model `sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`). The agent must use the requesting user's identity and permissions with least privilege; a shared broad service identity is prohibited.

The agent is summary-only. Its instructions must conspicuously state that all data is synthetic and for a development historical-summary POC, preserve the semantic model's four-serving-view boundary (`serving.well_summary`, `serving.dataset_summary`, `serving.quality_summary`, and `serving.category_summary`), and include the approved caveat that category results are subject to the model's quarantine treatment and must not imply coverage of quarantined records.

Authorize bounded calibration using only the approved, source-controlled 36-case evaluation set and the approved provisional thresholds: zero critical factual, scope, or security failures; citation validity at least 95%; clarification/refusal correctness at least 90%; repeat consistency 100%; and p95 end-to-end latency no greater than 15 seconds. Capture latency, factual correctness, citation validity, clarification/refusal behavior, consistency, and cost or usage where Fabric exposes it. Calibration may reveal failures. No milestone pass, answer-quality claim, production-readiness claim, or business-performance claim may be made unless Baek Yoonho independently reviews and approves the retained evidence.

Only read-only queries through the bounded semantic model are permitted. This authorization does not permit write or action tools; direct raw or curated access; prediction or similarity; operational advice; external sharing; Foundry-hosted agents; a custom UI; a validation workspace; new capacity; real data; or any source beyond the four approved serving views exposed through `sm_drillrun_summary`.

The Fabric Data Agent's source, configuration, and instructions must be exported or otherwise captured in source control after creation and before any broader work. This decision narrowly supersedes the prior Fabric Data Agent prohibition only for the single dev agent and bounded calibration described above. All other governance controls remain in force, and architecture remains **CONDITIONAL PASS**.
**Why:** The semantic model and governed evaluation package have been independently approved, allowing a tightly bounded read-only agent calibration while preserving identity, data-source, synthetic-evidence, reviewer, source-control, cost, and scope controls.

### 2026-10-24T22:32:57Z: Approve calibration-only Data Agent pre-creation security posture
**By:** Weatherford
**Authorization evidence:** The user explicitly approved the identity, source, access, geography, isolation, retention, and hard-gate posture recorded in `docs/data-agent-security-posture.md` and `evidence/data-agent-precreation-security-v1.0.0.json`.
**What:** Approve a single-user calibration sandbox in which only Project requester, Microsoft Entra principal `61a37498-9ab6-43d2-b70f-706fd58274e7`, may create, configure, access, use, or calibrate the Fabric Data Agent. The agent may use exactly one read-only source: semantic model `sm_drillrun_summary` (`ee7583b6-5be7-4802-83a8-530ce7dd8351`) in workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. No sharing, guests, organization-wide links, external integrations, service principals, Foundry exposure, Copilot Studio exposure, or Microsoft 365 exposure are permitted. The original prohibition on publication and API use was later narrowly superseded by commit `c77749d` only for unshared publication and the approved local MCP calibration runner.

RLS and OLS are not required for this calibration because all 100 wells and all fields are fictional/internal synthetic data fully authorized for the sole calibrator. Hidden fields are not security controls. No real, customer, operator, segmented, or multi-user data may enter without a new review. Central US is within the United States, so cross-geo AI processing/storage settings are not required for this capacity. The user confirmed the required tenant and capacity Copilot settings are enabled.

Each test must use a clean conversation. Grader-only governance evidence, scoring keys, and expected answers must never enter agent context. Local calibration questions, prompts, responses, measurements, and results are retained for 90 days with access limited to the calibrator and reviewer, then deleted; tokens and secrets are never retained. Microsoft-controlled service retention remains governed by Microsoft terms and is outside repository control.

Creation remains blocked until the complete agent definition and instructions are source controlled and the designated reviewer approves them and this posture. This tightens the earlier post-creation source-capture requirement: source control is now a pre-creation gate. After creation and before calibration, verify the exact single source and the item/relevant-workspace ACL. Failure of source isolation, identity/ACL controls, or any hard gate requires disabling or deleting the agent unless approved remediation is applied and fully retested. This repository update does not modify Fabric. Architecture remains **CONDITIONAL PASS**.
**Why:** The approved posture makes the sole calibrator, one-source boundary, synthetic-only RLS/OLS exception, non-exposure rules, test isolation, retention ownership, and fail-closed response explicit while preserving independent review and live post-creation verification as mandatory gates.

### 2026-10-24T22:43:41Z: Pass Data Agent pre-creation gates and authorize bounded creation
**By:** Weatherford Drilling History Agent
**Independent reviewer:** Baek Yoonho — **APPROVE** at commit `deaf23db97f248101d3ba8cb84ec7c867d4b6299`
**What:** Record that all pre-creation gates for the single bounded Fabric Data Agent now pass. The corrected source-controlled definition uses the dedicated Data Agent API, has exactly one semantic-model source (`sm_drillrun_summary`) and four selected tables, and is draft-only with no sharing, actions, few-shots, or published configuration. Full validation passed with 84 tests, 51 subtests, and the official JSON schemas.

[Personal identity details redacted in sanitized publication snapshot.]

The user confirmed that Copilot/Azure OpenAI is enabled for the account and that capacities can be designated as Fabric Copilot capacities. Central US is inside the United States; current Microsoft documentation applies the cross-geo processing/storage settings to capacities outside the United States or European Union, so those settings are not required here. The previously approved single-user, no-RLS/no-OLS, 90-day local calibration-retention posture remains in force.

Creation of the single bounded draft Data Agent is now authorized. Architecture remains **CONDITIONAL PASS**, and calibration remains unauthorized until post-creation verification confirms the exact semantic-model source and the agent item/relevant-workspace ACL. Any source or ACL mismatch requires disabling or deleting the agent unless approved remediation is applied, fully retested, and reapproved.
**Why:** The approved definition, independent review, exclusive live workspace ACL, confirmed tenant settings, approved geography, and recorded security posture satisfy every pre-creation gate while retaining mandatory fail-closed post-creation verification before calibration.

### 2026-10-24T22:47:00Z: Record bounded Data Agent creation and pass post-creation source and ACL checks
**By:** Weatherford Drilling History Agent
**What:** Record successful creation of draft Fabric Data Agent `da_drillrun_summary` (`72a3a511-ad36-4df8-842b-d6c268b2ff8a`) in workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. Creation operation `efb93d35-b38e-492f-84cd-163bee6cd38e` succeeded at `2026-10-24T22:45:38.9391024Z`.

The live definition remains draft and unpublished. It contains only `Files/Config/data_agent.json`, `draft/stage_config.json`, `draft/semantic-model-sm_drillrun_summary/datasource.json`, and Fabric-generated `.platform`; no published parts, `publish_info`, few-shots, or actions exist. The live definition hashes are recorded in `evidence/fabric-data-agent-creation-v1.0.0.json`.

The post-creation source gate passes. The agent has exactly one `semantic_model` source: model `ee7583b6-5be7-4802-83a8-530ce7dd8351` in workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, with selected tables exactly `Wells`, `Dataset Metadata`, `Data Quality`, and `Categories`. The live source configuration matches the approved source; Fabric only normalized each table element by adding `children: []`. All approved security and scope instructions and identifiers match.

The post-creation ACL gate passes. The item access API returned exactly Project requester (`61a37498-9ab6-43d2-b70f-706fd58274e7`), `User`, with `Read`, `Write`, `ReShare`, and `ReadAll`, and no other principal. The workspace ACL was reverified as the same sole `User`/`Member` with `Admin`; no guests, groups, service principals, or other users are present.

Creation is complete, but calibration has not started. No questions were sent, and no publish, MCP endpoint, or sharing occurred. Commit `c77749d` later authorized unshared publication for the approved local MCP runner, superseding the earlier publication prohibition. Calibration remains unauthorized until the post-publication Q1-Q5 gates pass and receive designated-reviewer approval.

Any later source or ACL regression requires disabling or deleting the agent unless an explicitly approved remediation is applied, followed by complete retest and reviewer reapproval. Architecture remains **CONDITIONAL PASS**.
**Why:** Durable post-creation evidence proves that the created draft item preserves the approved one-source boundary and exclusive single-user access without converting creation into calibration, publication, broader exposure, or a quality claim.

### 2026-10-24T22:56:25Z: Authorize unshared publication solely for automated MCP calibration
**By:** Weatherford
**Authorization evidence:** The user explicitly authorized publishing the existing Fabric Data Agent solely to expose its MCP endpoint to the local automated calibration runner.
**What:** Authorize publication of existing Fabric Data Agent `da_drillrun_summary` (`72a3a511-ad36-4df8-842b-d6c268b2ff8a`) without changing its source, instructions, or ACL. Project requester, Microsoft Entra principal `61a37498-9ab6-43d2-b70f-706fd58274e7`, must remain the sole item and workspace principal. The published MCP endpoint may be used only by the local calibration runner authenticated as Project requester.

Calibration is limited to the approved 36 cases. Every case must use a clean MCP session and conversation. Grader-only evidence, scoring keys, and expected answers must remain isolated from agent context. Local calibration questions, prompts, responses, measurements, and results are retained for 90 days with calibrator/reviewer-only access and then deleted; tokens and secrets are not retained.

Publication does not authorize sharing, guests, links, groups, service principals, Foundry, Copilot Studio, Microsoft 365, custom or ordinary-user UI integration, actions, writes, additional sources, direct raw or curated access, real data, prediction, similarity, operational use, or access by ordinary users. It does not authorize changing the existing definition, source, instructions, or ACL.

After publication and before sending any question, reverify the complete live definition, exact semantic-model source and selected-table boundary, item ACL, and workspace ACL. Any source or ACL mismatch, definition drift, or other hard-gate failure requires an immediate stop and disablement, unpublication, deletion, or explicitly approved remediation followed by complete retest and independent re-review before calibration may proceed.

This decision narrowly supersedes the previous prohibition on publication and programmatic invocation only for this unshared, single-user, local MCP calibration path. Publishing is not production approval, general-release approval, a quality claim, or authorization for broader integration or use. Architecture remains **CONDITIONAL PASS**.
**Why:** Automated execution of the already approved 36-case calibration requires the Fabric Data Agent's MCP endpoint. A tightly bounded, unshared publication preserves the approved single-user identity, source, ACL, isolation, retention, and fail-closed controls while enabling reproducible calibration without authorizing production or broader exposure.

### 2026-10-24T23:59:30Z: Pass Data Agent prepublication gates and bind post-publication question blocks
**By:** Weatherford Drilling History Agent
**Authorization evidence:** User publication exception commit `c77749dc1844a7303fbc2dff210d3f5abcbfd87c` and the user's temporary sole-user Admin/model Write/ReShare exception.
**Independent reviews:** Baek Yoonho — **APPROVE** for the publication-ready definition from `e06ab02b0055e14258a26dfd88a2cbe31d2a68bc` plus `b6332182ea2049eeb4408f3b6c9ab1b33a1777f3`; Thomas — final **APPROVE** for runner commits `b740e14ecfd8cd08b38b880f7de54244473c49f6`, `b0aaa77763027e6a7bb763a8112f85a8fde516ab`, and hardened `1578b2e4d8c23c1019484bef4ebfb50dde0d10a0`.
**What:** Record that every prepublication gate for existing draft Data Agent `da_drillrun_summary` (`72a3a511-ad36-4df8-842b-d6c268b2ff8a`) passes. The agent remains draft and unpublished. The user authorizes publishing it unshared only for automated MCP calibration by the sole user, with no external integrations, actions, or additional sources and rollback on failure.

The publication-ready draft and published definitions are semantically identical, use exactly one semantic-model source and four tables, contain no few-shots, actions, or extra sources, and produce the exact `updateDefinition` and `staging/publish` requests. Baek Yoonho approved this result after 95 tests, 51 subtests, and official-schema validation.

The fixed-target read-only runner passed Thomas's shell-capable final review in a fresh virtual environment: 27 calibration tests passed, Bandit reported zero findings, pip-audit reported no vulnerabilities, schemas were valid, and the worktree was clean.

[Personal identity details redacted in sanitized publication snapshot.]

Set `publication_authorized_now` to true because all prepublication gates pass. Keep `calibration_authorized_now` false. After publication, Q1 published-definition diff, Q2 ACL reverification, Q3 unauthenticated/wrong-token/current-user authorization, Q4 capability inventory, and Q5 evidence safety remain pending, block every question, and require designated-reviewer approval.

Local calibration artifacts remain subject to 90-day retention with calibrator/reviewer-only access and deletion afterward. No claim is made about Microsoft-controlled service retention. Any hard-gate failure requires immediate stop and disablement or safe unpublication where available, with deletion as the mandatory fallback, unless approved remediation is completely retested and independently re-reviewed. Architecture remains **CONDITIONAL PASS**.
**Why:** The exact publication authority, reviewed immutable definition, hardened read-only runner, and live sole-user identity/ACL evidence now support the narrowly bounded publication step without authorizing calibration questions, broader permissions, sharing, or production use.

### 2026-10-25T00:08:31Z: Stop calibration before any question after MCP preflight failure
**By:** Weatherford Drilling History Agent
**What:** Preserve the published calibration attempt for historical Data Agent `72a3a511-ad36-4df8-842b-d6c268b2ff8a` as a fail-closed event. Run `20261025T000831Z-fc192489` stopped with `STOP_REQUIRED` reason `preflight_failure` before any question, agent tool call, or calibration case was sent. The valid MCP tool inventory was rejected locally because MCP SDK wire field `inputSchema` is exposed by the Python SDK as `input_schema`; teardown then wrapped the failure in an `ExceptionGroup`. No answer-quality, tool-capability, calibration, or production claim may be inferred from this run.
**Why:** The runner correctly prevented an unvalidated session from reaching the agent, but the local schema adapter defect made the published item unusable for authorized calibration and activated the approved rollback path.

### 2026-10-25T00:08:54Z: Record approved deletion rollback and preserve the deleted ID as immutable evidence
**By:** Weatherford
**What:** Record the approved deletion of historical Data Agent `72a3a511-ad36-4df8-842b-d6c268b2ff8a` at `2026-10-25T00:08:54Z`, request ID `c4f2a6c5-ee5d-48c9-b9a9-a78d01d0433d`. A subsequent list operation verified that no Data Agents remained. The old ID and its creation, publication, preflight, and deletion records are immutable historical evidence and must not be rewritten as though the item never existed. The existing fail-closed deletion fallback remains unchanged.
**Why:** Deletion was the mandatory fallback after the hard-gate failure and removed the published calibration surface without erasing the audit trail.

### 2026-10-25T00:19:33Z: Record remediated Data Agent recreation with authorization reset
**By:** Weatherford Drilling History Agent
**Independent remediation review:** Commit `8abece2090620becf882089ad3d37b0427c9e982` — **APPROVE** after 120 tests plus 51 subtests, Bandit, and pip-audit.
**What:** Record successful recreation of `da_drillrun_summary` as new draft Data Agent `961c0db2-e7c4-42f8-887c-039085290338`. Creation operation `ccddbdd1-d002-4465-b25c-9afe2edee27a` succeeded. The approved draft definition, workspace, model, and source selection are unchanged; the description is calibration-only. The new item is draft, unpublished, and unshared.

The prior publication/calibration exception does not automatically authorize the replacement item. Set `publication_authorized_now` and `calibration_authorized_now` to false for the new ID. Publication and calibration authorization may transfer only after repository source identifiers are updated for the new ID, the live definition/source and item/workspace/model ACLs are reverified, all applicable tests and hard gates pass, and the designated reviewers explicitly approve the retained evidence. No question may be sent before those approvals.

The old ID remains immutable historical evidence. Architecture remains **CONDITIONAL PASS**, and the fail-closed deletion fallback is unchanged.
**Why:** Recreation restores a bounded draft after the independently approved local MCP adapter remediation, but a new Fabric item has a new identity and live state that must earn authorization through complete verification and independent review rather than inheriting approval by assumption.

### 2026-10-25T07:51:12.344-04:00: Adopt mandatory Fabric Data Agent with deterministic Foundry orchestration
**By:** Weatherford
**Authorization evidence:** The user explicitly directed that Fabric Data Agent is mandatory and integral to the larger application, selected a hybrid architecture with one Foundry orchestrator/application layer, required visible Data Agent failures and validated Data Agent contribution for normal answers, and imposed a local mock proving-spike gate before any new Data Agent or Foundry deployment.
**What:** Adopt a hybrid conversational architecture with an explicit control-plane/data-plane boundary. Fabric Data Agent is the mandatory analytics specialist and governed analytical data plane; it is not an optional implementation detail and may not be silently bypassed or replaced by a general model, direct query path, cached answer, or alternate analytics engine. One Foundry orchestrator/application layer is the control plane and deterministically owns request classification and routing, clarification and refusal policy, the mandatory response envelope and exact synthetic-data label, evidence-citation requirements, the user-visible component trace, and final validation. No second orchestrator or alternative analytical answer path is permitted without a new recorded architecture decision.

A normal analytical answer—including a summary, paraphrase, derived factual statement, or other response a user could reasonably interpret as an analytical result—is permitted only when the Fabric Data Agent contributes successfully and the orchestrator validates that contribution against the response contract, authorization and scope rules, citation requirements, required label, and trace requirements. Citation validation must use the approved source allowlists and governance provenance, confirm resolvability, and verify that each cited source supports its associated claim. Data Agent timeout, unavailability, refusal, malformed output, missing or invalid evidence, or validation failure must remain visible in the response envelope and component trace. In those cases the orchestrator must clarify, refuse, or return an explicit unavailable/failed status; it must not manufacture or silently substitute a normal analytical answer.

The component trace must remain curated, minimized, access-appropriate, and redacted under the existing activity-receipt and telemetry decisions. It may identify approved components, status, correlation identifiers, validation results, and safe evidence references, but must not expose hidden prompts, credentials, tokens, raw restricted payloads, sensitive telemetry, internal reasoning, or unnecessary topology details.

The decision is calibrated by the failed v1.0.1 run `20261025T013559Z-2808cabd`: 36 cases × 3 attempts, 108 successful invocations, 13 critical factual failures, 19 scope violations, 42 incorrect expected behaviors, 141 citation claims with 123 present and 12 valid, 87.234% citation presence, 8.511% citation validity, 50% clarification/refusal correctness, 88.889% repeat consistency, 31.836999-second p95 latency, exact synthetic label on 108/108 outputs, zero security disclosures, and cost unknown. The failed agent `a23346c3-1ce7-4203-8ecf-9b9982c82a03` was deleted at `2026-10-25T02:06:17Z`; the subsequent list verified that no Data Agents remain. Historical deleted-agent records remain immutable evidence.

Before any new Fabric Data Agent or Foundry resource is created, published, or deployed, a local mock proving spike must demonstrate deterministic routing; mandatory Data Agent participation for normal analytical answers; orchestrator-owned clarify/refuse behavior; the mandatory response envelope and exact label; allowlist-based resolvable and claim-supporting evidence citations; a minimized and redacted component trace; validation pass/fail behavior; and visible fail-closed handling with no silent replacement when the mocked Data Agent fails. The spike must also capture component latency and an attributable local cost/usage proxy so timeout and budget behavior can be tested; an approved measurable cloud cost ceiling remains mandatory before deployment because prior calibration cost is unknown. The spike must use source-controlled tests and retained reviewable evidence and must receive independent approval. Passing the spike authorizes no cloud deployment by itself; a separate explicit deployment decision and the existing identity, ACL, source, security, cost, and evaluation gates still apply.

`publication_authorized_now`, `calibration_authorized_now`, and `questions_authorized_now` remain false. No Fabric Data Agent or Foundry deployment is authorized. Because no Data Agent currently exists, normal analytical responses through the governed conversational application are disabled; only explicit clarification, refusal, or unavailable/failed responses are permitted. The approved data layer, SQL views, semantic model, and evaluation specification remain approved for their previously recorded bounded purposes, but that approval does not authorize an ordinary-user conversational query path, application go-live, or production use. Architecture remains **CONDITIONAL PASS**.
**Why:** The prior calibration proved reliable invocation, labeling, and security isolation but failed factual, scope, citation, refusal, consistency, latency, and cost-readiness gates. Keeping Data Agent as the governed analytics specialist preserves its required role, while deterministic orchestration centralizes policy and validation that should not depend on specialist model behavior. A local failure-path spike is the least-cost way to prove the integration contract before recreating cloud resources.

### 2026-10-25T09:50:08.125-04:00: Approve gated Central US Microsoft Foundry provisioning baseline
**By:** Weatherford
**Authorization evidence:** The user approved a new Central US Microsoft Foundry account and project in existing resource group `rg-welladvisor-mx01`, rejected reuse of the Sweden Central projects, and selected the security, identity, operational, and deployment gates below.
**What:** Preserve Fabric Data Agent as a mandatory and integral component of the hybrid architecture. The source-controlled local proving-spike lineage exists in commits `e508f1d`, `24110cb`, `07dfbe8`, and `6d2517e`. No Fabric Data Agent is currently deployed, so governed normal analytical answers remain unavailable and may not be silently replaced by another analytical path.

Provisioning design must target a new Microsoft Foundry account and project in Central US within existing resource group `rg-welladvisor-mx01`. Existing Sweden Central Foundry projects must not be reused. Demo simplicity and low operational overhead are preferred only within the mandatory security baseline: Foundry Managed VNet/outbound isolation plus a private endpoint. Public access is disabled by default and may not replace the private endpoint. If public access is technically required for the bounded demo, it must be an explicitly documented, time-bounded exception restricted to the current developer IP and removed after the demo; unrestricted public access is prohibited.

Use a system-assigned managed identity and least-privilege RBAC. No secrets, keys, or credentials may be committed to the repository. This provisioning phase does not authorize a model deployment, hosted agent deployment, Fabric Data Agent creation, or application deployment.

Include POC-appropriate diagnostics and monitoring, ownership and budget tags, and source-controlled Bicep. Provisioning execution remains blocked until the Bicep build and Azure what-if pass; required quota, provider registration, RBAC, and policy checks pass; and the independent architecture, security, cost, and implementation reviews approve the retained evidence. This decision authorizes recording and preparing the governed provisioning baseline, not executing a deployment before those gates pass. Architecture remains **CONDITIONAL PASS**.
**Why:** A new in-region Foundry control plane avoids accidental dependence on the Sweden Central projects while retaining a low-overhead demo posture. Managed network isolation, private connectivity, managed identity, least privilege, monitoring, cost ownership, source control, preflight checks, and independent review keep the POC bounded and auditable before any cloud resources or application components are deployed.

### 2026-10-25T18:05:54Z: Record secure hybrid and Foundry foundation readiness with external deployment block
**By:** Weatherford
**Authorization and implementation lineage:** The mandatory Data Agent hybrid architecture is recorded at commit `1e306dee`; the deterministic local orchestrator was hardened through commit `6d2517e`; and the secure Foundry foundation IaC and validator were finalized at commit `1ed13c6e7dac0529a62111e1ad994b2c4fdea3af`.
**What:** Preserve Fabric Data Agent as the mandatory and integral governed analytical data plane and one deterministic Foundry orchestrator as the control plane. The reviewed Central US foundation uses a bring-your-own VNet; private Foundry and private dependencies; Azure Firewall with controlled Fabric MCP egress; Standard Agent Setup dependencies and capability host; private monitoring; separate foundation and finalize phases; and exact RBAC, ABAC, and live validation.

Code readiness is **APPROVED**. Final security review found 0 Critical, High, Medium, or Low findings. Validation passed 252 tests plus 51 subtests, strict mypy, Bandit with no medium/high findings, clean dependency audits, Bicep build/lint/parameter/security checks, and resolution of all 82/82 custom-role actions. Azure validation and what-if passed for foundation and finalize at both `Provider` and `ProviderNoRbac` levels, with 58 planned foundation changes and 11 planned finalize changes. These are validation results only; no deployment occurred.

Deployment authorization remains **BLOCKED externally** because the current principal inherits subscription Contributor and User Access Administrator through a group, the exact phase-scoped JIT/PIM custom-role assignments are absent, and signed seven-day cost and teardown approval is absent. No foundation was deployed, so postdeployment gates cannot run. Human governance and identity owners must provide a dedicated deployment principal without the broad inherited roles and supply the signed approval. After that, rerun predeploy and deploy foundation only. Do not deploy a model, Fabric Data Agent, hosted agent, application, or finalize phase until the applicable postdeployment gates pass.

No Fabric Data Agent is live; all prior failed agents were deleted. The approved data layer and semantic model remain deployed, while conversational deployment remains disabled. Architecture remains **CONDITIONAL PASS**.
**Why:** The source, IaC, validators, and retained validation evidence now establish an approved secure foundation design, but source readiness cannot substitute for least-privilege deployment identity, time-bounded cost/teardown authorization, or live postdeployment proof. The external governance block must therefore fail closed without weakening the mandatory Data Agent architecture or authorizing cloud deployment.

### 2026-10-25T20:00:12Z: Record provider-fix validation and hold foundation retry for review
**By:** Weatherford
**Validation lineage:** Provider-fix commit `716f1d8c7c9566813a25ce9a80292bb6d5e3fa65`; sanitized evidence `evidence/foundry-foundation-predeploy-716f1d8.json`; stable deployment name `foundry-foundation-20261025-r2`.
**What:** The external identity and cost prerequisites recorded in the prior decision are now satisfied for the bounded foundation phase. The dedicated service principal preflight passed after the live foundation custom role was synchronized to the reviewed 90-action source, the subscription-scoped RBAC auditor was active, and the reviewed JIT schedules were active. The approved fixed-cost ceiling is $400 against the $280 estimate, with expiry `2026-10-31T20:00:00Z`. Approval artifacts, identity identifiers, and JIT references remain external and are not committed.

The initial `r2` attempt failed before full foundation creation on reviewed provider-contract errors. Storage, Cosmos DB, four NSGs, the route table, and the Azure Firewall public IP succeeded and remain as partial resources. Commit `716f1d8c7c9566813a25ce9a80292bb6d5e3fa65` adds the exact linked-resource permissions, removes the deprecated firewall DNS property, and corrects the Search Entra-only provider contract. Full validation passed with 285 pytest tests plus 51 subtests, strict mypy, Bandit with only the unrelated low-severity deterministic synthetic RNG finding, clean pip-audit, and Bicep restore/build/lint/build-params/diff.

Azure `validate` at `Provider` level succeeded under the dedicated identity. Target `Provider` what-if for the stable `r2` deployment reports 49 Create, 6 NoChange, 2 Modify, and 0 Delete, Replace, or Unsupported. The two Modify entries are reviewed server-populated/read-only drift: Cosmos properties and the public IP's server-generated `ddosSettings`/`ipTags` omitted by the template. Neither changes security, public access, networking intent, or tags. No existing Fabric capacity is deleted or changed. The live custom roles remain exact to reviewed source and the JIT schedules remain active.

There is still **no successful foundation deployment**. This decision records validation evidence only and does not authorize the retry. The incremental foundation retry remains pending independent reviewer approval. Finalize, model, Fabric Data Agent, hosted agent, and application deployment remain unauthorized until the foundation retry succeeds and the mandatory live postdeployment gate passes. Architecture remains **CONDITIONAL PASS**.
**Why:** The provider fix and dedicated-identity validation demonstrate that a stable incremental retry can converge the reviewed partial deployment without delete/replace behavior or changes to existing Fabric capacity. Holding execution for independent approval preserves the fail-closed governance boundary and prevents validation evidence from being misrepresented as a successful deployment or deployment authorization.

## Governance

- Agents submit cross-team decisions through `.squad/decisions/inbox/`; Scribe merges them here.
- Architectural decisions belong here; personal learnings belong in agent histories.
- Independent reviewer findings are not resolved by consensus alone; they require remediation evidence and re-review.

### 2026-10-26T12:30:00-04:00: Adopt Fabric-only POC and retire Foundry control plane
**By:** Project requester
**What:** The milestone architecture is now exclusively `authorized named
Fabric user -> Fabric Data Agent -> semantic model -> Fabric Lakehouse/SQL`.
The Foundry account, project, capability host, runtime assignments, Storage,
Cosmos DB, Search, firewall, virtual network, private endpoints, DNS,
monitoring, deployment service principal, and custom roles have been deleted.
Fabric capacity `fabricwelladvisorcusmx01` is the only remaining resource in
the resource group and is paused.

Retire the Foundry infrastructure, deployment and validation scripts, evidence,
custom hybrid orchestrator, dedicated schemas and fixtures, dependencies, and
tests from the active repository while preserving their Git history. No
Foundry model, hosted agent, custom orchestrator, alternate analytical path, or
retired network/JIT/ABAC validator is part of the milestone.

Keep the deterministic synthetic generator, Fabric Lakehouse notebook and SQL,
summary semantic model, Fabric Data Agent definition, calibration and
evaluation assets, and relevant contracts. Access is limited to explicitly
approved named Fabric users; no secrets may enter source. The scope remains
synthetic, development-only, and summary-only, with the exact synthetic label
required on every response. Capacity may be resumed only for an approved,
budgeted window with a pause plan. Publication, calibration, scope expansion,
and milestone release each require explicit approval; repository validation
alone grants none of them.
**Why:** The dedicated Foundry estate has been torn down and the milestone no
longer needs a separate control plane. Removing its active implementation and
governance surface leaves one smaller architecture aligned with the remaining
Fabric assets and approved POC scope.

### 2026-10-26T11:07:20-04:00: Authorize contained Fabric Data Agent calibration milestone
**By:** Project requester
**What:** Limit the next live milestone to exactly these actions:

1. resume `fabricwelladvisorcusmx01`;
2. create one unshared `da_drillrun_summary` Fabric Data Agent;
3. bind only semantic model `sm_drillrun_summary`
   (`ee7583b6-5be7-4802-83a8-530ce7dd8351`);
4. publish the agent for its MCP endpoint;
5. run the complete calibration from zero; and
6. pause the Fabric capacity after the run.

No Foundry, network architecture, private endpoints, data-security platform
work, prediction, similarity, UI, backend orchestration, additional source,
sharing, or unrelated implementation is authorized. This is a synthetic,
development-only POC. Keep only the minimal existing controls needed to avoid
secrets in source, bind the named Fabric user and exact semantic model, retain
the synthetic label, and prevent accidental scope expansion.
**Why:** The user explicitly requested a tightly contained POC execution and
corrected the prior tendency to expand network and data-security controls
beyond what synthetic-data calibration requires.

### 2026-10-26T11:22:48-04:00: Bind calibration approval to recreated Data Agent
**By:** Project requester
**What:** The authorized contained milestone created and published exactly one
unshared Fabric Data Agent:
`db727a5a-7e57-46c1-8fb1-81b2babed8f3`
(`da_drillrun_summary`) in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. It is bound only to semantic model
`ee7583b6-5be7-4802-83a8-530ce7dd8351`.

This exact UUID is the approved value for both `--data-agent-id` and
`--approved-data-agent-id` during the preflight and the complete from-zero
calibration run. No other Data Agent, source, sharing change, or workload is
authorized. Capacity must be paused after the run or any failure.
**Why:** The calibration runner intentionally has no default agent ID. Recording
the newly created live UUID closes the explicit runtime/approval binding
without broadening the contained milestone.

### 2026-10-26T16:49:06Z: Contained Data Agent calibration failed and rolled back
**By:** Project requester
**What:** Published Data Agent `db727a5a-7e57-46c1-8fb1-81b2babed8f3`
completed a fresh 36-case by 3-attempt run with 108 successful invocations.
Offline scoring returned `FAIL_ROLLBACK_REQUIRED`: 17 critical factual
failures, 19 scope violations, 12.568% citation validity, 38.889%
clarification/refusal correctness, 66.667% repeat consistency, and 44.652471
seconds p95 latency. The exact synthetic label passed 108 of 108 outputs and
there were zero security failures.

The agent was deleted, a subsequent list verified zero Data Agents, and Fabric
capacity was paused. Publication, questions, and calibration are no longer
authorized. The Fabric data layer, SQL views, semantic model, evaluation
specification, and Fabric-only architecture remain approved.
**Why:** The contained milestone completed exactly the authorized work. The
Data Agent still does not meet the factual, citation, scope, consistency, or
latency quality gates, so it must not remain live or be treated as a passed
conversational POC.

### 2026-10-26T13:02:58-04:00: Recreate Data Agent for interactive Fabric testing
**By:** Project requester
**What:** Recreate exactly one unshared draft Fabric Data Agent for direct
interactive testing in the Fabric UI. The live item is
`2c3241d4-07b7-4531-9038-642ca03014cb`
(`da_drillrun_summary`) in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, bound only to semantic model
`ee7583b6-5be7-4802-83a8-530ce7dd8351`.
Leave the item unshared and draft-only for user exploration. Do not publish,
calibrate, delete, add sources, or expand scope without a new request.
**Why:** The prior calibrated item was correctly deleted after failing quality
gates, but the user explicitly requested a new item they can see and exercise
manually in Fabric.

### 2026-10-26T13:44:31-04:00: Create Fabric IQ ontology experiment
**By:** Project requester
**What:** Create preview ontology `ont_drillrun_summary_test`
(`4f1096c2-02ca-4dc6-b831-3ddb66180483`) in workspace
`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`. The item is an isolated experiment for
generating ontology context from `sm_drillrun_summary`; it does not replace the
semantic model or modify the existing draft Data Agent.

Populate the ontology through its built-in Ontology Agent using only the
existing semantic model. Keep the proposed Fabric Ontology & Semantic
Knowledge Architect role deferred unless the customer approves a later
refinement milestone.
**Why:** The Ontology preview tenant setting became available after propagation,
and the user explicitly authorized creating the ontology with the existing
team.

### 2026-10-26T14:30:45-04:00: Connect drill-project prompt agent to Fabric Data Agent
**By:** Project requester
**What:** Use existing Foundry account `foundry-sandbox-swc-mx01` in
`rg-client-sandbox-eus2-mx01` and create child project `drill-project`.
Projects and project-child connections/agents necessarily inherit the parent
account's resource group. Keep all standalone Weatherford workload resources
in `rg-welladvisor-mx01`; that resource group continues to contain only Fabric
capacity `fabricwelladvisorcusmx01`.

Reuse existing GA model deployment `gpt-5.4-mini`. Create prompt agent
`welladvisor-fabric-orchestrator` version 1 with a `fabric_iq_preview` tool
connected to published Fabric Data Agent
`2c3241d4-07b7-4531-9038-642ca03014cb`. The remote-tool connection uses
delegated `UserEntraToken`, audience
`https://analysis.windows.net/powerbi/api`, and scope
`DataAgent.Execute.All`. Tool use is required for drill-run questions.

The smoke test successfully discovered and called
`DataAgent_da_drillrun_summary`, returning 100 wells with the exact synthetic
label. The mistakenly created resource group
`rg-welladvisor-agent-poc-7c9a31` was deleted. Evaluation-suite creation was
explicitly deferred.
**Why:** This provides the requested Foundry-to-Fabric orchestration with no
new standalone infrastructure, reuses the customer's existing Foundry account
and model deployment, and uses the replacement Fabric IQ integration instead
of the retiring legacy Fabric Data Agent tool.

### 2026-10-26T14:36:23-04:00: Add visual result formatting to Foundry orchestrator
**By:** Project requester
**What:** Create `welladvisor-fabric-orchestrator` version 2 with the same
required Fabric IQ Data Agent tool and grounding rules, plus visual
presentation instructions. Multiple metrics use compact Markdown KPI tables;
small comparisons can use tables and text bars; single values use emphasized
KPIs. Visuals must retain exact values, units, and semantic-model sources and
must not introduce independent calculations or unsupported trends.

The smoke test returned the correct 100 wells, 274 sections, 937 source runs,
932 accepted runs, and 5 quarantined runs in a compact visual panel.
**Why:** The user requested more visual output in the Foundry playground while
preserving Fabric-grounded factual behavior.

### 2026-10-27: Approve the v1.1.0 synthetic proximity-data expansion
**By:** Project requester
**What:** Approve v1.1.0 synthetic-data expansion with proximity-capable, fictional wellhead locations and distinct planned-target rows. Keep the coordinate frame local and fictional, preserve the v1.0.0 archive unchanged, and limit this work to data and related documentation/tests; no UI work is authorized. Coordinates are synthetic test data, not real well locations or evidence of operational validity.
**Why:** Proximity scenarios and separate planned targets can be represented in the synthetic data while preserving the prior release and the data-only scope.

### 2026-10-27T15:08:05-04:00: Authorize one bounded v1.1.0 raw landing upload
**By:** Project requester
**What:** Authorize one manual, byte-for-byte raw landing upload of the exact 11 manifest-listed files from `data/releases/v1.1.0/` to `Files/landing/synthetic/drill_run/v1.1.0/` in workspace `ws-welladvisor-drillrunhistory-poc-dev` (`4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`), Lakehouse `lh_drillrun_summary` (`964afbf5-6a33-46dc-98c1-be726d0f4999`). The approved maximum capacity window is 15 minutes; stop on any upload/verification error, do not retry, and pause the existing F8 capacity after completion or failure. Do not transform, activate, expose, rename, or delete data; no serving/model/Data Agent/UI changes are included. The user explicitly waives the source-control baseline gate only for this one raw upload because the local v1.1.0 source baseline is uncommitted and no remote is configured. Do not represent this as source-controlled or as approval for subsequent transformations, UI work, agent work, or other deployments.
**Why:** The v1.1.0 synthetic release is approved for the next bounded data step while preserving the old v1.0.0 release and limiting the source-control exception to this exact upload.

### 2026-10-27T16:35:04-04:00: Authorize bounded read-only verification of the v1.1.0 landing
**By:** Project requester
**What:** Authorize resuming the existing F8 capacity for one bounded window of up to 15 minutes solely to diagnose the v1.1.0 remote listing mismatch and verify the exact remote filenames and file hashes against the local manifest. Pause the capacity after the attempt or on any error. Do not upload, overwrite, transform, rename, expose, or delete any data; if verification shows that remote repair is required, stop and obtain separate explicit authorization.
**Why:** The previous upload returned successful create/append/flush responses for all 11 files, but the post-upload listing comparison failed and recorded no remote names or hashes. The user explicitly authorized resuming the capacity to fix the verification issue and accepted the billing.

### 2026-10-28T09:35:53-04:00: Approve Offset Well Analysis milestones M1 and M2
**By:** Project requester
**What:** Approve execution of milestones M1 and M2 in `plan/feature-offset-well-analysis-1.md`, including the proposed GUD-001–005 defaults and the distinct, separately bounded read-only and staged cloud operations defined in those tasks. Pause and verify the existing F8 capacity after each authorized window. This does not authorize full production implementation, broad source exposure, publication/activation, deployment, commit, push, or operations beyond the stated M1/M2 gates.
**Why:** The Offset Well Analysis is a critical POC feature; first establish the local data/API contract and prove the governed Fabric path and bounded staged feasibility before committing to the production slice.

### 2026-10-28T11:09:39-04:00: Prefer least-privilege workload identity for the POC
**By:** Project requester
**What:** The Offset Well Analysis POC does not need per-user Fabric authorization. Prefer a workload identity and the minimum permissions required to meet the approved POC requirements. This is a design constraint, not approval of the currently observed ACA-to-Fabric identity chain or broad grants, and it does not authorize identity/permission changes, live operations, publication, or deployment. The exact principal, source scope, and required grants remain subject to evidence, independent security review, and separate authorization.
**Why:** The POC must avoid unnecessary per-user setup while minimizing access and preserving the existing approval gates.

### 2026-10-28T13:42:05-04:00: Apply the POC identity preference to both Offset and historical Data Agent integration
**By:** Project requester
**What:** Apply the design preference for a non-user-specific workload identity and minimum permissions to both the Offset Well Analysis POC and the historical Data Agent integration. This is a design constraint only. It does not validate or approve the observed ACA-to-Fabric identity chain or broad grants, establish effective source access, authorize identity or permission changes, or authorize live operations, publication, activation, deployment, commit, or push. Exact principal, source scope, and required grants remain unresolved pending evidence, documented platform requirements, independent security review, and separate authorization.
**Why:** The user explicitly selected the same identity design preference for both scopes, while withholding authorization for live changes.

### 2026-10-28T14:59:56.614-04:00: Authorize a local-only synthetic Offset Well Analysis UI preview
**By:** Project requester
**Authorization evidence:** The user selected "Build the synthetic-data UI preview now (Recommended)" after being asked whether to build an explicit synthetic-data preview in the existing app without cloud changes or deployment.
**What:** Authorize local implementation of a clearly separated development-only Offset Well Analysis preview in the existing React application and checkout. Reactivate Cha Hae-In solely for this frontend assignment. Include target selection, proximity/section filters, manual selection of at most five historical wells, and a comparison layout using a version-labelled offline snapshot of the existing synthetic release. This narrowly permits local fixture calculations for the explicit preview; it does not change the required governed analytical path for live functionality or allow silent fallback. Preserve existing historical chat and its disclosure. Keep preview entry points unavailable in production, visibly distinguish planned targets from observed synthetic history, reset stale selections, and disclose that Fabric is not connected and live offset chat is unavailable. Related tests and app documentation are authorized. Do not modify immutable releases, generator provenance, authentication, permissions, cloud resources, deployed configuration, or historical security documentation; no deployment, commit, push, or Git-state mutation is authorized.
**Review:** Sung Jinwoo independently approved this boundary, with no blocking corrections, before implementation. Baek Yoonho must independently review the completed preview.
**Why:** The user needs to see and refine the workflow while live Fabric feasibility remains unresolved. A local preview is not completion of the end-to-end feature or evidence of live integration.

### 2026-10-28T16:13:44.641-04:00: Authorize hosting the offline Offset UI preview on the existing Azure app
**By:** Project requester
**Authorization evidence:** After the local preview was presented as offline synthetic data, the user requested "make sure everything is pushed to azure, provide the url to access".
**What:** Extend the preview assignment to an explicitly enabled hosted offline demonstration on existing Container App `ca-drill-advisor-wfrd-mx01`, resource group `rg-welladvisor-mx01`, using existing registry `acrdrilladvisormx01`. Cha Hae-In may add a default-off build-time opt-in, accurate hosted/offline labels, related tests, Docker build wiring, and app documentation. Igris may build/publish the application image and update only that existing application's image/revision, preserving existing authentication, environment settings, ingress, identity, replica limits, and historical chat behavior. Capture the old image/revision and verify readiness plus the public static preview; restore the prior image if the rollout fails. This authorizes hosting the existing fictional summary snapshot, not raw run exports, live offset functionality, new infrastructure, Fabric resume/query/source/permission changes, Foundry calls, Git commits, or Git pushes. Default builds must continue to exclude the preview unless explicitly enabled. Independently review the code and exposure boundary before rollout.
**Why:** The user wants an accessible Azure URL for the preview. Hosting the offline demo does not fix or authorize the separately gated live analytical integration.

### 2026-10-29T08:41:52.870-04:00: Replacement Data Agent publication and label-failure rollback (consolidated)
**By:** Copilot
**What:** Merge the three 2026-10-25 replacement prepublication, postpublication, and calibration-failure records as historical checkpoints, not current authorization. Following the separately recorded recreation of `961c0db2-e7c4-42f8-887c-039085290338`, source/runner rebinding commit `2db841d68b91b87400db7715e1a87af8ec9545ee` passed 120 tests and 51 subtests; complete identity/source/ACL/definition/runner/security retesting earned the same narrow publication exception for that exact item. Publication succeeded at `2026-10-25T00:32:14Z`, request `3348cf9e-642f-4995-909b-1f24a9b399bf`, unshared and calibration-only.

Postpublication Q1-Q5 passed: six approved definition parts plus `.platform`; matching draft/published single-model/four-table source except Fabric `children: []` normalization; sole Project requester principal `61a37498-9ab6-43d2-b70f-706fd58274e7` on agent/model ACLs with unchanged sole-user workspace evidence; preflight `20261025T003243Z-8128b459` returned 401 for unauthenticated/wrong-token probes and passed the delegated-user handshake; one question tool and no action/admin/write capability; no question or tool call during preflight; safe evidence and identity cleanup with no credentials, raw response bodies, or secret markers persisted. At that checkpoint, questions/calibration remained false pending designated-reviewer approval.

Subsequent calibration `20261025T004054Z-b79eede4` began `2026-10-25T00:40:54.748215Z`, recording 65 attempts across 22 cases: 64 succeeded, then `summary-v1.0.0-C10` attempt 2 failed at `2026-10-25T00:58:04.375033Z` because the synthetic label was missing. No failing response body was retained, no secret/security failure was indicated, and no further case/attempt ran. Result: `FAIL_ROLLBACK_REQUIRED`, not milestone approval. Deletion at `2026-10-25T00:58:30Z`, request `9ddea39f-7684-4725-8af5-fba5eb820441`, was followed by a list verifying zero agents. Sanitized failure evidence is `evidence/data-agent-calibration-failure-20261025.json`, commit `c99a85ac96f1096508f26f9eb93b5b53c4afabc3`.

The terminal checkpoint resets publication/calibration/questions to false. Remediation requires independently revised instructions, a new identity, fresh source/ACL/publication review, preflight, and a complete 36-case × 3-attempt rerun; the 64 successes cannot transfer. Preserve predecessor history, CONDITIONAL PASS, data-layer/model/evaluation approvals, sole-user/no-sharing scope, 90-day local calibrator/reviewer-only retention and deletion, and mandatory fail-closed deletion rollback.
**Why:** Complete retesting can earn identity-specific publication, but publication and objective preflight do not replace designated review or quality gates. A missing mandatory synthetic label requires rollback and a fresh independently reviewed run, not reuse of partial successes.

### 2026-10-29T08:41:52.870-04:00: v1.0.1 Data Agent remediation and failed full calibration (consolidated)
**By:** Copilot
**What:** Merge the four 2026-10-25 v1.0.1 recreation/prepublication/postpublication/failure records as immutable historical evolution. After the predecessor label failure and deletion, independent exact-label remediation commits `d368402ffd41eff3b970678d4f59d3f65c6cfd59` and `f4062d4f4704a154e02970fd49244c7c309aa116` passed 136 tests, 51 subtests, TOM validation, and security review. Creation operation `a305cd2a-e750-4ca0-b315-b08ed0735bf4` created draft, unshared `da_drillrun_summary` v1.0.1, ID `a23346c3-1ce7-4203-8ecf-9b9982c82a03`. At recreation all authorization flags were false; ID rebinding commit `0dc114817bce6402c40c456e1557e0a16a7ffcab` alone granted no authority.

Fresh live verification then matched the approved definition except Fabric `children: []` normalization, exact first-line synthetic-label instructions, sole model `ee7583b6-5be7-4802-83a8-530ce7dd8351`, and tables `Wells`, `Dataset Metadata`, `Data Quality`, `Categories`. Agent/model/workspace ACLs contained only Project requester (`61a37498-9ab6-43d2-b70f-706fd58274e7`); temporary sole-user Admin/model Write/ReShare exception and reviewed runner/security lineage were unchanged. Baek/security approved prepublication with Bandit and pip-audit passing. Only publication for this exact ID became true; calibration/questions still awaited fresh Q1-Q5 and review.

Publication succeeded at `2026-10-25T01:26:55Z`, request `f5663fae-bd87-4846-808d-30f11028a3f8`. Fresh Q1-Q5 verified published source, all three sole-user ACLs, exact label, and preflight `20261025T012704Z-6a32549a`: unauthenticated/wrong-token 401, delegated handshake, exactly one question tool, successful cleanup, no question/tool call, and no credentials/raw response bodies persisted. Baek approved the exact new 36-case × 3-attempt evaluation at `d07d3edd04f634aed680d71cd565760457549efc`; Thomas's substantive final security APPROVE at `d13acd17978199b1a36e558f8d8b34c610e6b126` completed the gates. Questions/calibration became true only for that fresh evaluation while Q1-Q5 remained PASS; no question had been sent at approval.

Run `20261025T013559Z-2808cabd` subsequently completed all 108 invocations without an invocation hard stop. Baek's offline grading found 13 critical factual failures, 19 scope violations, 42 incorrect expected behaviors, and zero security disclosures. Of 141 citation claims, 123 citations were present and 12 valid: presence 87.234%, validity 8.511%. Clarification/refusal correctness was 50%, consistency 32/36 cases (88.889%), p95 latency 31.836999 seconds, and cost UNKNOWN/null. Exact synthetic label passed 108/108 outputs. Result: `FAIL_ROLLBACK_REQUIRED`, not a conversational milestone pass.

Deletion at `2026-10-25T02:06:17Z`, request `3831710c-1a25-4a9f-a267-67afcc2d093e`, was followed by a list verifying zero agents. Sanitized summary: `evidence/data-agent-calibration-failure-v1.0.1.json`; raw run/grading evidence remains local, ignored, uncommitted, and subject to 90-day retention/deletion. At the terminal checkpoint all publication/calibration/question flags were false. Next required root-cause analysis and explicit approval of v1.0.2 remediation or an architecture change; no prior attempt can count toward a future pass. Preserve deleted-agent histories, CONDITIONAL PASS, data-layer/SQL/model/evaluation approvals, no sharing/additional sources/actions/writes, and disable/safe-unpublish/delete rollback.
**Why:** Identity-specific complete retesting and separate review earn only a bounded fresh run. Reliable invocation, exact labels, and no disclosure do not compensate for failed factual, scope, citation, behavioral, consistency, latency, or unknown-cost gates; rollback and explicit future approval remain required.

### 2026-10-29T08:41:52.870-04:00: Historical Foundry JIT corrections and staged retry evidence (consolidated)
**By:** Copilot
**What:** Merge three dated follow-ups to the separately recorded provider-fix checkpoint without treating them as current infrastructure or retry approval. The later Fabric-only teardown decision supersedes these historical estate descriptions.

- `2026-10-25T20:12:04Z`: provider-fix `716f1d8c7c9566813a25ce9a80292bb6d5e3fa65` evidence retained. The Provisioned foundation request and same-named Assigned/Direct/Provisioned instance both expire `2026-10-31T20:00:00Z`; the Provisioned auditor request has the same expiry, but its instance response omits `endDateTime`. This discrepancy is not proof of permanence; standard role-assignment listing is not authoritative for schedule expiry. What-if ignored the existing Fabric capacity, neither changing nor deleting it. Retry still required a corrected independent verdict.
- `2026-10-25T20:43:50Z`: target `92af0579d6c885be4dd73dad49150b81ee58b031`, firewall fix `e5b1c5cc1c5fd0a93596d0df1db08ca6aeb68576`, and postdeployment validator fix passed 290 tests plus 51 subtests, strict mypy, clean pip-audit, no medium/high Bandit findings, and Bicep. Azure validation passed; Provider/ProviderNoRbac what-if each showed 45 Create, 12 Deploy, one ignored Fabric capacity, and zero Modify/Delete/Unsupported. Partial VNet/network controls, firewall policy/rules/public IP, Storage, Cosmos, and Search existed, but no Azure Firewall. `AzureFirewallSubnet` lacked its firewall IP configuration; expected provider assignment `10.40.1.68`, UDR/DNS fail-closed handling, and mandatory postdeployment verification remained. JIT schedules/roles/preflight were active/pass. No post-fix retry had occurred or was authorized without review.
- `2026-10-25T21:46:04Z`: sanitized monitoring-fix target `1bd8ca5fa5129efc1002338901055bf08c92665d` recorded read-only live evidence superseding earlier partial-state descriptions, not erasing them. Firewall was Succeeded; Foundry account/project/four base AAD connections succeeded; Storage, Cosmos, Search, five approved private endpoints, ten DNS zones/links, Log Analytics, Application Insights, AMPLS/private monitoring existed. Project Application Insights connection was still absent; capability host/runtime RBAC absent because only foundation had run. Foundation what-if had one material Create for that connection plus reviewed Deploy/Ignore projections, no Modify/Delete/Replace/Unsupported; finalize validation planned ten expected creates. Validation passed 305 tests plus 51 subtests, strict mypy, pip-audit, Bicep, Azure validate/what-if, and no medium/high Bandit. Fixes enforce exact Application Insights property/metadata allowlists, recursive sensitive-content rejection, and project-managed-identity output semantics. JIT/preflight/cost/teardown window remained active then. Retry still needed independent reviewer approval.

**Why:** Commit-bound evidence and authoritative schedule APIs distinguish bounded assignments and changing partial deployments from permanent grants or a successful foundation. Corrections preserve original failure checkpoints, exact remaining work, and independent retry-time gates; they do not revive the retired estate.

### 2026-10-29T08:41:52.870-04:00: Historical anonymous Drill Advisor directive and source-specific cutover gates (consolidated)
**By:** Project requester (via Copilot), Sung Jinwoo, Go Gunhee
**What:** Merge the 2026-10-26 public directive, blocked cutover, and separate SQL-agent follow-up as historical evolution, not proof of the current identity chain or new TASK-025 authority.

Jason's `2026-10-26T16:10:27.042-04:00` directive required no visitor sign-in/authentication, with keyless Azure service-to-service managed/federated workload identity. Browser tokens, client secrets, API keys, and committed credentials could not replace user authentication. The recorded directive approved a keyless public rebuild including a linked Function App, identity resources, Foundry connection changes, Fabric application identity, and anonymous usage limits; it did not remove the need for successful governed end-to-end results.

Sung Jinwoo's cutover checkpoint allowed deployment of the indexed Function API and activation of Foundry version 4/project-managed-identity MCP bridge, while requiring `PUBLIC_CHAT_ENABLED=false`, `TRUSTED_PLATFORM_AUTH_ENABLED=false`, and `ALLOW_LOCAL_ANONYMOUS=false`. Do not deploy the then-current anonymous frontend, link the Static Web App, or remove rollback assets: the host still served the previous authenticated frontend with no linked backend. Easy Auth, routing, provider-header, federation, and Power BI audience defects had been corrected, but the federated Fabric principal received HTTP 401 when the Data Agent queried `sm_drillrun_summary`. A bridge/tool call alone did not pass the cutover gate.

Go Gunhee's subsequent checkpoint recorded creation/publication of separate `da_drillrun_public_summary` (`dd1cd69f-3b49-4575-932f-1d871f73d2e2`) in workspace `4e1977a8-d7ff-487e-b42d-c4b3bc118f3d`, using only Lakehouse `964afbf5-6a33-46dc-98c1-be726d0f4999` and selected SQL views `serving.dataset_summary`, `serving.well_summary`, `serving.quality_summary`, `serving.category_summary`. The Function relay targeted its published MCP endpoint. Foundry version 4 successfully listed/called the new tool through the federated Fabric service principal, returning reconciled KPI totals and the exact synthetic disclosure. This recorded a separate bounded read-only historical-summary source path; it did not modify the preserved semantic-model Data Agent, ontology, or semantic model, nor attest current effective source permissions or complete public cutover.
**Why:** Public access must remain keyless and fail closed until grounded output and exact disclosure succeed. The semantic-model source failed service-principal authorization; a separate Lakehouse SQL agent addressed that source-specific obstacle without rewriting preserved assets. Historical success cannot resolve today's identity/documentation reconciliation or authorize live changes.

### 2026-10-23: Use release-scoped writes with rollback for summary tables
**By:** Go Gunhee
**What:** The local summary notebook validates and hashes all release data before publication, replaces only the `v1.0.0` partitions, verifies every published table, and restores prior Delta versions (or drops newly created tables) if publication fails.
**Why:** Fabric Delta commits are atomic per table rather than across the full table set. Recording prior versions and rolling back on failure provides contract-aligned failure behavior without introducing unapproved resources or a second publication namespace.

### 2026-10-23: Establish the first deterministic synthetic release contract
**By:** Woo Jinchul
**What:** Dataset `v1.0.0` uses separate well, section, drilling-run, quality-issue, and whole-well split CSVs with canonical feet/hours/inches/UTC units. Every row carries synthetic and generation provenance. Four configured quality scenarios are preserved and explicitly flagged. Releases are immutable under `data/releases/<dataset_version>/`.
**Why:** The summary-only Fabric milestone needs reproducible, inspectable, OneLake-ready data without telemetry, predictions, confidential source data, or ambiguous real-asset identifiers.


### 2026-10-29T08:55:07.992-04:00: Live offset wire/deploy decision merged with final handoff state
**By:** Sung Jinwoo
**What:** Merged the session-specific inbox directive into the active decision log and recorded the final live handoff state: user-approved wire+deploy path remains in place, Fabric stays running, and deployed ACA revision `ca-drill-advisor-wfrd-mx01--0000007` serves the live app URL with image digest `sha256:220cf57b89e14413a7c2221668e6d93fce68e8d02a53e4a0ef256a27265fa3a2`. Data Agent semantic repair now uses a single-target slice to prevent historical-value multiplication and independently verified values remain Cobalt `247512.3` and Driftwood `170381.6`. Frontend fetch-loop remediation (stable singleton defaults + `AppRoot` composition test) is redeployed and independently approved. Security review found no issues. Evidence of record is `evidence/deployment-live-offset-redeploy-20261029.json` and `evidence/fabric_diag/semantic_revision_e2e_20261029_yoojinho.json`; earlier bad evidence is preserved as non-final history. This decision does not mark final browser workflow pass, which remains in coordinator verification.
**Why:** Preserve an accurate, bounded handoff that reflects approved live deployment outcomes without overstating unverified browser completion or altering historical records.

### 2026-10-29: Completed approved image-only ACA rollout
**By:** Igris
**What:** Built `src/app/Dockerfile` in existing ACR as `drill-advisor:comparison-feedback-20261029T190832Z-78802052` (digest `sha256:176c7c8ea04488a066de5650a9f33645cd33b0de9981cf03c02989a5f37c6e49`), then updated only container `drill-advisor` image on `ca-drill-advisor-wfrd-mx01`, producing revision `ca-drill-advisor-wfrd-mx01--0000008`. Preserved identity, ingress, scale, registry wiring, and OFFSET SQL env settings; recorded rollback target revision/image `ca-drill-advisor-wfrd-mx01--0000007` with digest `sha256:220cf57b89e14413a7c2221668e6d93fce68e8d02a53e4a0ef256a27265fa3a2`.
**Why:** User-approved scope required deployment of comparison-feedback UI through image-only rollout while avoiding Bicep/AZD apply and preserving all existing runtime configuration.

### 2026-10-29: Live offset wiring/deployment scope supersedes offline-only restrictions
**By:** Sung Jinwoo
**What:** Jason explicitly selected "Wire and deploy live offset analysis, including required Fabric/Foundry changes" as the active delivery scope. This supersedes earlier offline-preview-only and Foundry-dormant restrictions for this delivery. Operative assignment is: Yoo Jinho (backend/API + Data Agent/Foundry contract wiring), Cha Hae-In (frontend workflow/context UX), Go Gunhee (Fabric source/view/contract readiness), Igris (deployment window, rollback, and capacity controls), with Beru active for Foundry orchestration policy wiring and Baek retaining independent validation authority.
**Why:** The prior milestone framing no longer matched the user-authorized outcome. Team/routing/registry/identity state needed alignment so implementation planning and governance gates reflect the actual live offset target while preserving synthetic-only, fail-closed, and no-commit/no-push constraints.
