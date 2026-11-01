# Foundry IaC Security Review

**Review date:** 2026-10-25  
**Reviewed commit:** `a875258f2a4ba20a4929af3acff9b5eb1715cf8d`  
**Severity:** **MEDIUM**  
**Confidence:** **9/10**  
**Ready for production:** **No**  
**Critical issues:** 0

## Scope

This review covered the Microsoft Foundry infrastructure-as-code changes in:

- `infra/main.bicep`
- `infra/main.bicepparam`

The review focused on network isolation, outbound-egress governance, regional support for Foundry Agent Service, and whether the recorded deployment validation proves the intended security posture. No IaC was changed as part of this review.

## Review plan

1. Verify private ingress and agent-network isolation declarations.
2. Verify deny-by-default outbound enforcement, explicit outbound rules, and approval permissions.
3. Verify that the selected Agent Service networking mode is supported in the deployment region.
4. Compare Bicep build, lint, and Azure what-if results with the claimed security properties.

## Priority 1 (Must Fix) ⛔

### Microsoft-managed agent network is selected but not provisioned

**Finding:** `infra/main.bicep` selects managed-network isolation through the Foundry account's `properties.networkInjections`:

```bicep
networkInjections: [
  {
    scenario: 'agent'
    useMicrosoftManagedNetwork: true
  }
]
```

However, the deployment does not declare the associated `Microsoft.CognitiveServices/accounts/managedNetworks` resource named `default`. It also does not declare the managed network's explicit outbound rules or the required **Azure AI Enterprise Network Connection Approver** role assignment used to approve the private connections required by the isolated agent environment.

In addition, `infra/main.bicepparam` selects `centralus`. According to the current Microsoft region-support documentation, **Central US is not supported for the selected Microsoft-managed VNet Agent Service configuration**.

Account-level settings such as `networkAcls.defaultAction: 'Deny'`, `publicNetworkAccess: 'Disabled'`, and `restrictOutboundNetworkAccess: true` are useful controls, but they do not provision the Agent Service managed network, its private dependency paths, or its governed outbound rules.

### Impact

The template expresses an intent to use Microsoft-managed agent networking without deploying the resources needed to realize and govern that network. If the account/project were treated as ready for hosted agents based only on the account flags, operators could incorrectly assume that agent egress is isolated and explicitly approved.

The unsupported region/configuration combination also prevents the intended Microsoft-managed VNet Agent Service setup from being completed in Central US. Enabling a hosted agent workload before choosing and fully implementing a supported network design would violate the required isolation and egress-governance posture.

### Evidence

- `infra/main.bicep` lines 132-137 select `scenario: 'agent'` with `useMicrosoftManagedNetwork: true`.
- `infra/main.bicepparam` line 3 sets `location = 'centralus'`.
- The reviewed IaC contains no `Microsoft.CognitiveServices/accounts/managedNetworks` resource named `default`.
- The reviewed IaC contains no managed-network outbound-rule resources and no Azure AI Enterprise Network Connection Approver role assignment.
- Azure what-if completed successfully, but its planned resource set contained **no managed network resource**. This corroborates the template inspection: deployment of the current plan cannot create the managed agent network or its outbound policy.

## Remediation options

Choose one network architecture and complete it before running Standard Agent Setup or enabling any hosted agent workload.

### Option A — Remain in Central US with a bring-your-own network

1. Provision a dedicated, appropriately sized subnet for Agent Service and delegate it as required by the current Microsoft documentation.
2. Configure the account/project for the supported bring-your-own delegated agent subnet rather than the unsupported Microsoft-managed VNet mode.
3. Provision and privately connect all required dependencies, including the services required by the selected agent setup and tooling.
4. Configure private DNS, least-privilege identities and role assignments, network security controls, and approved egress paths.
5. Validate private connectivity and deny-by-default egress.
6. Only then run **Standard Agent Setup** and enable hosted agent workloads.

### Option B — Use Microsoft-managed VNet in a supported region

1. Move the Foundry account/project and colocated regional resources to a region listed by Microsoft as supporting the selected Microsoft-managed VNet Agent Service configuration.
2. Provision `Microsoft.CognitiveServices/accounts/managedNetworks/default`.
3. Declare all required managed-network outbound rules for approved private dependencies; do not rely on implicit or unrestricted egress.
4. Assign the Azure AI Enterprise Network Connection Approver role at the minimum required scope to the documented identity.
5. Verify private endpoint approvals, DNS resolution, and effective outbound behavior before enabling agents.

