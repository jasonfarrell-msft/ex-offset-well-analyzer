# Container Apps preflight report

Validated: 2026-10-27
Target: subscription `bb4b2781-6739-4fa1-994e-4ad6ce55c59c`, resource group `rg-welladvisor-mx01`, region `centralus`

## Result

- The deployment is split into a registry stage and an app stage, so a clean deployment can build and push the image before the Container App references its digest.
- Bicep CLI: `0.43.8`
- `bicep format`: passed for both templates and both parameter files
- `bicep restore`: passed for both templates; neither template has external module dependencies
- `bicep build <template> --stdout --no-restore`: passed for both templates
- `bicep build-params <parameters> --stdout --no-restore`: passed for both parameter files
- `bicep lint <template> --no-restore`: passed for both templates
- Final Bicep warnings: **0**
- Azure what-if validation level: **Provider** for both stages; no `ProviderNoRbac` fallback was used
- Registry what-if: **0 create, 0 modify, 0 delete, 0 replace, 1 no change, 9 ignore**
- App what-if: **0 create, 0 modify, 0 delete, 0 replace, 5 no change, 7 ignore**
- No deployment or ACR build was run, no resource was changed, and no transient ARM JSON file was created

## Stage ownership

### Registry stage

`registry.bicep` owns only Basic ACR `acrdrilladvisormx01`. It preserves the existing tags and POC security posture:

- public network access enabled;
- registry admin and anonymous pull disabled;
- data endpoint disabled;
- encryption disabled, matching the current Basic registry;
- task network-rule bypass disabled;
- legacy registry permissions retained for registry-scoped `AcrPull`;
- `SecurityControl=Ignore`.

### App stage

`main.bicep` treats the ACR as an existing resource and owns:

1. exact-scope `AcrPull` assignment `0d942250-663d-521d-9b17-2339643d1fcb`;
2. Log Analytics workspace `log-drill-advisor-wfrd-mx01`;
3. Container Apps environment `cae-drill-advisor-wfrd-mx01`;
4. environment diagnostic setting `service`;
5. Container App `ca-drill-advisor-wfrd-mx01`.

`main.bicepparam` retains the currently deployed immutable image:

```text
acrdrilladvisormx01.azurecr.io/drill-advisor@sha256:8f01398c110cd43092071f2918ed3e4d202bdc3543cc5c4eafdcad730249504e
```

## API versions

| Resource type | API version | Selection |
|---|---:|---|
| `Microsoft.ContainerRegistry/registries` | `2025-11-01` | Latest GA with current Bicep type support |
| `Microsoft.Authorization/roleAssignments` | `2022-04-01` | Latest GA |
| `Microsoft.OperationalInsights/workspaces` | `2025-07-01` | Latest GA with current Bicep type support |
| `Microsoft.App/managedEnvironments` | `2026-01-01` | Latest GA with current Bicep type support |
| `Microsoft.App/containerApps` | `2026-01-01` | Latest GA with current Bicep type support |
| `Microsoft.Insights/diagnosticSettings` | `2016-09-01` | Latest GA; newer versions remain preview |

The providers also advertise GA `2026-03-01` for Log Analytics and GA `2026-07-01` for Container Apps. Bicep CLI `0.43.8` emits `BCP081` for those versions, so the templates use the latest GA versions that provide full compile-time typing. The diagnostic settings GA type omits the metric category returned by the provider; the template localizes `any()` to that provider-returned object to preserve idempotence.

## Staged deployment workflow

These are operator commands for a future deployment. They were **not** run during this preflight.

Set the target values:

```sh
SUBSCRIPTION_ID='bb4b2781-6739-4fa1-994e-4ad6ce55c59c'
RESOURCE_GROUP='rg-welladvisor-mx01'
ACR_NAME='acrdrilladvisormx01'
IMAGE_TAG="staged-$(date -u +%Y%m%d%H%M%S)"
```

1. Deploy the registry stage:

   ```sh
   az deployment group create \
     --name "container-registry-$(date -u +%Y%m%d%H%M%S)" \
     --subscription "$SUBSCRIPTION_ID" \
     --resource-group "$RESOURCE_GROUP" \
     --template-file infra/container-app/registry.bicep \
     --parameters infra/container-app/registry.bicepparam
   ```

2. Build `src/app/Dockerfile` in ACR and capture the pushed manifest digest:

   ```sh
   az acr build \
     --subscription "$SUBSCRIPTION_ID" \
     --registry "$ACR_NAME" \
     --image "drill-advisor:${IMAGE_TAG}" \
     --file Dockerfile \
     src/app

   IMAGE_DIGEST="$(
     az acr manifest show-metadata \
       --subscription "$SUBSCRIPTION_ID" \
       --registry "$ACR_NAME" \
       --name "drill-advisor:${IMAGE_TAG}" \
       --query digest \
       --output tsv
   )"
   test -n "$IMAGE_DIGEST"
   CONTAINER_IMAGE="${ACR_NAME}.azurecr.io/drill-advisor@${IMAGE_DIGEST}"
   printf '%s\n' "$CONTAINER_IMAGE"
   ```

3. Set the captured immutable digest in `main.bicepparam`, then format it:

   ```sh
   python3 -c 'import re, sys; from pathlib import Path; p = Path(sys.argv[1]); p.write_text(re.sub(r"(?m)^param containerImage = .*$", f"param containerImage = '\''{sys.argv[2]}'\''", p.read_text()))' \
     infra/container-app/main.bicepparam \
     "$CONTAINER_IMAGE"
   bicep format infra/container-app/main.bicepparam
   ```

4. Run the app-stage provider what-if, review it, and then create the deployment:

   ```sh
   az deployment group what-if \
     --name "preflight-container-app-$(date -u +%Y%m%d%H%M%S)" \
     --subscription "$SUBSCRIPTION_ID" \
     --resource-group "$RESOURCE_GROUP" \
     --template-file infra/container-app/main.bicep \
     --parameters infra/container-app/main.bicepparam \
     --validation-level Provider \
     --result-format FullResourcePayloads

   az deployment group create \
     --name "container-app-$(date -u +%Y%m%d%H%M%S)" \
     --subscription "$SUBSCRIPTION_ID" \
     --resource-group "$RESOURCE_GROUP" \
     --template-file infra/container-app/main.bicep \
     --parameters infra/container-app/main.bicepparam
   ```

## Validation what-if commands

```sh
az deployment group what-if \
  --name preflight-container-registry-final-20261027 \
  --subscription bb4b2781-6739-4fa1-994e-4ad6ce55c59c \
  --resource-group rg-welladvisor-mx01 \
  --template-file infra/container-app/registry.bicep \
  --parameters infra/container-app/registry.bicepparam \
  --validation-level Provider \
  --result-format FullResourcePayloads

az deployment group what-if \
  --name preflight-container-app-final2-20261027 \
  --subscription bb4b2781-6739-4fa1-994e-4ad6ce55c59c \
  --resource-group rg-welladvisor-mx01 \
  --template-file infra/container-app/main.bicep \
  --parameters infra/container-app/main.bicepparam \
  --validation-level Provider \
  --result-format FullResourcePayloads
```

## Security checks

- The existing UAMI client ID and principal ID match `main.bicepparam`.
- The app stage maintains `AcrPull` at registry scope and uses the UAMI for registry authentication.
- The environment sends logs through Azure Monitor diagnostic settings without retrieving a Log Analytics shared key.
- No client secret, storage key, registry password, deployment token, or secret output is present.
- ACR public access and the external Container App endpoint remain deliberate POC choices. Registry admin and anonymous pull are disabled, and ingress redirects HTTP to HTTPS.
