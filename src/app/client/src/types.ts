export type ChatRole = "user" | "assistant";
export type ScalarValue = string | number | boolean | null;

export interface UserMessage {
  id: string;
  role: "user";
  text: string;
  createdAtUtc: string;
}

export interface AssistantMessage {
  id: string;
  role: "assistant";
  markdown: string;
  createdAtUtc: string;
  visuals: VisualBlock[];
  toolCalls: ToolCallSummary[];
  sources: SourceSummary[];
  usage?: UsageSummary;
  latencyMs?: number;
}

export type ConversationMessage = UserMessage | AssistantMessage;

export interface KpiItem {
  id?: string;
  label: string;
  value: string | number;
  unit?: string;
  context?: string;
}

export interface KpiGridVisual {
  type: "kpi-grid";
  id?: string;
  title?: string;
  description?: string;
  items: KpiItem[];
}

export interface BarDatum {
  id?: string;
  label: string;
  value: number;
  unit?: string;
}

export interface BarChartVisual {
  type: "bar-chart";
  id?: string;
  title?: string;
  description?: string;
  unit?: string;
  data: BarDatum[];
}

export interface DataTableColumn {
  key: string;
  label: string;
  unit?: string;
  align?: "left" | "center" | "right";
}

export interface DataTableVisual {
  type: "data-table";
  id?: string;
  title?: string;
  description?: string;
  columns: DataTableColumn[];
  rows: Record<string, ScalarValue>[];
  caption?: string;
}

export type VisualBlock =
  | KpiGridVisual
  | BarChartVisual
  | DataTableVisual;

export interface ToolCallSummary {
  id?: string | null;
  type: string;
  name?: string | null;
  server?: string | null;
  status?: "completed" | "failed" | "running" | string | null;
  toolCount?: number | null;
}

export interface SourceSummary {
  name?: string | null;
  measures: string[];
}

export interface UsageSummary {
  inputTokens?: number | null;
  outputTokens?: number | null;
  totalTokens?: number | null;
  [key: string]: number | null | undefined;
}

export interface ChatResponse {
  conversationId: string;
  message: {
    id: string;
    role: "assistant";
    markdown: string;
    createdAtUtc: string;
  };
  visuals: VisualBlock[];
  toolCalls: ToolCallSummary[];
  sources: SourceSummary[];
  usage?: UsageSummary;
  latencyMs?: number;
}

export interface StoredConversation {
  localId: string;
  conversationId?: string;
  title: string;
  messages: ConversationMessage[];
  createdAtUtc: string;
  updatedAtUtc: string;
}

export type OffsetOperation = "targets" | "candidates" | "compare";

export interface OffsetCriteria {
  radiusFt: string;
  formationMatch: boolean;
  holeSizeMatch: boolean;
  mdOverlap: boolean;
}

export interface OffsetContext {
  targetId: string;
  criteria: OffsetCriteria;
  selectedWellIds: string[];
  contextRevision: number;
}

export interface OffsetContextEnvelope {
  contractVersion: string;
  releaseId: string;
  context: OffsetContext;
}

export interface ChatRequest {
  message: string;
  conversationId?: string;
  offsetContext?: OffsetContextEnvelope;
}

export interface ChatApi {
  send(request: ChatRequest, signal?: AbortSignal): Promise<ChatResponse>;
}

export interface OffsetVersions {
  contractVersion: string;
  queryContractVersion: string;
  transformationContractVersion: string;
  datasetVersion: string;
  releaseId: string;
  manifestSha256: string;
}

export interface OffsetRequestBase {
  contractVersion: string;
  releaseId: string;
}

export interface OffsetTargetsRequest extends OffsetRequestBase {
  operation: "targets";
}

export interface OffsetCandidatesRequest extends OffsetRequestBase {
  operation: "candidates";
  context: OffsetContext;
}

export interface OffsetCompareRequest extends OffsetRequestBase {
  operation: "compare";
  context: OffsetContext;
}

export type OffsetRequest =
  | OffsetTargetsRequest
  | OffsetCandidatesRequest
  | OffsetCompareRequest;

export interface OffsetTarget {
  targetId: string;
  recordKind: "PLANNED_TARGET";
  basinName: string;
  fieldName: string;
  expectedFormationName: string;
  plannedTrajectoryProfile: "VERTICAL" | "BUILD_AND_HOLD" | "HORIZONTAL";
  plannedHoleSizeIn: string;
  plannedMdMinFt: string;
  plannedMdMaxFt: string;
  coordinateFrameId: "SYN-LOCAL-FT-V1";
  locationSemantics: "SYNTHETIC_SURFACE_WELLHEAD";
  coordinateUnits: "ft";
  surfaceXFt: string;
  surfaceYFt: string;
  referenceDatasetVersion: string;
  referenceManifestSha256: string;
  isSynthetic: true;
  plannedBitType?: string | null;
  plannedBhaType?: string | null;
  plannedMudType?: string | null;
}