## Validation facts and limitations

The following checks passed for the reviewed IaC:

- Bicep build
- Bicep lint
- Azure deployment what-if

These checks establish that the template can be compiled, satisfies the exercised static checks, and produces an Azure deployment plan. They **do not prove egress isolation**. In particular:

- Build and lint do not test effective Azure network behavior.
- What-if reports declared resource changes; it does not infer or create omitted managed-network resources.
- A successful what-if does not test DNS, private endpoint approval, dependency reachability, data exfiltration paths, or effective agent egress.
- The absence of `managedNetworks/default` from what-if is evidence that the intended isolation layer is absent, not evidence that isolation is effective.

Security validation after remediation must include inspection of the deployed managed network or delegated subnet, effective outbound rules, private endpoint state, role assignments, private DNS, and a negative egress test from the hosted agent environment.

## Current disposition

The bare Foundry account and project could be created by the reviewed deployment. Creation alone does not make the environment approved for hosted agents.

**Deployment is blocked by governance/security review, and no hosted agent workload may be enabled.** The block remains until one remediation option is implemented, deployment evidence includes the complete network resources and approvals, and effective private dependency access and deny-by-default outbound behavior are validated.

## Official Microsoft references

- [Secure your AI agents with network isolation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks)
- [Set up a standard agent](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/standard-agent-setup)
- [Azure AI Foundry Agent Service models, tools, and region support](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/model-region-support)
- [Microsoft.CognitiveServices accounts/managedNetworks ARM/Bicep reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/managednetworks)
- [Microsoft.CognitiveServices accounts/managedNetworks/outboundRules ARM/Bicep reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.cognitiveservices/accounts/managednetworks/outboundrules)
- [Azure built-in roles for AI and machine learning](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/ai-machine-learning)

References were evaluated as current on the review date. Microsoft service availability and setup requirements can change; recheck the region-support and networking documentation immediately before remediation and deployment.

---

## Remediation status — 2026-10-25

**Revision owner:** independent owner under reviewer lockout
**Remediates baseline:** `8370d859313f10473472c4a035e26bd977d770ac`
**Deployment performed:** **No**

**Production approval:** **Pending live postdeployment gate**

The original finding history above is preserved unchanged. Commit `8370d859`
replaced the unsupported Microsoft-managed network with a Central US BYO
delegated subnet, private dependencies, forced-tunnel Azure Firewall egress,
least-privilege project roles, AMPLS, and compile-time controls. This follow-up
revision closes the remaining static design findings as follows:

1. **Capability host:** the project capability host now declares the
   service-required `capabilityHostKind: 'Agents'` discriminator and retains the
   four explicit Standard Agent connection lists. Static and compiled-template
   tests assert the discriminator, `2026-09-01` API, connections, dependency
   order, and planned postdeployment GET status.
2. **Private operator path:** the former shared PE subnet is split into
   `snet-foundry-private-endpoint` and
   `snet-dependency-private-endpoints`; `snet-management` is reserved. Only an
   approved private `/24` or narrower CIDR can reach the Foundry PE subnet on
   TCP 443. It cannot reach the dependency PE subnet. Public fallback remains
   disabled. Compile-time CIDR arithmetic and Python `ipaddress` tests reject
   overlap, non-RFC1918 ranges, broad client ranges, and a missing path.
3. **Private telemetry:** a `2026-09-01` Foundry project connection with
   category `AppInsights` and `ProjectManagedIdentity` authentication targets
   workspace-based Application Insights. It has the service-required
   destination metadata and no credential payload. Monitoring Metrics Publisher
   is scoped to that component for the project identity. Application Insights
   and Log Analytics keep local auth and public ingestion/query disabled; AMPLS
   remains PrivateOnly.
4. **RBAC/ABAC:** generated ARM tests assert the exact eight Standard Agent role
   IDs, resource scopes, both exact Storage ABAC strings and version `2.0`,
   database-only Cosmos scope, deterministic capability-host ordering, and the
   absence of Owner, Contributor, and User Access Administrator assignments.
5. **Live gate:** `scripts/validate_foundry_postdeploy.py` is read-only,
   accepts resource IDs but no secrets, and fails closed on live RBAC/ABAC,
   capability status/kind, private endpoints/DNS, public/local auth, project and
   App Insights connections, firewall/UDR, private-resolution evidence, or
   private trace-ingestion failures.

Azure what-if may report role assignments as `Unsupported`. Such output is not
accepted as RBAC evidence. A future deployment remains blocked until the
postdeployment validator passes from approved private validation paths and its
evidence is independently reviewed.

