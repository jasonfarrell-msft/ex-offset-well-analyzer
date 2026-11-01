import { useEffect, useMemo, useRef, useState } from "react";
import { ChatApiError, createChatApi, createOffsetApi } from "../lib/api";
import type {
  ChatApi,
  OffsetApi,
  OffsetCandidate,
  OffsetCandidatesResponse,
  OffsetComparison,
  OffsetCompareResponse,
  OffsetContext,
  OffsetCriteria,
  OffsetEvidence,
  OffsetEventContext,
  OffsetExclusion,
  OffsetMatchingSection,
  OffsetRunTuple,
  OffsetTarget,
} from "../types";
import { MarkdownContent } from "../components/MarkdownContent";

const defaultCriteria: OffsetCriteria = {
  radiusFt: "10000",
  formationMatch: true,
  holeSizeMatch: true,
  mdOverlap: false,
};
const DEFAULT_OFFSET_DISCLOSURE_CONTRACT_VERSION = "offset-well-analysis-v2";
const DEFAULT_OFFSET_DISCLOSURE_RELEASE_ID =
  "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0";
const defaultOffsetApi = createOffsetApi();
const defaultChatApi = createChatApi();

interface OffsetAnalysisProps {
  offsetApi?: OffsetApi;
  chatApi?: ChatApi;
}

interface FollowupMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

interface OffsetDisclosureVersion {
  contractVersion: string;
  releaseId: string;
}

type ResultsStage = "compare" | "brief";

