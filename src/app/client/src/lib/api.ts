import type {
  ChatApi,
  ChatRequest,
  ChatResponse,
  OffsetApi,
  OffsetCandidatesResponse,
  OffsetCompareResponse,
  OffsetContext,
  OffsetFailure,
  OffsetRequest,
  OffsetTarget,
  OffsetTargetsResponse,
} from "../types";

const OFFSET_CONTRACT_VERSION = "offset-well-analysis-v2";
const OFFSET_RELEASE_ID =
  "v1.2.0:6370024a3cdec3e3a4fdb3e9525bfe54d88d92375af7a74836461520e5617ab0";

export class ChatApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly retryable = true,
  ) {
    super(message);
    this.name = "ChatApiError";
  }
}

export function createChatApi(fetcher: typeof fetch = fetch): ChatApi {
  return {
    async send(request: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
      const response = await sendChatRequest(fetcher, request, signal);

      if (!response.ok) {
        throw await toApiError(response);
      }

      const body: unknown = await response.json();
      if (!isChatResponse(body)) {
        throw new ChatApiError(
          "The service returned an unexpected response. Please try again.",
          response.status,
        );
      }
      return body;
    },
  };
}

export function createOffsetApi(fetcher: typeof fetch = fetch): OffsetApi {
  return {
    async targets(signal?: AbortSignal): Promise<OffsetTargetsResponse> {
      return sendOffset(fetcher, {
        operation: "targets",
        contractVersion: OFFSET_CONTRACT_VERSION,
        releaseId: OFFSET_RELEASE_ID,
      }, signal);
    },

    async candidates(
      context: OffsetContext,
      signal?: AbortSignal,
    ): Promise<OffsetCandidatesResponse> {
      return sendOffset(fetcher, {
        operation: "candidates",
        contractVersion: OFFSET_CONTRACT_VERSION,
        releaseId: OFFSET_RELEASE_ID,
        context,
      }, signal);
    },

    async compare(
      context: OffsetContext,
      signal?: AbortSignal,
    ): Promise<OffsetCompareResponse> {
      return sendOffset(fetcher, {
        operation: "compare",
        contractVersion: OFFSET_CONTRACT_VERSION,
        releaseId: OFFSET_RELEASE_ID,
        context,
      }, signal);
    },
  };
}

function sendChatRequest(
  fetcher: typeof fetch,
  request: ChatRequest,
  signal?: AbortSignal,
): Promise<Response> {
  return fetcher("/api/chat", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    ...(signal ? { signal } : {}),
  });
}

async function sendOffset<T extends OffsetTargetsResponse | OffsetCandidatesResponse | OffsetCompareResponse>(
  fetcher: typeof fetch,
  request: OffsetRequest,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetcher("/api/offset-analysis", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    ...(signal ? { signal } : {}),
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  const body: unknown = await response.json();
  if (!isOffsetResponse(body, request.operation)) {
    throw new ChatApiError(
      "The offset analysis service returned an unexpected response.",
      response.status,
    );
  }

  return body as T;
}

async function toApiError(response: Response): Promise<ChatApiError> {
  let serverMessage = "";
  try {
    const body = (await response.json()) as {
      message?: unknown;
      detail?: unknown;
      error?: { code?: unknown };
    };
    const value = body.message ?? body.detail;
    if (typeof value === "string") serverMessage = value;
    else if (typeof body.error?.code === "string") serverMessage = body.error.code;
  } catch {
    // The status-specific fallback below is deliberately user-safe.
  }

  if (response.status === 401) {
    return new ChatApiError(
      serverMessage || "The public endpoint rejected the request.",
      401,
      false,
    );
  }
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    const retrySuffix = retryAfter ? ` Retry after ${retryAfter} seconds.` : "";
    return new ChatApiError(
      serverMessage ||
        `The analysis service is receiving heavy traffic.${retrySuffix}`,
      429,
    );
  }
  if (response.status >= 500) {
    return new ChatApiError(
      serverMessage ||
        "The analysis service is temporarily unavailable. Please retry.",
      response.status,
    );
  }
  return new ChatApiError(
    serverMessage || "The request could not be completed.",
    response.status,
    response.status >= 408,
  );
}

function isChatResponse(value: unknown): value is ChatResponse {
  if (!value || typeof value !== "object") return false;
  const response = value as Partial<ChatResponse>;
  return (
    typeof response.conversationId === "string" &&
    !!response.message &&
    response.message.role === "assistant" &&
    typeof response.message.id === "string" &&
    typeof response.message.markdown === "string" &&
    typeof response.message.createdAtUtc === "string" &&
    Array.isArray(response.visuals) &&
    Array.isArray(response.toolCalls) &&
    Array.isArray(response.sources)
  );
}

function isOffsetResponse(
  value: unknown,
  expectedOperation: "targets" | "candidates" | "compare",
): value is
  | OffsetTargetsResponse
  | OffsetCandidatesResponse
  | OffsetCompareResponse {
  if (!value || typeof value !== "object") return false;

  const response = value as {
    operation?: unknown;
    status?: unknown;
    rows?: unknown;
    error?: unknown;
  };

  if (!isOffsetBase(value)) return false;

  if (
    response.status === "unavailable" ||
    response.status === "stale" ||
    response.status === "error"
  ) {
    return isOffsetFailure(value, expectedOperation);
  }

  if (
    response.operation !== expectedOperation ||
    (response.status !== "success" && response.status !== "empty")
  ) {
    return false;
  }

  if (!Array.isArray(response.rows)) return false;

  if (expectedOperation === "targets") {
    return response.rows.every(isOffsetTarget);
  }

  return true;
}

function isOffsetBase(value: unknown): boolean {
  const body = value as {
    contractVersion?: unknown;
    queryContractVersion?: unknown;
    transformationContractVersion?: unknown;
    datasetVersion?: unknown;
    releaseId?: unknown;
    manifestSha256?: unknown;
    operation?: unknown;
  };

  return (
    typeof body.contractVersion === "string" &&
    typeof body.queryContractVersion === "string" &&
    typeof body.transformationContractVersion === "string" &&
    typeof body.datasetVersion === "string" &&
    typeof body.releaseId === "string" &&
    typeof body.manifestSha256 === "string" &&
    (body.operation === "targets" ||
      body.operation === "candidates" ||
      body.operation === "compare" ||
      body.operation === "chat" ||
      body.operation === null)
  );
}

function isOffsetFailure(
  value: unknown,
  expectedOperation: "targets" | "candidates" | "compare",
): value is OffsetFailure {
  const body = value as OffsetFailure;

  if (
    body.operation !== expectedOperation &&
    body.operation !== null
  ) {
    return false;
  }

  return (
    (body.status === "unavailable" ||
      body.status === "stale" ||
      body.status === "error") &&
    body.contextHash === null &&
    body.evidence === null &&
    !!body.error &&
    typeof body.error.code === "string" &&
    typeof body.error.retryable === "boolean"
  );
}

function isOffsetTarget(value: unknown): value is OffsetTarget {
  if (!value || typeof value !== "object") return false;
  const target = value as Partial<OffsetTarget>;
  return (
    typeof target.targetId === "string" &&
    target.recordKind === "PLANNED_TARGET" &&
    typeof target.expectedFormationName === "string" &&
    typeof target.fieldName === "string"
  );
}