The topology, deployment identity/JIT requirements, fixed resources, costs,
postdeployment process, and explicit statement that no hosted agent or model is
created are recorded in `docs/foundry-infrastructure.md`.

## Independent validator hardening remediation — 2026-10-25

**Revision owner:** independent owner under strict reviewer lockout

**Prior authors consulted:** **No**

**Deployment performed:** **No**

**Finding history:** retained above; this section records the second remediation
without replacing or weakening the original findings.

The postdeployment validator now closes the two remaining HIGH findings:

1. **Resource graph and binding integrity — remediated in source/tests.**
   Supplied IDs are parsed as exact ARM type/name chains under one subscription
   and resource group. Project/account/capability ancestry, returned resource
   IDs, Foundry network injection, exact connection targets and
   `metadata.ResourceId`, VNet/subnet topology, private endpoint targets/groups/
   DNS, firewall policy/rules, NSG rules, and UDR/firewall associations are
   cross-checked. Decoy resources and extra/broader rules fail closed.
2. **Effective RBAC — remediated in source/tests.** Project and account
   identities are queried with `--include-inherited` across subscription,
   resource-group, Foundry, project, dependency, and telemetry scopes. Role
   definitions are resolved, including management-group assignments inherited
   into those scopes. Owner, Contributor, User Access Administrator, RBAC
   Administrator, custom roles, and any assignment outside the exact allowlist
   fail. Storage ABAC strings/version and the Cosmos SQL database scope are
   exact. Optional inherited Reader is disabled by default and, when explicitly
   enabled, is limited to the supplied subscription or resource group.
3. **Safety and evidence — remediated in source/tests.** Azure CLI execution
   uses argument arrays without a shell, bounded timeout/retries/output,
   redacted errors, trusted pagination, and read-only operations. Optional
   evidence output refuses overwrite and contains only hashes, counts, and
   non-sensitive summaries.

Mocked negative tests cover decoy ancestry and returned IDs, connection target
mismatch, wrong private endpoint target/group/DNS, firewall wildcard and extra
rules, missing NSG, inherited Owner/Contributor/User Access Administrator
(including management-group inheritance), unexpected custom roles, ABAC
mismatch, and malformed DNS evidence. Live deployment approval remains blocked
until Azure validation/what-if and the hardened postdeployment gate pass against
the actual approved deployment.

## Final Foundry validator and lifecycle closure — 2026-10-25

**Revision owner:** next independent owner under strict reviewer lockout

**Locked-out prior owners consulted:** **No**

**Deployment performed:** **No**

**Finding history:** all prior findings above remain unchanged. This section
records the final source/test remediation.

1. **Firewall inheritance:** the validator now requires `basePolicy` to be
   absent/null. Because this reviewed policy is standalone, any hierarchy fails
   before rule evaluation. The validator retrieves the complete paged rule
   collection group configuration, verifies the exact group ID/state, and
   retains exact application-rule allowlists. Negative coverage includes a
   broad inherited parent policy.
2. **Private endpoint and DNS binding:** required service names are derived from
   live Foundry, Storage, Cosmos, Search, Application Insights, Log Analytics,
   and AMPLS properties plus documented private-link naming. Every endpoint,
   connection/group/subnet, NIC/IP configuration, custom DNS configuration,
   zone group, zone ID, private DNS zone/link/A/CNAME record set, governed
   subnet endpoint, and governed subnet NIC is queried. The exact FQDN-to-NIC-IP
   mapping is mandatory. Extra endpoints, NICs, A/CNAME records, attacker names,
   and same-subnet wrong IPs fail. Optional client resolver evidence must match
   the same complete mapping and exact management source context.
3. **Complete effective RBAC:** both managed identities are evaluated over all
   infrastructure scopes, including capability host/connections, data
   containers, Cosmos database/data-plane role, telemetry, AMPLS, network,
   firewall, endpoint/NIC, and DNS resources. Scoped Azure CLI calls use
   `--scope ... --include-inherited` without `--all`; a separate unscoped
   enumeration uses `--all`. Prohibited built-in roles, broad custom
   actions/dataActions, all unexpected custom roles, unexpected assignments,
   ABAC drift, extra Cosmos databases, and extra Cosmos SQL assignments fail.