export function OffsetAnalysis({
  offsetApi = defaultOffsetApi,
  chatApi = defaultChatApi,
}: OffsetAnalysisProps) {
  const mainRef = useRef<HTMLElement | null>(null);
  const loadingOverlayRef = useRef<HTMLDivElement | null>(null);
  const compareRequestGenerationRef = useRef(0);
  const compareAbortControllerRef = useRef<AbortController | null>(null);
  const followupAbortControllerRef = useRef<AbortController | null>(null);

  const [targets, setTargets] = useState<OffsetTarget[]>([]);
  const [targetsLoading, setTargetsLoading] = useState(true);
  const [targetsError, setTargetsError] = useState<string | null>(null);
  const [disclosureVersion, setDisclosureVersion] =
    useState<OffsetDisclosureVersion | null>(null);

  const [targetId, setTargetId] = useState("");
  const [criteria, setCriteria] = useState<OffsetCriteria>({ ...defaultCriteria });
  const [selectedWellIds, setSelectedWellIds] = useState<string[]>([]);
  const [contextRevision, setContextRevision] = useState(0);

  const [candidatesResult, setCandidatesResult] =
    useState<OffsetCandidatesResponse | null>(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [initialCandidatesResolved, setInitialCandidatesResolved] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  const [compareResult, setCompareResult] = useState<OffsetCompareResponse | null>(
    null,
  );
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [compareCompletionMessage, setCompareCompletionMessage] =
    useState<string | null>(null);
  const [activePane, setActivePane] = useState<"selection" | "results">("selection");
  const [resultsStage, setResultsStage] = useState<ResultsStage>("compare");
  const [selectedReferenceWellId, setSelectedReferenceWellId] = useState<string | null>(
    null,
  );
  const [referenceRationale, setReferenceRationale] = useState("");

  const [followupMessages, setFollowupMessages] = useState<FollowupMessage[]>([]);
  const [followupConversationId, setFollowupConversationId] = useState<
    string | undefined
  >(undefined);
  const [followupDraft, setFollowupDraft] = useState("");
  const [followupBusy, setFollowupBusy] = useState(false);
  const [followupError, setFollowupError] = useState<string | null>(null);

  const target = targets.find((value) => value.targetId === targetId) ?? null;
  const candidates = useMemo(() => {
    if (!candidatesResult || candidatesResult.status !== "success") return [];
    return candidatesResult.rows as OffsetCandidate[];
  }, [candidatesResult]);
  const compareContextIdentity = useMemo(
    () => JSON.stringify(buildContext(targetId, criteria, selectedWellIds, contextRevision)),
    [targetId, criteria, selectedWellIds, contextRevision],
  );
  const compareContextIdentityRef = useRef(compareContextIdentity);

  useEffect(() => {
    compareContextIdentityRef.current = compareContextIdentity;
  }, [compareContextIdentity]);

  const cancelInFlightCompare = () => {
    compareRequestGenerationRef.current += 1;
    compareAbortControllerRef.current?.abort();
    compareAbortControllerRef.current = null;
    setCompareLoading(false);
  };

  const cancelInFlightFollowup = () => {
    followupAbortControllerRef.current?.abort();
    followupAbortControllerRef.current = null;
    setFollowupBusy(false);
  };

  const resetReferenceDecision = () => {
    setResultsStage("compare");
    setSelectedReferenceWellId(null);
    setReferenceRationale("");
  };

  const invalidateComparisonAndChat = () => {
    cancelInFlightCompare();
    cancelInFlightFollowup();
    setCompareResult(null);
    setCompareError(null);
    setCompareCompletionMessage(null);
    setActivePane("selection");
    resetReferenceDecision();
    setFollowupMessages([]);
    setFollowupConversationId(undefined);
    setFollowupError(null);
  };

  useEffect(() => {
    const controller = new AbortController();
    setTargetsLoading(true);
    setInitialCandidatesResolved(false);
    setTargetsError(null);

    void offsetApi
      .targets(controller.signal)
      .then((response) => {
        if (response.status !== "success") {
          setTargets([]);
          setTargetsError(toFailureMessage(response));
          return;
        }

        setDisclosureVersion({
          contractVersion: response.contractVersion,
          releaseId: response.releaseId,
        });
        setTargets(response.rows);
        setTargetId((current) => current || response.rows[0]?.targetId || "");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setTargets([]);
        setTargetsError(toUnknownMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setTargetsLoading(false);
      });

    return () => controller.abort();
  }, [offsetApi]);

  useEffect(() => {
    if (!targetId || !isRadiusValid(criteria.radiusFt)) {
      setCandidatesLoading(false);
      if (!targetsLoading) setInitialCandidatesResolved(true);
      return;
    }

    const controller = new AbortController();
    setCandidatesLoading(true);
    setCandidatesError(null);

    void offsetApi
      .candidates(buildContext(targetId, criteria, [], contextRevision), controller.signal)
      .then((response) => {
        if (response.status === "success" || response.status === "empty") {
          setDisclosureVersion({
            contractVersion: response.contractVersion,
            releaseId: response.releaseId,
          });
        }
        setCandidatesResult(response);
        if (response.status !== "success" && response.status !== "empty") {
          setCandidatesError(toFailureMessage(response));
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setCandidatesResult(null);
        setCandidatesError(toUnknownMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setCandidatesLoading(false);
          setInitialCandidatesResolved(true);
        }
      });

    return () => controller.abort();
  }, [offsetApi, targetId, criteria, contextRevision, targetsLoading]);

  useEffect(
    () => () => {
      compareAbortControllerRef.current?.abort();
      followupAbortControllerRef.current?.abort();
    },
    [],
  );

  const initialCandidatesPending =
    !targetsLoading && !initialCandidatesResolved && !targetsError;
  const blockingLoadPhase: "targets" | "candidates" | "compare" | null = targetsLoading
    ? "targets"
    : (initialCandidatesPending || candidatesLoading)
      ? "candidates"
      : compareLoading
        ? "compare"
        : null;
  const isBlockingDatasetLoad = blockingLoadPhase !== null;

  useEffect(() => {
    if (!isBlockingDatasetLoad) return;

    const overlayElement = loadingOverlayRef.current;
    const previousActiveElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const navigation = document.querySelector<HTMLElement>(".dev-nav");
    const hadNavAriaHidden = navigation?.getAttribute("aria-hidden") ?? null;
    const hadNavInert = navigation?.hasAttribute("inert") ?? false;
    navigation?.setAttribute("aria-hidden", "true");
    navigation?.setAttribute("inert", "");

    mainRef.current?.setAttribute("aria-hidden", "true");
    mainRef.current?.setAttribute("inert", "");

    overlayElement?.focus();

    const blockBackgroundInteraction = (event: Event) => {
      if (!overlayElement) return;
      if (event.target instanceof Node && overlayElement.contains(event.target)) return;
      event.preventDefault();
      event.stopPropagation();
    };

    document.addEventListener("pointerdown", blockBackgroundInteraction, true);
    document.addEventListener("click", blockBackgroundInteraction, true);
    document.addEventListener("keydown", blockBackgroundInteraction, true);

    return () => {
      document.removeEventListener("pointerdown", blockBackgroundInteraction, true);
      document.removeEventListener("click", blockBackgroundInteraction, true);
      document.removeEventListener("keydown", blockBackgroundInteraction, true);
      document.body.style.overflow = previousOverflow;

      if (navigation) {
        if (hadNavAriaHidden === null) navigation.removeAttribute("aria-hidden");
        else navigation.setAttribute("aria-hidden", hadNavAriaHidden);

        if (hadNavInert) navigation.setAttribute("inert", "");
        else navigation.removeAttribute("inert");
      }

      mainRef.current?.removeAttribute("aria-hidden");
      mainRef.current?.removeAttribute("inert");

      if (
        previousActiveElement
        && typeof previousActiveElement.focus === "function"
        && document.contains(previousActiveElement)
      ) {
        previousActiveElement.focus();
      }
    };
  }, [isBlockingDatasetLoad]);

  const invalidateContext = (next: {
    targetId?: string;
    criteria?: OffsetCriteria;
    clearSelection?: boolean;
  }) => {
    if (next.targetId !== undefined) setTargetId(next.targetId);
    if (next.criteria) setCriteria(next.criteria);
    if (next.clearSelection !== false) setSelectedWellIds([]);
    invalidateComparisonAndChat();
    setContextRevision((value) => value + 1);
  };

  const toggleSelection = (wellId: string) => {
    setSelectedWellIds((current) => {
      const exists = current.includes(wellId);
      if (exists) {
        return current.filter((value) => value !== wellId);
      }
      if (current.length >= 5) return current;
      return [...current, wellId];
    });
    invalidateComparisonAndChat();
  };

  const compare = async () => {
    if (!targetId || selectedWellIds.length === 0 || !isRadiusValid(criteria.radiusFt)) {
      return;
    }

    const context = buildContext(targetId, criteria, selectedWellIds, contextRevision);
    const requestContextIdentity = JSON.stringify(context);
    const requestGeneration = compareRequestGenerationRef.current + 1;
    compareRequestGenerationRef.current = requestGeneration;
    compareAbortControllerRef.current?.abort();
    const controller = new AbortController();
    compareAbortControllerRef.current = controller;

    setCompareLoading(true);
    setCompareError(null);
    setCompareCompletionMessage(null);
    resetReferenceDecision();

    try {
      const response = await offsetApi.compare(context, controller.signal);
      if (controller.signal.aborted) return;
      if (
        requestGeneration !== compareRequestGenerationRef.current
        || requestContextIdentity !== compareContextIdentityRef.current
      ) {
        return;
      }

      if (response.status === "success" || response.status === "empty") {
        setDisclosureVersion({
          contractVersion: response.contractVersion,
          releaseId: response.releaseId,
        });
      }
      setCompareResult(response);
      if (response.status !== "success") {
        setCompareError(toFailureMessage(response));
        return;
      }
      setCompareCompletionMessage(
        `Comparison ready for ${response.rows.length} selected `
        + `${response.rows.length === 1 ? "well" : "wells"}.`,
      );
      setResultsStage("compare");
      setActivePane("results");
    } catch (error) {
      if (controller.signal.aborted) return;
      if (requestGeneration !== compareRequestGenerationRef.current) return;
      setCompareResult(null);
      setCompareError(toUnknownMessage(error));
      setCompareCompletionMessage(null);
      resetReferenceDecision();
      setActivePane("selection");
    } finally {
      if (compareAbortControllerRef.current === controller) {
        compareAbortControllerRef.current = null;
      }
      if (requestGeneration === compareRequestGenerationRef.current) {
        setCompareLoading(false);
      }
    }
  };

  const sendFollowup = async () => {
    const message = followupDraft.trim();
    const successCompare =
      compareResult && compareResult.status === "success" ? compareResult : null;
    const compareContext = successCompare?.context ?? null;
    if (!message || !compareContext || !successCompare || followupBusy) return;

    followupAbortControllerRef.current?.abort();
    const controller = new AbortController();
    followupAbortControllerRef.current = controller;
    setFollowupBusy(true);
    setFollowupError(null);
    setFollowupDraft("");
    setFollowupMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: message },
    ]);

    try {
      const response = await chatApi.send({
        message,
        ...(followupConversationId ? { conversationId: followupConversationId } : {}),
        offsetContext: {
          contractVersion: successCompare.contractVersion,
          releaseId: successCompare.releaseId,
          context: compareContext,
        },
      }, controller.signal);
      if (controller.signal.aborted) return;

      setFollowupConversationId(response.conversationId);
      setFollowupMessages((current) => [
        ...current,
        {
          id: response.message.id,
          role: "assistant",
          text: response.message.markdown,
        },
      ]);
    } catch (error) {
      if (controller.signal.aborted) return;
      setFollowupError(toUnknownMessage(error));
    } finally {
      if (followupAbortControllerRef.current === controller) {
        followupAbortControllerRef.current = null;
        setFollowupBusy(false);
      }
    }
  };

  const canCompare = selectedWellIds.length > 0 && isRadiusValid(criteria.radiusFt);
  const successfulCompare =
    compareResult && compareResult.status === "success" ? compareResult : null;
  const comparedWellIds = useMemo(
    () => new Set(successfulCompare?.rows.map((row) => row.wellId) ?? []),
    [successfulCompare],
  );
  const selectedReferenceRow =
    selectedReferenceWellId && successfulCompare
      ? successfulCompare.rows.find((row) => row.wellId === selectedReferenceWellId) ?? null
      : null;
  const referenceBrief =
    selectedReferenceRow && successfulCompare
      ? buildReferenceDecisionBrief({
          target,
          referenceRow: selectedReferenceRow,
          selectedWellIds: successfulCompare.context?.selectedWellIds ?? [],
          criteria: successfulCompare.context?.criteria ?? criteria,
          contextRevision: successfulCompare.context?.contextRevision ?? contextRevision,
          releaseId: successfulCompare.releaseId,
          contractVersion: successfulCompare.contractVersion,
          evidence: successfulCompare.evidence,
          userRationale: referenceRationale,
        })
      : null;

  useEffect(() => {
    if (!successfulCompare) {
      resetReferenceDecision();
      return;
    }
    if (selectedReferenceWellId && !comparedWellIds.has(selectedReferenceWellId)) {
      setSelectedReferenceWellId(null);
      setResultsStage("compare");
    }
  }, [successfulCompare, selectedReferenceWellId, comparedWellIds]);

  const disclosureContractVersion =
    disclosureVersion?.contractVersion ?? DEFAULT_OFFSET_DISCLOSURE_CONTRACT_VERSION;
  const disclosureReleaseId =
    disclosureVersion?.releaseId ?? DEFAULT_OFFSET_DISCLOSURE_RELEASE_ID;
  const disclosureDataReleaseVersion = toReleaseVersion(disclosureReleaseId);

  return (
    <>
      {blockingLoadPhase && (
        <div
          className="offset-loading-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="offset-loading-title"
          aria-describedby="offset-loading-description"
          ref={loadingOverlayRef}
          tabIndex={-1}
        >
          <div className="offset-loading-panel" role="status" aria-live="assertive" aria-atomic="true">
            <div className="offset-loading-spinner" aria-hidden="true" />
            <h2 id="offset-loading-title">Loading offset workspace data</h2>
            <p id="offset-loading-description">{toBlockingLoadMessage(blockingLoadPhase)}</p>
          </div>
        </div>
      )}
      <main
        className="offset-preview"
        aria-label="Offset well analysis workspace"
        aria-busy={isBlockingDatasetLoad}
        ref={mainRef}
      >
      <aside className="offset-disclosure" aria-label="Offset analysis disclosure">
        <strong>SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY</strong>
        <p>
          API contract <code>{disclosureContractVersion}</code> ·
          Data release <code>{disclosureDataReleaseVersion}</code> ·
          Release ID <code>{disclosureReleaseId}</code>
        </p>
        <p>
          Live requests use <code>/api/offset-analysis</code>. Results render only
          from successful API responses; no local snapshot fallback is used.
        </p>
      </aside>

      <header className="offset-intro">
        <div>
          <p className="offset-eyebrow">LIVE OFFSET ANALYSIS</p>
          <h1>Offset well analysis</h1>
          <p>
            Select a planned target, load candidate wells, manually choose 1–5,
            compare, then optionally ask follow-up chat questions grounded to the
            selected context.
          </p>
        </div>
      </header>

      <div className="offset-grid">
        <section className="offset-card offset-controls" aria-labelledby="offset-scope-title">
          <h2 id="offset-scope-title">1–2 / Define your scope</h2>
          <label htmlFor="offset-target">Planned target</label>
          <select
            id="offset-target"
            value={targetId}
            disabled={targetsLoading || targets.length === 0}
            onChange={(event) =>
              invalidateContext({ targetId: event.target.value, clearSelection: true })
            }
          >
            {targets.map((row) => (
              <option key={row.targetId} value={row.targetId}>
                {row.targetId} · {row.fieldName}
              </option>
            ))}
          </select>

          {targetsLoading && <p className="offset-help">Loading targets…</p>}
          {targetsError && (
            <div className="offset-empty" role="alert">
              <h3>Unable to load targets</h3>
              <p>{targetsError}</p>
            </div>
          )}

          {target && (
            <div className="offset-target">
              <span className="offset-pill">PLANNED TARGET</span>
              <h3>{target.expectedFormationName}</h3>
              <dl>
                <dt>Basin / field</dt>
                <dd>
                  {target.basinName} / {target.fieldName}
                </dd>
                <dt>Planned hole size</dt>
                <dd>{target.plannedHoleSizeIn} in</dd>
                <dt>Planned MD interval</dt>
                <dd>
                  {target.plannedMdMinFt}–{target.plannedMdMaxFt} ft
                </dd>
                <dt>Planned trajectory</dt>
                <dd>{target.plannedTrajectoryProfile.replaceAll("_", " ")}</dd>
                <dt>Planned target intent</dt>
                <dd>
                  Bit: {toDisplayValue(target.plannedBitType)} ·
                  BHA: {toDisplayValue(target.plannedBhaType)} ·
                  Mud: {toDisplayValue(target.plannedMudType)}
                </dd>
              </dl>
            </div>
          )}

          <label htmlFor="offset-radius">Surface radius (ft)</label>
          <input
            id="offset-radius"
            type="number"
            min="0"
            max="3000000"
            step="any"
            value={criteria.radiusFt}
            aria-invalid={!isRadiusValid(criteria.radiusFt)}
            onChange={(event) =>
              invalidateContext({
                criteria: { ...criteria, radiusFt: event.target.value },
                clearSelection: true,
              })
            }
          />
          <p className={isRadiusValid(criteria.radiusFt) ? "offset-help" : "offset-invalid"}>
            {isRadiusValid(criteria.radiusFt)
              ? "0–3,000,000 ft; up to 6 decimals."
              : "Enter a radius from 0 to 3,000,000 ft with up to 6 decimals."}
          </p>

          <fieldset>
            <legend>Apply to the same historical section</legend>
            <label className="offset-check">
              <input
                type="checkbox"
                checked={criteria.formationMatch}
                onChange={(event) =>
                  invalidateContext({
                    criteria: { ...criteria, formationMatch: event.target.checked },
                    clearSelection: true,
                  })
                }
              />
              Same canonical formation
            </label>
            <label className="offset-check">
              <input
                type="checkbox"
                checked={criteria.holeSizeMatch}
                onChange={(event) =>
                  invalidateContext({
                    criteria: { ...criteria, holeSizeMatch: event.target.checked },
                    clearSelection: true,
                  })
                }
              />
              Same hole size
            </label>
            <label className="offset-check">
              <input
                type="checkbox"
                checked={criteria.mdOverlap}
                onChange={(event) =>
                  invalidateContext({
                    criteria: { ...criteria, mdOverlap: event.target.checked },
                    clearSelection: true,
                  })
                }
              />
              Strict planned MD overlap
            </label>
          </fieldset>
          <button
            type="button"
            className="offset-secondary"
            onClick={() => invalidateContext({ criteria: { ...defaultCriteria } })}
          >
            Reset filters
          </button>
        </section>

        {activePane === "selection" && (
          <section className="offset-card offset-candidates" aria-labelledby="offset-candidates-title">
            <div className="offset-section-heading">
              <div>
                <h2 id="offset-candidates-title">3 / Select historical wells</h2>
                <p>Nearest first · API-provided order</p>
              </div>
              <span className="offset-count">
                {candidatesResult?.status === "success"
                  ? `${candidatesResult.totalCount} eligible`
                  : "No result"}
              </span>
            </div>

            <div className="offset-selection" role="status" aria-live="polite">
              <div className="offset-selection-main">
                <span>
                  <strong>{selectedWellIds.length} of 5 selected</strong> ·
                  {selectedWellIds.length === 5
                    ? " limit reached"
                    : " select wells manually"}
                </span>
                <button
                  type="button"
                  className="offset-primary"
                  disabled={!canCompare || compareLoading}
                  onClick={() => void compare()}
                >
                  {compareLoading
                    ? "Comparing…"
                    : `Compare selected (${selectedWellIds.length})`}
                </button>
              </div>
              <div className="offset-compare-feedback">
                <p className="offset-compare-status" role="status" aria-live="polite">
                  {compareCompletionMessage}
                </p>
                {compareResult?.status === "success" && (
                  <button
                    type="button"
                    className="offset-secondary"
                    onClick={() => setActivePane("results")}
                  >
                    View comparison
                  </button>
                )}
              </div>
            </div>

            {compareError && (
              <div className="offset-empty" role="alert">
                <h3>Comparison unavailable</h3>
                <p>{compareError}</p>
              </div>
            )}

            {candidatesLoading && (
              <div className="offset-empty" role="status">
                <h3>Loading candidates</h3>
                <p>Fetching candidates for the current target and filter context.</p>
              </div>
            )}

            {candidatesError && (
              <div className="offset-empty" role="alert">
                <h3>Unable to load candidates</h3>
                <p>{candidatesError}</p>
              </div>
            )}

            {!candidatesLoading && !candidatesError && (
              <>
                {candidatesResult?.status === "empty" && (
                  <div className="offset-empty">
                    <h3>No matching historical wells</h3>
                    <p>
                      No eligible candidates were returned for this context.
                      Update filters and retry.
                    </p>
                  </div>
                )}

                {candidatesResult?.status === "success" && (
                  <ul className="offset-candidate-list">
                    {candidates.map((candidate) => {
                      const selected = selectedWellIds.includes(candidate.wellId);
                      const limitReached = selectedWellIds.length >= 5 && !selected;
                      return (
                        <li key={candidate.wellId}>
                          <label
                            className={`offset-candidate${selected ? " is-selected" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={selected}
                              disabled={limitReached}
                              aria-label={`Select ${candidate.wellId}`}
                              onChange={() => toggleSelection(candidate.wellId)}
                            />
                            <span className="offset-candidate-body">
                              <strong>{candidate.wellName}</strong>
                              <span className="offset-well-id">
                                {candidate.wellId} · {candidate.fieldName}
                              </span>
                              <span>
                                {candidate.metrics.matchingSectionCount} matching sections
                                · {candidate.metrics.acceptedRunCount} accepted runs
                              </span>
                            </span>
                            <span className="offset-distance">
                              <strong>{candidate.distanceFt} ft</strong>
                              <small>surface distance</small>
                            </span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </>
            )}
          </section>
        )}

        {activePane === "results" && (
          <section className="offset-card offset-candidates" aria-labelledby="offset-compare-title">
            <div className="offset-section-heading">
              <div>
                <h2 id="offset-compare-title">4 / Compare accepted historical summaries</h2>
                <p>Comparison for the current selected context.</p>
              </div>
              <button
                type="button"
                className="offset-secondary"
                onClick={() => setActivePane("selection")}
              >
                Edit selection
              </button>
            </div>
            <div className="offset-selection">
              <div className="offset-selection-main">
                <span>
                  <strong>{selectedWellIds.length} selected</strong> ·
                  comparison context revision {compareResult?.context?.contextRevision ?? contextRevision}
                </span>
                <button
                  type="button"
                  className="offset-secondary"
                  onClick={() => setActivePane("selection")}
                >
                  Back to selection
                </button>
              </div>
              {compareCompletionMessage && (
                <p className="offset-compare-status" role="status" aria-live="polite">
                  {compareCompletionMessage}
                </p>
              )}
            </div>

            {compareResult?.status === "success" && (
              <>
                {resultsStage === "compare" && (
                  <ComparisonTable
                    rows={compareResult.rows}
                    candidates={candidates}
                    target={target}
                    criteria={compareResult.context?.criteria ?? criteria}
                    selectedReferenceWellId={selectedReferenceWellId}
                    onSelectReference={(wellId) => {
                      if (!comparedWellIds.has(wellId)) return;
                      setSelectedReferenceWellId(wellId);
                    }}
                    referenceRationale={referenceRationale}
                    onReferenceRationaleChange={setReferenceRationale}
                    onCreateBrief={() => {
                      if (!selectedReferenceRow) return;
                      setResultsStage("brief");
                    }}
                  />
                )}
                {resultsStage === "brief" && referenceBrief && (
                  <ReferenceDecisionBriefPanel
                    brief={referenceBrief}
                    onBackToComparison={() => setResultsStage("compare")}
                    onChangeReference={() => setResultsStage("compare")}
                  />
                )}
                <ProvenancePanel
                  releaseId={compareResult.releaseId}
                  contractVersion={compareResult.contractVersion}
                  contextRevision={compareResult.context?.contextRevision ?? 0}
                  contextHash={compareResult.contextHash}
                  evidence={compareResult.evidence}
                  exclusions={compareResult.exclusions}
                />
                <FollowupChat
                  draft={followupDraft}
                  busy={followupBusy}
                  error={followupError}
                  messages={followupMessages}
                  onChange={setFollowupDraft}
                  onSend={() => void sendFollowup()}
                />
              </>
            )}
          </section>
        )}
      </div>
      </main>
    </>
  );
}

function ComparisonTable({
  rows,
  candidates,
  target,
  criteria,
  selectedReferenceWellId,
  onSelectReference,
  referenceRationale,
  onReferenceRationaleChange,
  onCreateBrief,
}: {
  rows: OffsetComparison[];
  candidates: OffsetCandidate[];
  target: OffsetTarget | null;
  criteria: OffsetCriteria;
  selectedReferenceWellId: string | null;
  onSelectReference: (wellId: string) => void;
  referenceRationale: string;
  onReferenceRationaleChange: (value: string) => void;
  onCreateBrief: () => void;
}) {
  const nameByWellId = new Map(candidates.map((candidate) => [candidate.wellId, candidate.wellName]));
  const plannedBitType = firstDefined([
    target?.plannedBitType,
    ...rows.map((row) => row.plannedBitType),
  ]);
  const plannedBhaType = firstDefined([
    target?.plannedBhaType,
    ...rows.map((row) => row.plannedBhaType),
  ]);
  const plannedMudType = firstDefined([
    target?.plannedMudType,
    ...rows.map((row) => row.plannedMudType),
  ]);
  const metrics: [string, (row: OffsetComparison) => string][] = [
    ["Matching sections", (row) => String(row.metrics.matchingSectionCount)],
    ["Accepted runs", (row) => String(row.metrics.acceptedRunCount)],
    ["Warning runs", (row) => String(row.metrics.warningRunCount)],
    ["Warning sections", (row) => String(row.metrics.warningSectionCount)],
    ["Warning issues", (row) => String(row.metrics.warningIssueCount)],
    ["Quarantined runs", (row) => String(row.metrics.quarantinedRunCount)],
    ["Accepted footage (ft)", (row) => row.metrics.acceptedFootageFt ?? "Unavailable"],
    ["Accepted duration (hours)", (row) => row.metrics.acceptedDurationHours ?? "Unavailable"],
    ["Average footage/run (ft/run)", (row) => row.metrics.averageFootagePerRunFt ?? "Unavailable"],
    [
      "Accepted footage ÷ accepted duration (summary ft/hour)",
      (row) => row.metrics.summaryPenetrationRateFtPerHour ?? "Unavailable",
    ],
  ];

  return (
    <>
      <aside className="offset-synthetic-context-disclosure" role="note">
        Synthetic comparison context only: operational events are generated synthetic
        comparison signals, not field telemetry and not drilling recommendations.
      </aside>

      <section className="offset-planned-intent" aria-label="Planned target intent">
        <h3>Planned target intent (if provided)</h3>
        <dl>
          <dt>Bit type</dt>
          <dd>{toDisplayValue(plannedBitType)}</dd>
          <dt>BHA type</dt>
          <dd>{toDisplayValue(plannedBhaType)}</dd>
          <dt>Mud type</dt>
          <dd>{toDisplayValue(plannedMudType)}</dd>
        </dl>
      </section>

      <section className="offset-planned-intent" aria-label="Reference well selection">
        <h3>5 / Choose reference well</h3>
        <p>
          Select one compared well as a human planning reference. This does not rank wells
          or predict target performance.
        </p>
        <ul className="offset-candidate-list">
          {rows.map((row) => {
            const selected = selectedReferenceWellId === row.wellId;
            return (
              <li key={`${row.wellId}:reference`}>
                <label className={`offset-candidate${selected ? " is-selected" : ""}`}>
                  <input
                    type="radio"
                    name="offset-reference-well"
                    checked={selected}
                    aria-label={`Use ${row.wellId} as reference`}
                    onChange={() => onSelectReference(row.wellId)}
                  />
                  <span className="offset-candidate-body">
                    <strong>
                      {row.wellId} · {nameByWellId.get(row.wellId) ?? "Candidate name unavailable"}
                    </strong>
                    <span>
                      {row.metrics.matchingSectionCount} matching sections ·
                      {" "}
                      {row.metrics.acceptedRunCount} accepted runs ·
                      {" "}
                      warnings {row.metrics.warningRunCount} / quarantined {row.metrics.quarantinedRunCount}
                    </span>
                    {toReferenceFitNarrative(row, target, criteria).map((line) => (
                      <span key={`${row.wellId}:${line}`}>{line}</span>
                    ))}
                    <details>
                      <summary>Matching section details ({row.matchingSections.length})</summary>
                      <ul className="offset-context-list">
                        {row.matchingSections.map((section) => (
                          <li key={section.sectionId}>{formatSection(section)}</li>
                        ))}
                      </ul>
                    </details>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        <label htmlFor="offset-reference-rationale" className="offset-help">
          Optional rationale (workspace-only note)
        </label>
        <textarea
          id="offset-reference-rationale"
          value={referenceRationale}
          onChange={(event) => onReferenceRationaleChange(event.target.value)}
          maxLength={500}
          rows={3}
          placeholder="Why does this reference seem compatible for planning context?"
        />
        <button
          type="button"
          className="offset-primary"
          disabled={!selectedReferenceWellId}
          onClick={onCreateBrief}
        >
          Create target expectation brief
        </button>
      </section>

      <div className="offset-table-scroll" role="region" aria-label="Selected historical well comparison" tabIndex={0}>
        <p className="offset-help" style={{ margin: "0 22px 12px" }}>
          The ft/hour value is a broad historical ratio over accepted footage and duration from whole
          matching sections. Do not use it alone to rank wells or project target ROP.
        </p>
        <table>
          <caption>Accepted synthetic history for the selected live context</caption>
          <thead>
            <tr>
              <th scope="col">Historical metric</th>
              {rows.map((row) => (
                <th scope="col" key={row.wellId}>
                  {row.wellId}
                  <small>{nameByWellId.get(row.wellId) ?? "Candidate name unavailable"}</small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(([label, render]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                {rows.map((row) => (
                  <td key={`${label}:${row.wellId}`}>{render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="offset-section-evidence">
          {rows.map((row) => (
            <details key={row.wellId}>
              <summary>
                {row.wellId} · inspect {row.matchingSections.length} matching sections
              </summary>
              <ul>
                {row.matchingSections.map((section) => (
                  <li key={section.sectionId}>{formatSection(section)}</li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </div>

      <div className="offset-context-grid">
        <aside className="offset-synthetic-context-disclosure" role="note">
          Well context cards are broader than matching-section metrics: run configuration tuples and event
          context are aggregated by well ID and do not share the same filtered denominator as matching
          section metrics.
        </aside>
        {rows.map((row) => (
          <section key={`${row.wellId}:context`} className="offset-context-card" aria-label={`${row.wellId} synthetic context`}>
            <h3>{row.wellId} observed well context (broader than matching-section metrics)</h3>
            <ObservedRunTupleList runTuples={row.runConfigContext?.runTuples ?? null} />
            <EventContextSummary eventContext={row.eventContext ?? null} />
          </section>
        ))}
      </div>
    </>
  );
}

function ObservedRunTupleList({ runTuples }: { runTuples: OffsetRunTuple[] | null }) {
  if (!runTuples || runTuples.length === 0) {
    return (
      <p className="offset-context-unavailable">
        Well-wide configuration tuples: unavailable in this response.
      </p>
    );
  }

  return (
    <details>
      <summary>Well-wide configuration tuples ({runTuples.length})</summary>
      <ul className="offset-context-list">
        {runTuples.map((tuple, index) => (
          <li key={`tuple:${index}`}>
            <strong>
              Bit {toDisplayValue(tuple.bitType)} · BHA {toDisplayValue(tuple.bhaType)} ·
              Mud {toDisplayValue(tuple.mudType)}
            </strong>
            <span>
              Mud weight: {toDisplayValue(tuple.mudWeightPpg)} ppg · Funnel viscosity: {toDisplayValue(tuple.mudFunnelViscositySec)} sec
            </span>
            <span>
              Well-wide tuple totals — accepted runs: {toDisplayValue(tuple.acceptedRunCount)} ·
              Footage: {toDisplayValue(tuple.acceptedFootageFt)} ft ·
              Duration: {toDisplayValue(tuple.acceptedDurationHours)} hours
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function EventContextSummary({ eventContext }: { eventContext: OffsetEventContext | null }) {
  if (!eventContext) {
    return (
      <p className="offset-context-unavailable">
        Synthetic operational event context: unavailable in this response.
      </p>
    );
  }

  return (
    <details>
      <summary>Observed well context events (well-wide)</summary>
      <p>
        Well-wide event totals — count: {toDisplayValue(eventContext.totalEventCount)} ·
        duration: {toDisplayValue(eventContext.totalEventDurationHours)} hours
      </p>
      {eventContext.byType && eventContext.byType.length > 0 ? (
        <>
          <p><strong>By type</strong></p>
          <ul className="offset-context-list">
            {eventContext.byType.map((item, index) => (
              <li key={`type:${item.eventType}:${index}`}>
                {item.eventType}: {toDisplayValue(item.eventCount)} events ·
                {toDisplayValue(item.eventDurationHours)} hours
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="offset-context-unavailable">By type: unavailable in this response.</p>
      )}
      {eventContext.bySubtype && eventContext.bySubtype.length > 0 ? (
        <>
          <p><strong>By subtype</strong></p>
          <ul className="offset-context-list">
            {eventContext.bySubtype.map((item, index) => (
              <li key={`subtype:${item.eventType}:${item.eventSubtype}:${index}`}>
                {item.eventType} / {item.eventSubtype}: {toDisplayValue(item.eventCount)} events ·
                {toDisplayValue(item.eventDurationHours)} hours
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="offset-context-unavailable">By subtype: unavailable in this response.</p>
      )}
    </details>
  );
}

interface ReferenceDecisionBrief {
  createdAtUtc: string;
  targetId: string;
  referenceWellId: string;
  selectedWellIds: string[];
  criteria: OffsetCriteria;
  releaseId: string;
  contractVersion: string;
  contextRevision: number;
  receiptId: string;
  matchingSectionCount: number;
  acceptedRunCount: number;
  warningRunCount: number;
  warningSectionCount: number;
  warningIssueCount: number;
  quarantinedRunCount: number;
  plannedIntent: {
    bitType: string;
    bhaType: string;
    mudType: string;
  };
  fitHighlights: string[];
  caveats: string[];
  missingInfo: string[];
  observedMudWeightRangePpg: string | null;
  observedMudViscosityRangeSec: string | null;
  userRationale: string | null;
}

function ReferenceDecisionBriefPanel({
  brief,
  onBackToComparison,
  onChangeReference,
}: {
  brief: ReferenceDecisionBrief;
  onBackToComparison: () => void;
  onChangeReference: () => void;
}) {
  const downloadHref = `data:application/json;charset=utf-8,${encodeURIComponent(
    JSON.stringify(brief, null, 2),
  )}`;
  return (
    <section className="offset-metric-notes" aria-label="Target expectation evidence brief">
      <strong>6 / Target expectation evidence brief</strong>
      <p>
        Target <code>{brief.targetId}</code> using reference <code>{brief.referenceWellId}</code>
        {" "}under context revision {brief.contextRevision}.
      </p>
      <p>
        Contract <code>{brief.contractVersion}</code> · Release <code>{brief.releaseId}</code> ·
        Receipt <code>{brief.receiptId}</code>.
      </p>
      <p>
        Matching sections {brief.matchingSectionCount} and accepted runs {brief.acceptedRunCount}
        {" "}for this reference row. Warning runs {brief.warningRunCount}; warning sections{" "}
        {brief.warningSectionCount}; warning issues {brief.warningIssueCount}; quarantined runs{" "}
        {brief.quarantinedRunCount}.
      </p>
      <p>
        Planned intent available for the target: bit {brief.plannedIntent.bitType}, BHA{" "}
        {brief.plannedIntent.bhaType}, mud {brief.plannedIntent.mudType}.
      </p>
      {brief.fitHighlights.length > 0 && (
        <ul>
          {brief.fitHighlights.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
      <p>
        If used as a planning reference, this history demonstrates qualitative compatibility only
        within the returned matching-section scope plus broader well-wide context. It does not
        transfer performance outcomes to the target.
      </p>
      <p>
        Cannot estimate expected target footage, duration, ft/hour, event projections, or drilling
        parameter recommendations with the current data because run-aligned interval data required
        for target expectation modeling is not in this payload.
      </p>
      <p>
        Synthetic POC evidence only. Correlation in this comparison is not causation and is not field
        approval.
      </p>
      {(brief.observedMudWeightRangePpg || brief.observedMudViscosityRangeSec) && (
        <p>
          Observed tuple ranges: mud weight {brief.observedMudWeightRangePpg ?? "Unavailable"} ppg ·
          funnel viscosity {brief.observedMudViscosityRangeSec ?? "Unavailable"} sec.
        </p>
      )}
      {brief.userRationale && (
        <p>
          User rationale (workspace note): <em>{brief.userRationale}</em>
        </p>
      )}
      {brief.missingInfo.length > 0 && (
        <>
          <p><strong>Missing or insufficient information</strong></p>
          <ul>
            {brief.missingInfo.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}
      {brief.caveats.length > 0 && (
        <>
          <p><strong>Scope caveats</strong></p>
          <ul>
            {brief.caveats.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}
      <div className="offset-selection" style={{ marginTop: 12 }}>
        <button type="button" className="offset-secondary" onClick={onBackToComparison}>
          Back to comparison
        </button>
        <button type="button" className="offset-secondary" onClick={onChangeReference}>
          Change reference
        </button>
        <a className="offset-secondary" href={downloadHref} download={`${brief.targetId}-${brief.referenceWellId}-brief.json`}>
          Download brief JSON
        </a>
      </div>
    </section>
  );
}

function formatSection(section: OffsetMatchingSection): string {
  return [
    section.sectionId,
    section.formationName ?? "Unknown formation",
    section.holeSizeIn ? `${section.holeSizeIn} in` : "Unknown hole size",
    section.startMdFt && section.endMdFt
      ? `MD ${section.startMdFt}–${section.endMdFt} ft`
      : "Unknown MD interval",
    section.trajectoryProfile?.replaceAll("_", " ") ?? "Unknown trajectory",
  ].join(" · ");
}

function ProvenancePanel({
  releaseId,
  contractVersion,
  contextRevision,
  contextHash,
  evidence,
  exclusions,
}: {
  releaseId: string;
  contractVersion: string;
  contextRevision: number;
  contextHash: string | null;
  evidence: OffsetEvidence;
  exclusions: OffsetExclusion[];
}) {
  const toolCallId = toPresentText(evidence.toolCallId);
  const resultId = toPresentText(evidence.resultId);
  const contextHashValue = toPresentText(contextHash);
  const grain = toPresentText(evidence.grain);
  const sources = Array.isArray(evidence.sources) ? evidence.sources : [];
  const qualityCaveats = toPresentTextList(evidence.qualityCaveats);
  const unitEntries = toRecordEntries(evidence.units);
  const denominatorEntries = toRecordEntries(evidence.denominators);

  return (
    <section className="offset-metric-notes" aria-label="Result provenance">
      <strong>Result provenance</strong>
      <p>
        Release <code>{releaseId}</code> · Contract <code>{contractVersion}</code> ·
        Context revision {contextRevision}
      </p>
      <p>
        Receipt <code>{evidence.receiptId}</code> · Request <code>{evidence.requestId}</code> ·
        Completion {evidence.completion}
      </p>
      <p>
        Correlation IDs:{" "}
        {[
          toolCallId ? `toolCallId ${toolCallId}` : null,
          resultId ? `resultId ${resultId}` : null,
          contextHashValue ? `contextHash ${contextHashValue}` : null,
        ].filter((value): value is string => value !== null).join(" · ") || "Unavailable in this response."}
      </p>
      <details>
        <summary>Evidence sources ({sources.length})</summary>
        {sources.length > 0 ? (
          <ul>
            {sources.map((source, index) => {
              const viewName = toPresentText(source.view);
              const columns = toPresentTextList(source.columns);
              const measures = toPresentTextList(source.measures);
              return (
                <li key={`${source.view}:${index}`}>
                  <strong>{viewName ?? "Unnamed source view"}</strong>
                  <div>Columns: {columns.length > 0 ? columns.join(", ") : "Unavailable"}</div>
                  <div>Measures: {measures.length > 0 ? measures.join(", ") : "Unavailable"}</div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p>No source views were returned.</p>
        )}
      </details>
      <details>
        <summary>Grain, units, and denominators</summary>
        <p>Grain: {grain ?? "Unavailable"}</p>
        <p><strong>Units</strong></p>
        {unitEntries.length > 0 ? (
          <ul>
            {unitEntries.map(([name, value]) => (
              <li key={`unit:${name}`}>
                <code>{name}</code>: {value}
              </li>
            ))}
          </ul>
        ) : (
          <p>Units were not returned.</p>
        )}
        <p><strong>Denominators</strong></p>
        {denominatorEntries.length > 0 ? (
          <ul>
            {denominatorEntries.map(([name, value]) => (
              <li key={`denominator:${name}`}>
                <code>{name}</code>: {value}
              </li>
            ))}
          </ul>
        ) : (
          <p>Denominators were not returned.</p>
        )}
      </details>
      <details>
        <summary>Quality caveats</summary>
        {qualityCaveats.length > 0 ? (
          <ul>
            {qualityCaveats.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p>No quality caveats were returned.</p>
        )}
      </details>
      {exclusions.length > 0 && (
        <details>
          <summary>{exclusions.length} exclusions returned</summary>
          <ul>
            {exclusions.map((row) => (
              <li key={row.wellId}>
                {row.wellId}: {row.reasons.join(", ")}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function FollowupChat({
  draft,
  busy,
  error,
  messages,
  onChange,
  onSend,
}: {
  draft: string;
  busy: boolean;
  error: string | null;
  messages: FollowupMessage[];
  onChange: (value: string) => void;
  onSend: () => void;
}) {
  return (
    <section className="offset-metric-notes" aria-label="Offset follow-up chat">
      <strong>Optional follow-up chat for this selected context</strong>
      <p>
        Follow-up prompts are sent to <code>/api/chat</code> with the current
        selected offset context.
      </p>
      {messages.length > 0 && (
        <ul className="offset-candidate-list" aria-label="Follow-up messages">
          {messages.map((message) => (
            <li key={message.id}>
              <div className="offset-candidate">
                <span className="offset-candidate-body">
                  <strong>{message.role === "user" ? "You" : "Drill Advisor"}</strong>
                  {message.role === "assistant" ? (
                    <MarkdownContent markdown={message.text} />
                  ) : (
                    <span>{message.text}</span>
                  )}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="offset-selection">
        <input
          aria-label="Ask follow-up about selected offset context"
          value={draft}
          maxLength={2000}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask a context-grounded follow-up question…"
        />
        <button
          type="button"
          className="offset-primary"
          disabled={busy || draft.trim().length === 0}
          onClick={onSend}
        >
          {busy ? "Sending…" : "Ask follow-up"}
        </button>
      </div>
      {error && (
        <p className="offset-invalid" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function toReleaseVersion(releaseId: string): string {
  const [version] = releaseId.split(":", 1);
  return version || "unknown";
}

function isRadiusValid(value: string): boolean {
  if (!/^\d+(?:\.\d{1,6})?$/.test(value)) return false;
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= 0 && numeric <= 3_000_000;
}

function buildContext(
  targetId: string,
  criteria: OffsetCriteria,
  selectedWellIds: string[],
  contextRevision: number,
): OffsetContext {
  return {
    targetId,
    criteria,
    selectedWellIds: [...selectedWellIds].sort(),
    contextRevision,
  };
}

function toFailureMessage(response: { status: string; error?: { code?: string } }): string {
  const code = response.error?.code;
  if (code) return `The service returned ${code}.`;
  if (response.status === "stale") {
    return "The selected context is stale. Refresh candidates and compare again.";
  }
  if (response.status === "unavailable") {
    return "The offset analysis service is unavailable right now.";
  }
  return "The request could not be completed.";
}

function toUnknownMessage(error: unknown): string {
  if (error instanceof ChatApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return "Unexpected service response.";
}

function toPresentText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function toPresentTextList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => toPresentText(item))
    .filter((item): item is string => item !== null);
}

function toRecordEntries(value: unknown): [string, string][] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value)
    .map(([key, entryValue]) => {
      const text = toPresentText(entryValue);
      return text ? [key, text] : null;
    })
    .filter((entry): entry is [string, string] => entry !== null);
}

function firstDefined(values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    if (value && value.trim().length > 0) return value;
  }
  return null;
}

function toDisplayValue(value: string | number | null | undefined): string {
  if (typeof value === "number") return String(value);
  if (typeof value === "string" && value.trim().length > 0) return value;
  return "Unavailable";
}

function buildReferenceDecisionBrief({
  target,
  referenceRow,
  selectedWellIds,
  criteria,
  contextRevision,
  releaseId,
  contractVersion,
  evidence,
  userRationale,
}: {
  target: OffsetTarget | null;
  referenceRow: OffsetComparison;
  selectedWellIds: string[];
  criteria: OffsetCriteria;
  contextRevision: number;
  releaseId: string;
  contractVersion: string;
  evidence: OffsetEvidence;
  userRationale: string;
}): ReferenceDecisionBrief {
  const runTuples = referenceRow.runConfigContext?.runTuples ?? [];
  const mudWeightRange = toObservedRange(runTuples.map((tuple) => tuple.mudWeightPpg));
  const mudViscosityRange = toObservedRange(
    runTuples.map((tuple) => tuple.mudFunnelViscositySec),
  );
  const missingInfo = [
    target ? null : "Target summary is unavailable in the current UI state.",
    referenceRow.matchingSections.length === 0
      ? "No matching section detail rows were returned for the selected reference."
      : null,
    runTuples.length === 0
      ? "No well-wide run configuration tuples were returned for this reference."
      : null,
    referenceRow.eventContext ? null : "No well-wide event context was returned for this reference.",
  ].filter((value): value is string => value !== null);

  return {
    createdAtUtc: new Date().toISOString(),
    targetId: target?.targetId ?? "Unavailable",
    referenceWellId: referenceRow.wellId,
    selectedWellIds,
    criteria,
    releaseId,
    contractVersion,
    contextRevision,
    receiptId: evidence.receiptId,
    matchingSectionCount: referenceRow.metrics.matchingSectionCount,
    acceptedRunCount: referenceRow.metrics.acceptedRunCount,
    warningRunCount: referenceRow.metrics.warningRunCount,
    warningSectionCount: referenceRow.metrics.warningSectionCount,
    warningIssueCount: referenceRow.metrics.warningIssueCount,
    quarantinedRunCount: referenceRow.metrics.quarantinedRunCount,
    plannedIntent: {
      bitType: toDisplayValue(target?.plannedBitType ?? referenceRow.plannedBitType),
      bhaType: toDisplayValue(target?.plannedBhaType ?? referenceRow.plannedBhaType),
      mudType: toDisplayValue(target?.plannedMudType ?? referenceRow.plannedMudType),
    },
    fitHighlights: toReferenceFitNarrative(referenceRow, target, criteria),
    caveats: [
      "Matching metrics use MATCHING_WHOLE_SECTIONS scope only; values are not prorated to sub-interval overlap.",
      "Well-wide configuration tuples and event context are aggregated by well ID and are broader than matching-section denominators.",
      "Strict MD overlap controls section eligibility only and does not imply stratigraphic correlation.",
    ],
    missingInfo,
    observedMudWeightRangePpg: mudWeightRange,
    observedMudViscosityRangeSec: mudViscosityRange,
    userRationale: userRationale.trim().length > 0 ? userRationale.trim() : null,
  };
}

function toReferenceFitNarrative(
  row: OffsetComparison,
  target: OffsetTarget | null,
  criteria: OffsetCriteria,
): string[] {
  return [
    summarizeFilterScope(criteria),
    summarizeTrajectoryFit(row, target),
    summarizeFormationAndHoleFit(row, target, criteria),
    summarizeMdFit(row, target, criteria),
  ];
}

function summarizeFilterScope(criteria: OffsetCriteria): string {
  return `Filters: formation ${criteria.formationMatch ? "ON" : "OFF"}, hole size ${criteria.holeSizeMatch ? "ON" : "OFF"}, strict MD overlap ${criteria.mdOverlap ? "ON" : "OFF"}, radius ${criteria.radiusFt} ft.`;
}

function summarizeTrajectoryFit(row: OffsetComparison, target: OffsetTarget | null): string {
  if (!target) return "Trajectory fit: target trajectory unavailable.";
  const trajectories = row.matchingSections
    .map((section) => section.trajectoryProfile)
    .filter((value): value is NonNullable<OffsetMatchingSection["trajectoryProfile"]> => value !== null);
  if (trajectories.length === 0) {
    return "Trajectory fit: matching section trajectories unavailable.";
  }
  const targetTrajectory = target.plannedTrajectoryProfile;
  const matchingCount = trajectories.filter((value) => value === targetTrajectory).length;
  if (matchingCount === trajectories.length) {
    return `Trajectory fit: match (${targetTrajectory.replaceAll("_", " ")} across all returned sections).`;
  }
  if (matchingCount === 0) {
    return `Trajectory fit: mismatch (target ${targetTrajectory.replaceAll("_", " ")} vs historical ${[...new Set(trajectories)].join(", ").replaceAll("_", " ")}).`;
  }
  return `Trajectory fit: mixed (${matchingCount} of ${trajectories.length} sections match target ${targetTrajectory.replaceAll("_", " ")}).`;
}

function summarizeFormationAndHoleFit(
  row: OffsetComparison,
  target: OffsetTarget | null,
  criteria: OffsetCriteria,
): string {
  const sectionCount = row.matchingSections.length;
  if (sectionCount === 0) {
    return "Formation/hole fit: no matching sections were returned, so canonical alignment counts are unavailable.";
  }
  if (!target) {
    return "Formation/hole fit: target formation/hole intent unavailable.";
  }

  const targetFormation = canonicalFormationName(target.expectedFormationName);
  const targetHoleSize = canonicalHoleSize(target.plannedHoleSizeIn);
  const formationMatches = targetFormation === null
    ? null
    : row.matchingSections.filter((section) => canonicalFormationName(section.formationName) === targetFormation).length;
  const holeMatches = targetHoleSize === null
    ? null
    : row.matchingSections.filter((section) => canonicalHoleSize(section.holeSizeIn) === targetHoleSize).length;

  const formationText = formationMatches === null
    ? "target canonical formation unavailable"
    : `${formationMatches}/${sectionCount} sections match target canonical formation`;
  const holeText = holeMatches === null
    ? "target hole size unavailable"
    : `${holeMatches}/${sectionCount} sections match target hole size`;
  const formationFilterStatus = criteria.formationMatch ? "ON" : "OFF";
  const holeFilterStatus = criteria.holeSizeMatch ? "ON" : "OFF";
  const filterCaveat = (!criteria.formationMatch || !criteria.holeSizeMatch)
    ? " Filters that are OFF did not constrain section eligibility, so these counts are descriptive only."
    : "";

  return `Formation/hole fit: formation filter ${formationFilterStatus}; ${formationText}. Hole-size filter ${holeFilterStatus}; ${holeText}.${filterCaveat}`;
}

function canonicalFormationName(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = value.trim().replace(/\s+/g, " ").toLowerCase();
  return normalized.length > 0 ? normalized : null;
}

function canonicalHoleSize(value: string | number | null | undefined): string | null {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    return String(value);
  }
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!/^[+-]?\d+(?:\.\d+)?$/.test(trimmed)) return null;
  const numeric = Number(trimmed);
  if (!Number.isFinite(numeric)) return null;
  return String(numeric);
}

function summarizeMdFit(
  row: OffsetComparison,
  target: OffsetTarget | null,
  criteria: OffsetCriteria,
): string {
  if (!target) return "MD fit: target planned interval unavailable.";
  const plannedStart = toNumber(target.plannedMdMinFt);
  const plannedEnd = toNumber(target.plannedMdMaxFt);
  if (plannedStart === null || plannedEnd === null || plannedStart >= plannedEnd) {
    return "MD fit: target planned MD interval is unavailable or invalid.";
  }
  const overlapChecks = row.matchingSections
    .map((section) => {
      const start = toNumber(section.startMdFt);
      const end = toNumber(section.endMdFt);
      if (start === null || end === null || start >= end) return null;
      return Math.max(start, plannedStart) < Math.min(end, plannedEnd);
    })
    .filter((value): value is boolean => value !== null);

  if (overlapChecks.length === 0) {
    return "MD fit: matching section MD intervals are unavailable for overlap checks.";
  }
  const overlapCount = overlapChecks.filter(Boolean).length;
  if (criteria.mdOverlap) {
    return "MD fit: strict planned MD overlap filter is ON; returned rows passed that eligibility test, but each row still represents a whole historical section.";
  }
  if (overlapCount === 0) {
    return "MD fit: strict planned MD overlap filter is OFF and no returned section showed numeric overlap with the planned interval.";
  }
  if (overlapCount === overlapChecks.length) {
    return "MD fit: strict planned MD overlap filter is OFF; all returned sections happen to overlap the planned interval numerically.";
  }
  return `MD fit: strict planned MD overlap filter is OFF; overlap is mixed (${overlapCount}/${overlapChecks.length} sections overlap planned interval).`;
}

function toObservedRange(values: Array<string | number | null | undefined>): string | null {
  const parsed = values
    .map((value) => toNumber(value))
    .filter((value): value is number => value !== null)
    .sort((left, right) => left - right);
  if (parsed.length === 0) return null;
  const min = parsed[0];
  const max = parsed[parsed.length - 1];
  if (min === undefined || max === undefined) return null;
  if (min === max) return `${min}`;
  return `${min}–${max}`;
}

function toNumber(value: string | number | null | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function toBlockingLoadMessage(phase: "targets" | "candidates" | "compare"): string {
  if (phase === "targets") {
    return "Loading planned targets before candidate analysis can begin.";
  }
  if (phase === "candidates") {
    return "Loading candidate wells for the current target and filter criteria.";
  }
  return "Building selected well comparison results.";
}