export interface OffsetMetrics {
  matchingSectionCount: number;
  acceptedRunCount: number;
  acceptedFootageFt: string | null;
  acceptedDurationHours: string | null;
  averageFootagePerRunFt: string | null;
  summaryPenetrationRateFtPerHour: string | null;
  quarantinedRunCount: number;
  warningRunCount: number;
  warningSectionCount: number;
  warningIssueCount: number;
  scope: "MATCHING_WHOLE_SECTIONS";
  unavailableReasons: string[];
}

export interface OffsetMatchingSection {
  sectionId: string;
  formationName: string | null;
  holeSizeIn: string | null;
  startMdFt: string | null;
  endMdFt: string | null;
  trajectoryProfile: "VERTICAL" | "BUILD_AND_HOLD" | "HORIZONTAL" | null;
}

export interface OffsetCandidate {
  wellId: string;
  wellName: string;
  basinName: string;
  fieldName: string;
  coordinateFrameId: "SYN-LOCAL-FT-V1";
  locationSemantics: "SYNTHETIC_SURFACE_WELLHEAD";
  coordinateUnits: "ft";
  distanceSquaredFt2: string;
  distanceFt: string;
  matchingSections: OffsetMatchingSection[];
  metrics: OffsetMetrics;
  plannedBitType?: string | null;
  plannedBhaType?: string | null;
  plannedMudType?: string | null;
  runConfigContext?: OffsetRunConfigContext | null;
  eventContext?: OffsetEventContext | null;
}

export interface OffsetComparison {
  wellId: string;
  matchingSections: OffsetMatchingSection[];
  metrics: OffsetMetrics;
  plannedBitType?: string | null;
  plannedBhaType?: string | null;
  plannedMudType?: string | null;
  runConfigContext?: OffsetRunConfigContext | null;
  eventContext?: OffsetEventContext | null;
}

export interface OffsetRunTuple {
  bitType?: string | null;
  bhaType?: string | null;
  mudType?: string | null;
  mudWeightPpg?: string | number | null;
  mudFunnelViscositySec?: string | number | null;
  acceptedRunCount?: number | null;
  acceptedFootageFt?: string | number | null;
  acceptedDurationHours?: string | number | null;
}

export interface OffsetRunConfigContext {
  runTuples?: OffsetRunTuple[] | null;
}

export interface OffsetEventSummaryByType {
  eventType: string;
  eventCount?: number | null;
  eventDurationHours?: string | number | null;
}

export interface OffsetEventSummaryBySubtype {
  eventType: string;
  eventSubtype: string;
  eventCount?: number | null;
  eventDurationHours?: string | number | null;
}

export interface OffsetEventContext {
  totalEventCount?: number | null;
  totalEventDurationHours?: string | number | null;
  byType?: OffsetEventSummaryByType[] | null;
  bySubtype?: OffsetEventSummaryBySubtype[] | null;
}

export interface OffsetExclusion {
  wellId: string;
  reasons: string[];
}

export interface OffsetEvidenceSource {
  view: string;
  columns: string[];
  measures: string[];
}

export interface OffsetEvidence {
  receiptId: string;
  requestId: string;
  toolCallId: string;
  resultId: string;
  sources: OffsetEvidenceSource[];
  grain: string;
  units: {
    distanceSquaredFt2: string;
    distanceFt: string;
    acceptedFootageFt: string;
    acceptedDurationHours: string;
    averageFootagePerRunFt: string;
    summaryPenetrationRateFtPerHour: string;
    counts: string;
  };
  denominators: {
    averageFootagePerRunFt: string;
    summaryPenetrationRateFtPerHour: string;
  };
  qualityCaveats: string[];
  completion: string;
}

export interface OffsetAnalyticalSuccess<T, TOperation extends OffsetOperation>
  extends OffsetVersions {
  operation: TOperation;
  status: "success" | "empty";
  context: OffsetContext | null;
  contextHash: string | null;
  rows: T[];
  totalCount: number;
  truncated: false;
  exclusions: OffsetExclusion[];
  evidence: OffsetEvidence;
}

export interface OffsetFailure extends OffsetVersions {
  operation: OffsetOperation | "chat" | null;
  status: "unavailable" | "stale" | "error";
  context: OffsetContext | null;
  contextHash: null;
  evidence: null;
  error: {
    code:
      | "INVALID_REQUEST"
      | "CAPABILITY_UNPROVEN"
      | "UPSTREAM_UNAVAILABLE"
      | "INCOMPLETE_RESULT"
      | "CONTEXT_MISMATCH"
      | "CLAIM_NOT_GROUNDED";
    retryable: boolean;
  };
}

export type OffsetTargetsResponse =
  | OffsetAnalyticalSuccess<OffsetTarget, "targets">
  | OffsetFailure;

export type OffsetCandidatesResponse =
  | OffsetAnalyticalSuccess<OffsetCandidate, "candidates">
  | OffsetFailure;

export type OffsetCompareResponse =
  | OffsetAnalyticalSuccess<OffsetComparison, "compare">
  | OffsetFailure;

export interface OffsetApi {
  targets(signal?: AbortSignal): Promise<OffsetTargetsResponse>;
  candidates(
    context: OffsetContext,
    signal?: AbortSignal,
  ): Promise<OffsetCandidatesResponse>;
  compare(
    context: OffsetContext,
    signal?: AbortSignal,
  ): Promise<OffsetCompareResponse>;
}