4. **Deployment identity, cost, and expiry:** a read-only preflight validates
   the current principal's exact JIT scopes, restricted role-administration
   condition, current uncommitted budget/teardown approval, owner, cost center,
   and future expiry bounded to seven days. It never elevates or deploys.
   Required lifecycle values are forced into resource tags. The documented
   fixed planning baseline is approximately $1,200/month or $280/seven days,
   before usage charges and subject to current calculator confirmation.
5. **Teardown:** a preview-first script intersects deployment outputs with exact
   tags and blocks every Microsoft Fabric resource. It has no timer or automatic
   action and deletes only after an exact confirmation phrase. It never performs
   resource-group deletion. Independent review found and the revision fixed a
   fail-open case where absent lifecycle output fields and absent resource tags
   could both compare as null; all required lifecycle fields and tag keys must
   now be present, non-empty, and equal.

Live approval remains blocked until the read-only preflight passes for an
approved current principal, Azure validation and both what-if levels complete
against the intended subscription/resource group, the environment is deployed
through an independently authorized process, and the postdeployment validator
passes with live private DNS, endpoint, RBAC, and trace evidence.

## Effective privilege and two-phase closure — 2026-10-25

**Revision owner:** next independent owner under strict reviewer lockout

**Locked-out Foundry owners consulted:** **No**

**Deployment performed:** **No**

**Finding history:** preserved above. This section records the remaining
source/IaC/test remediation at reviewed baseline `e6197baf`.

1. **Effective deployer privilege:** preflight now enumerates the current
   principal with `--include-groups` on both scoped inherited and unscoped
   assignment lists, resolving direct, group, transitive-group, subscription,
   resource-group, and management-group effective access. Every role definition
   and permission set is resolved. Owner, Contributor, User Access
   Administrator, RBAC Administrator outside the exact approved condition/scope,
   Network Contributor, unreviewed custom roles, unexpected roles, and action
   drift fail. Foundation accepts only its exact custom deployment role.
   Finalize additionally accepts exact-scope conditional RBAC Administrator and
   the two exact service prerequisites.
2. **Canonical delegated-role ABAC:** the repository defines one version `2.0`
   condition for guarded role-assignment write/delete. Tokenized canonical
   comparison ignores only whitespace/case and set ordering. The role IDs, live
   Foundry account/project managed-identity principal IDs, and
   `ServicePrincipal` type are exact; extra clauses, OR branches, role IDs,
   principal IDs/types, operators, wildcards, missing actions, and malformed
   input fail. PIM eligibility, activation, expiry, signed approval reference,
   and approval artifact hash remain external mandatory evidence.
3. **Greenfield phase separation:** `infra/main.bicep` is foundation-only and
   creates no runtime role assignment, capability host, hosted agent, or model.
   `infra/finalize.bicep` reproducibly creates only the reviewed runtime role
   assignments and capability host. Foundation live validation omits future
   runtime assignments/capability/trace but explicitly requires their absence
   and keeps all private controls. Finalize derives principal/workspace IDs from
   live existing Foundry resources instead of mutable parameters. Finalize
   preflight and live validation require the exact runtime posture. Every
   transition is fail-closed.
4. **Complete private endpoint inventory:** the validator checks the complete
   target-side `privateEndpointConnections` collection for Foundry, Storage,
   Cosmos, Search, and AMPLS, requiring exactly the approved endpoint, group,
   and state. Subscription-wide PE/NIC enumeration is filtered across all five
   deployment VNet subnets, not only the two PE subnets. Extra target
   connections elsewhere and management/agent/firewall subnet decoys fail.
5. **Cost approval:** the fixed planning baseline remains approximately
   `$280/seven days`. Preflight requires a current signed external approval
   reference, hash, positive ceiling, teardown approval, and bounded JIT
   evidence. No approval or evidence was created by this revision.

The expected current external blocker is intentional: any current principal
that inherits broad group access fails before validation or deployment. Live
foundation/finalize Azure validation, what-if, deployment, and postdeployment
evidence remain external; no deployment was authorized or attempted here.

Validation completed without deployment:

- dependency-installed `pytest`: `265 passed, 51 subtests passed`;
- strict `mypy`: no issues in 13 source files;
- Bandit: no medium/high findings; the complete scan also reported the existing
  low-severity deterministic `random.Random` use in the synthetic generator;
- `pip-audit`: no known vulnerabilities;
- Bicep build/lint/build-params and the security-invariants fixture: passed for
  foundation and finalize;
- all 85 documented custom-role actions resolved to current Azure provider
  operations;
- Azure `validate` and `what-if` passed for foundation and finalize at both
  `Provider` and `ProviderNoRbac` levels (58 and 11 planned changes,
  respectively); and
