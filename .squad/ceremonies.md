# Ceremonies

> Focused gates for interfaces, evidence, safety, and continuous improvement.

## Design Review

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before |
| **Condition** | Multi-agent work changes shared interfaces, methodology, or evidence contracts |
| **Facilitator** | Sung Jinwoo |
| **Participants** | Relevant data, model, backend, frontend, and validation owners |
| **Time budget** | focused |
| **Enabled** | yes |

**Agenda:**
1. Review scope and distinguish exploratory choices from approved requirements.
2. Agree on interfaces, versions, provenance, and prediction-time feature contracts.
3. Identify leakage, reproducibility, explainability, security, and integration risks.
4. Assign owners without collapsing independent validation into authorship.

---

## Evidence Gate

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before presenting analytical results |
| **Condition** | Model, similarity, uncertainty, or data-quality evidence is proposed for demonstration |
| **Facilitator** | Baek Yoonho |
| **Participants** | Baek Yoonho, artifact owners, and Fact Checker for external claims |
| **Time budget** | focused |
| **Enabled** | yes |

**Agenda:**
1. Verify dataset, generator, split, feature-availability, and model versions.
2. Confirm whole-well and scenario holdouts, leakage defenses, and transparent baselines.
3. Check aggregate untouched-case results and uncertainty coverage.
4. Separate synthetic workflow evidence from claims requiring representative real-well validation.
5. Reject unsupported claims. The original author is locked out from revising a rejected artifact; the coordinator assigns a different qualified agent and Baek Yoonho re-reviews.

---

## Pre-Ship Review

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | before user-facing artifacts finalize |
| **Condition** | UI, report, API contract, model evidence, or external factual claim is ready |
| **Facilitator** | Sung Jinwoo |
| **Participants** | Baek Yoonho, Rai, Fact Checker, and relevant artifact owners |
| **Time budget** | focused |
| **Enabled** | yes |

**Agenda:**
1. Confirm synthetic labels, provenance, limitations, and baseline views are visible.
2. Require Baek Yoonho's independent evidence verdict for analytical claims.
3. Require Fact Checker verification for factual claims and citations.
4. Require Rai review. A Red verdict blocks shipment and triggers strict reviewer-rejection lockout: a different agent revises, Rai guides the revision, and Rai re-reviews.

---

## Retrospective

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | after |
| **Condition** | Build failure, test failure, evidence rejection, or reviewer rejection |
| **Facilitator** | Sung Jinwoo |
| **Participants** | all involved |
| **Time budget** | focused |
| **Enabled** | yes |

**Agenda:**
1. Establish facts and evidence.
2. Identify root cause.
3. Record the required process or control change.
4. Assign follow-up work.

---

## Retrospective with Enforcement

| Field | Value |
|-------|-------|
| **Trigger** | auto |
| **When** | weekly |
| **Condition** | No retrospective log in `.squad/log/` within the last 7 days |
| **Facilitator** | Sung Jinwoo |
| **Participants** | all |
| **Time budget** | focused |
| **Enabled** | yes |
| **Enforcement skill** | retro-enforcement |

At round start, apply the `retro-enforcement` skill. In a future Git repository, action items become tracked issues; in this folder-backed non-git workspace, record them in the available work tracker without initializing Git.