- live read-only preflight failed as intended because the current principal
  inherits subscription Contributor through a group. The same enumeration also
  observed inherited group User Access Administrator. This external privilege
  blocker must be removed; it was not changed by this revision.

## Subscription RBAC auditor scope closure — 2026-10-25

**Revision owner:** independent owner under reviewer lockout

**Locked-out prior role authors consulted:** **No**

**Deployment performed:** **No**

The phase deployment roles remain assigned only at the exact target resource
group. Their scoped RBAC metadata reads remain available for scoped checks.
Unscoped, group-aware, and inherited effective-role enumeration is now
authorized separately by `Foundry POC RBAC Auditor`, fixed role ID
`df3a75f8-1e03-598b-a0b0-a19ae0b5bb46`, assigned JIT at the exact subscription.

The auditor definition is limited to
`Microsoft.Authorization/roleAssignments/read` and
`Microsoft.Authorization/roleDefinitions/read`, with no wildcard, resource
read, write, delete, NotAction, or data action. Preflight validates the live
role name, ID, exact subscription assignable scope, and permission arrays, then
requires exactly one auditor assignment plus the exact phase identity model.
The phase and auditor roles must be assigned directly to the dedicated
deployment principal. Missing, duplicate, wrong-scope, wrong-subscription,
broad, inherited, group, or other extra assignments fail.

External approval evidence must identify the auditor PIM schedule and either
record its own bounded activation/expiry or explicitly bind it to the existing
deployment JIT window. The repository still creates no role, assignment,
approval evidence, cloud resource, or deployment.

Validation completed without deployment or cloud mutation:

- full `pytest`: `277 passed, 51 subtests passed`;
- strict `mypy`: no issues in 13 source files;
- full Bandit scan: no medium/high findings; the existing low-severity
  deterministic synthetic-data `random.Random` finding remains;
- `pip-audit`: no known vulnerabilities;
- Bicep build, lint, build-params, and security-invariants fixture: passed;
- both foundation and finalize Azure `validate` passed;
- Azure what-if passed at `Provider` and `ProviderNoRbac` levels with 58
  foundation and 11 finalize changes, matching the prior plan shape;
- both auditor actions resolved as current Microsoft.Authorization provider
  operations; and
- independent security review reported no vulnerabilities in this revision.

## Provider-contract remediation validation — 2026-10-25

**Validated commit:** `716f1d8c7c9566813a25ce9a80292bb6d5e3fa65`

**Stable deployment name:** `foundry-foundation-20261025-r2`

**Successful foundation deployment:** **No**

**Incremental retry authorization:** **Pending independent reviewer approval**

**Finding history:** preserved above. This section records sanitized
remediation evidence after the initial `r2` attempt reached Azure providers and
failed before full foundation creation.

The initial attempt produced three reviewed provider-contract failures:

1. the foundation deployment role lacked exact linked-resource join and
   private-endpoint approval actions required by the Bicep graph;
2. Azure Firewall rejected the deprecated
   `requireProxyForNetworkRules` DNS setting; and
3. Azure AI Search rejected `authOptions` while `disableLocalAuth` was true.

Storage, Cosmos DB, four NSGs, the route table, and the Azure Firewall public IP
completed successfully before the attempt failed. They remain as bounded
partial resources. The provider-fix commit adds the exact 12 linked-resource
actions, removes the deprecated firewall property, omits the incompatible
Search property, and retains fixed nested deployment names in `Incremental`
mode for a convergent retry.

Dedicated-identity preflight now passes. The live foundation, finalize, and
subscription-scoped RBAC auditor roles exactly match their reviewed sources;
the foundation role has 90 actions and the auditor is active. The reviewed JIT
schedules are active. The external approval ceiling is $400 against the $280
fixed estimate and expires
`2026-10-31T20:00:00Z`. No approval artifact, identity identifier, certificate
path/content, secret, token, key, or JIT reference is stored in repository
evidence.

Validation bound to the fix commit passed:

- `pytest`: 285 tests and 51 subtests;
- strict `mypy`: clean;
- Bandit: passed with no medium/high finding; the only documented low finding
  is unrelated deterministic `random.Random` use in the synthetic generator;
- `pip-audit`: no known vulnerabilities;
- Bicep restore, build, lint, build-params, and compiled-template diff: passed;
- Azure `validate` at `Provider` level: `Succeeded` under the dedicated
  identity; and
- target `Provider` what-if: 49 Create, 6 NoChange, 2 Modify, 0 Delete,
  0 Replace, and 0 Unsupported.

The two Modify results are reviewed service-populated drift, not design drift:
Cosmos server-populated/read-only properties and public-IP server-generated
`ddosSettings`/`ipTags` omitted by the template. They introduce no security,
public-network, network-topology, or tag change. No existing Fabric capacity is
deleted or changed.

This remediation evidence does not represent a successful deployment and does
not authorize execution. The foundation retry remains blocked pending
independent reviewer approval. Before retry, recheck that JIT and cost/teardown
approval are still active and unexpired. Retry foundation only; finalize,
model, Fabric Data Agent, hosted agent, and application work remain blocked
until the foundation deployment and mandatory live postdeployment validation
pass. The sanitized retained record is
`evidence/foundry-foundation-predeploy-716f1d8.json`.

## Live JIT evidence correction — 2026-10-25

**Validated code commit:** `716f1d8c7c9566813a25ce9a80292bb6d5e3fa65`

**Cloud or source mutation performed:** **No**

**Incremental retry authorization:** **Pending corrected independent reviewer
verdict**

**Finding history:** preserved above. This addendum corrects the factual basis
of a subsequent security-review blocker; it does not erase the blocker or
authorize the retry.

The blocker alleged that the foundation schedule instance had
`endDateTime: null`. Live authoritative schedule output contradicts that claim:

- foundation schedule request
  `7055ed56-a21a-4e20-ae5a-05554cab8bd9` is `Provisioned` for service principal
  `dd598...` under the exact foundation role
  `7f83e4ce-8151-4a7d-9765-40c04d2cf0b8` at the target resource group; its
  start is `2026-10-25T18:36:31.5465064Z` and its `AfterDateTime` expiration is
  `2026-10-31T20:00:00Z`; and
- the same-named foundation schedule instance is `Assigned`, `Direct`, and
  `Provisioned`, starts at `2026-10-25T18:36:32.803Z`, and has
  `endDateTime` `2026-10-31T20:00:00Z`.

The subscription auditor request
`acf1f4b1-58a7-4a44-ab90-20a5d0a49ef4` is `Provisioned`, starts at
`2026-10-25T19:14:28.5901718Z`, and has `AfterDateTime` expiration
`2026-10-31T20:00:00Z`. The auditor schedule-instance response omits
`endDateTime`; this is recorded as an API response discrepancy, not a permanent
assignment claim. The Provisioned schedule request is authoritative for the
expiration, and the external approval JSON binds the same expiry.

Standard `role assignment list` output exposes the underlying assignments
without schedule-expiry fields. It is not authoritative for JIT schedule
expiration and cannot support a permanent-assignment conclusion.

The target what-if evidence remains 49 Create, 6 NoChange, 2 reviewed Modify,
and zero Delete, Replace, or Unsupported. Its ignored-existing inventory
contains exactly one `Microsoft.Fabric/capacities` resource, which is neither
changed nor deleted. Provider-fix evidence for commit `716f1d8` otherwise
remains unchanged. The retry remains fail-closed until the independent reviewer
issues a corrected verdict.

## Firewall API and validator predeploy evidence — 2026-10-25

**Validated target commit:** `92af0579d6c885be4dd73dad49150b81ee58b031`

**Included firewall provider fix:**
`e5b1c5cc1c5fd0a93596d0df1db08ca6aeb68576`

**Cloud mutation or infrastructure retry after the fixes:** **No**

**Incremental retry authorization:** **Pending independent reviewer approval**

**Finding history:** preserved above and in the prior evidence artifacts. This
section does not replace the initial provider failures, the later Azure
Firewall failure, or the corrected JIT record.

The subsequent approved retry reached Azure Firewall but failed because the
generated request placed `sku` at the resource root rather than under
`properties`. The target fix uses the documented GA
`Microsoft.Network/azureFirewalls@2026-03-01` contract, emits the Standard
`AZFW_VNet` SKU under `properties`, and omits the provider-assigned read-only
private IP from the request. The validator fix uses the same API, reads
`properties.sku`, and fails closed for missing, incorrect, or legacy root-only
SKU shapes.

Full commit-bound validation passed:

- 290 pytest tests plus 51 subtests;
- strict mypy;
- pip-audit with no known vulnerabilities;
- Bandit with no medium/high findings; and
- Bicep validation.

Azure `validate` succeeded against the current partial state. `Provider` and
`ProviderNoRbac` what-if each reported 45 Create, 12 Deploy, one Ignore for the
existing Fabric capacity, and zero Modify, Delete, or Unsupported. The ignored
capacity is not changed or deleted.

The current partial state contains the VNet, four NSGs, route table, firewall
policy and rules, Azure Firewall public IP, Storage, Cosmos DB, and Search. The
Azure Firewall itself is absent. Consequently, `AzureFirewallSubnet` currently
has no firewall IP configuration. The provider is expected to assign the first
Azure-usable subnet address, `10.40.1.68`; the UDR and VNet DNS controls remain
fixed to that address and fail closed if the live assignment differs. The
mandatory postdeployment validator must verify the live assignment.

The live JIT schedules and reviewed role definitions remain active/exact, and
dedicated-principal preflight passes. No retry has occurred after the firewall
and validator fixes. The next foundation-only incremental retry remains blocked
until independent reviewer approval, followed by a retry-time JIT and
cost/teardown approval check. Finalize, model, hosted-agent, Fabric Data Agent,
and application deployment remain unauthorized. Sanitized evidence is retained
in `evidence/foundry-foundation-predeploy-92af057.json`.

## App Insights connection validator closure — 2026-10-25

**Validated target commit:** `1bd8ca5fa5129efc1002338901055bf08c92665d`

**Included request-shape fix:**
`670c74009dba73b23f08556bcc9aa301bd21bf4a`

**Deployment performed:** **No**

**Incremental retry authorization:** **Pending independent reviewer approval**

Read-only live inventory supersedes the earlier current-state statements
without changing their historical record. Azure Firewall is now `Succeeded`
with Standard `AZFW_VNet` SKU and private IP `10.40.1.68`. The Foundry account
and project, Storage/Cosmos/Search dependencies, five approved private
endpoints, ten private DNS zones and links, Log Analytics, Application
Insights, and AMPLS are present. Application Insights and Log Analytics retain
private ingestion/query controls, and AMPLS is `PrivateOnly`. The live project
contains four AAD dependency connections; `conn-application-insights` remains
absent after the failed `private-monitoring` deployment.

The validator now treats the future `ProjectManagedIdentity` App Insights
connection as a closed contract. Its connection property keys and metadata keys
must exactly match the reviewed official shape. `ApiType`, `ResourceId`, and
the expected connection-string hash are exact. A recursive scanner rejects
credential-like field names or values at any unexpected depth, and the
connection rejects `credentials`, `peRequirement`, API/instrumentation keys,
secrets/tokens, unexpected connection strings, nested extensions, and every
other unreviewed property or metadata key. Negative tests cover unexpected
metadata, nested credentials, `peRequirement`, arbitrary extensions, and hash
drift.

The monitoring module and compiled-template regression now state that
authentication uses the Foundry **project** system-assigned managed identity,
not the account identity.

Target validation passed 305 tests plus 51 subtests, strict mypy, pip-audit,
Bicep, Azure validate/what-if, and Bandit with no medium/high findings.
Foundation `Provider` and `ProviderNoRbac` plans contain one material Create
for `conn-application-insights`, 56 Deploy and seven Ignore provider
projections, and zero Modify, Delete, Replace, or Unsupported. Finalize plans
contain only ten expected creates: one capability host, eight Standard Agent
runtime role assignments, and one Monitoring Metrics Publisher assignment.

Capability host and runtime RBAC remain absent, as required for the
foundation-only live state. Dedicated-principal preflight, foundation/auditor
JIT, and the approved cost/teardown window remain active but require
reconfirmation at retry time. A future retry remains blocked until independent
review and explicit authorization complete. Sanitized evidence is retained in
`evidence/foundry-foundation-predeploy-1bd8ca5.json`.

## Live App Insights projection validator correction — 2026-10-25

**Deployment performed by this correction:** **No**

The preceding review history remains unchanged. A later live foundation
validation showed that the current Foundry provider adds safe provider-managed
fields to the App Insights connection projection. The validator now requires
the complete observed property-key set and exact value types: null `audience`,
`error`, and `expiryTime`; `ProjectManagedIdentity`; `AppInsights`; group
`ServicesAndApps`; boolean `isDefault: true`; boolean
`isSharedToAll: false`; `NotRequired`/`NotApplicable` private-endpoint state;
an empty `sharedUserList`; the exact App Insights target; and boolean
`useWorkspaceManagedIdentity: false`.

The metadata allowlist and expected connection-string hash remain exact.
Recursive sensitive-field and credential-like-value scanning remains active
outside the one hash-verified metadata value. Tests reject missing or extra
properties, non-null audience/error/expiry values, group/default/share/user
changes, boolean type substitution, AAD or API-key authentication, private
endpoint state drift, workspace managed identity enablement, target or metadata
drift, and nested credentials. This correction changes validation only; it
does not deploy, mutate Azure resources, or create evidence.

Working-tree validation passed 329 tests plus 51 subtests, strict mypy,
pip-audit with no known vulnerabilities, Bicep restore/build/lint/build-params,
and Azure validation at `Provider` and `ProviderNoRbac` levels for foundation
and finalize. Both foundation what-if levels returned 57 Deploy and seven
Ignore projections; both finalize levels returned ten Create and 49 Ignore
projections. Bandit reported no medium/high findings and only the documented
low-severity deterministic synthetic-data `random.Random` use.

## Drill Advisor application review — 2026-10-26

Scope: `src/app/**`

### Medium: conversation history persists across browser users

Drill Advisor stores all conversation history under one origin-wide
`localStorage` key. The application loads and displays that history before
authentication, and logout does not clear the in-memory or persisted
conversations.

On a shared browser, a later user can read a previous user's prompts, responses,
and retained Foundry conversation identifiers without signing in as that user.

Affected files:

- `src/app/client/src/lib/storage.ts`
- `src/app/client/src/App.tsx`
- `src/app/client/src/auth.tsx`

Recommended remediation:

- Load and display history only after authentication.
- Namespace persisted history by the signed-in account and tenant.
- Clear in-memory history on logout and account changes.
- Consider `sessionStorage` or opt-in persistence if history does not need to
  survive browser sessions.

Severity: **Medium**  
Confidence: **10/10**

No additional actionable vulnerabilities were found in delegated token
validation, tenant-pinned Entra v1/v2 issuer handling, Static Web Apps
platform-header precedence, Foundry forwarding, request validation, response
parsing, CSP/routing configuration, or runtime credential handling.

Residual risks:

- The first request for `https://ai.azure.com/user_impersonation` requires user
  consent or tenant administrator consent.
- Delegated tokens necessarily exist in browser memory and MSAL
  `sessionStorage`; same-origin XSS, compromised dependencies, or a malicious
  browser extension could access them.
- `X-Drill-Advisor-Access-Token` must remain excluded from application and
  platform logs.

## Drill Advisor Container Apps review — 2026-10-27

Scope:

- `src/app/**`
- `infra/container-app/**`
- Live Azure Container Apps deployment

### Medium: daily anonymous cost limit is not durable

The advertised 500-call daily Foundry allowance is stored only in process
memory. Azure Container Apps is configured with `minReplicas: 0`, so routine
scale-to-zero, restarts, revisions, or platform maintenance reset the counter.
An anonymous caller can therefore consume the allowance, wait for a new
container process, and receive a fresh allowance.

Affected files:

- `src/app/api/DrillAdvisor.Api/Limits/AnonymousChatGate.cs`
- `infra/container-app/main.bicep`

Recommended remediation:

- Store the UTC-day allowance in an atomic durable service such as Azure Table
  Storage, Redis, or Cosmos DB.
- Retain the application kill switch and add upstream Foundry quota/budget
  controls as a second boundary.

Severity: **Medium**  
Confidence: **10/10**

### Medium: public workload uses an over-privileged shared identity

The Container App currently reuses the legacy Function App user-assigned
managed identity. That identity retains Storage Blob Data Owner, Queue Data
Contributor, Table Data Contributor, project-level Foundry Agent Consumer, and
agent-level Foundry Agent Consumer assignments. The Container App does not use
the Storage permissions and only invokes one Foundry agent.

Affected files:

- `infra/container-app/main.bicep`
- `src/app/server/DrillAdvisor.Web/Program.cs`

Recommended remediation:

- Give the public Container App a dedicated user-assigned managed identity.
- Assign only ACR pull, exact-agent Foundry invocation, and the required
  federated Fabric identity.
- Remove the duplicate project-scoped Foundry assignment after confirming the
  agent-scoped assignment is sufficient.

Severity: **Medium**  
Confidence: **9/10**

Residual POC risks:

- Forwarded-header trust depends on the current Azure Container Apps ingress
  topology and must be revalidated if another proxy is introduced.
- CSP and HSTS are defense-in-depth gaps; current Markdown rendering escaped
  raw HTML and neutralized `javascript:` links during review.
- Build-stage container tags are mutable and the registry trust policy is
  disabled. The deployed application image itself is pinned by digest and runs
  as a non-root user.
