import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatApp } from "./App";
import { ChatApiError } from "./lib/api";
import type { ChatApi, ChatRequest, ChatResponse } from "./types";

function response(
  conversationId = "server-conversation-1",
  id = "assistant-1",
): ChatResponse {
  return {
    conversationId,
    message: {
      id,
      role: "assistant",
      markdown: "Analysis complete.",
      createdAtUtc: "2026-10-26T18:00:00Z",
    },
    visuals: [],
    toolCalls: [],
    sources: [],
    latencyMs: 125,
  };
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("ChatApp", () => {
  it("shows only prepared prompts validated against the public summary model", () => {
    render(<ChatApp api={{ send: vi.fn() }} />);

    expect(
      screen.getByRole("button", {
        name: /Summarize all 100 synthetic wells/,
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", {
        name: /Compare accepted and quarantined run counts/,
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", {
        name: /Show the top 10 wells by total accepted footage/,
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", {
        name: /Summarize all data-quality issues/,
      }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", {
        name: /8½-inch sections/,
      }),
    ).not.toBeInTheDocument();
  });

  it("announces an industrial busy state while awaiting a response", async () => {
    const api: ChatApi = {
      send: vi.fn(
        () =>
          new Promise<ChatResponse>(() => {
            // Deliberately pending for this assertion.
          }),
      ),
    };
    const user = userEvent.setup();
    render(<ChatApp api={api} />);

    await user.type(
      screen.getByRole("textbox", { name: "Ask about drill-run history" }),
      "Compare recent runs",
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByRole("status", {
        name: "Analyzing drill-run history",
      }),
    ).toHaveTextContent("Analyzing drill-run history…");
    expect(screen.getByRole("button", { name: "Stop analysis" })).toBeVisible();
  });

  it("shows a retryable error and retries the same request", async () => {
    const send = vi
      .fn()
      .mockRejectedValueOnce(
        new ChatApiError("Service is temporarily unavailable.", 503),
      )
      .mockResolvedValueOnce(response());
    const user = userEvent.setup();
    render(<ChatApp api={{ send }} />);

    await user.type(
      screen.getByRole("textbox", { name: "Ask about drill-run history" }),
      "Summarize NPT",
    );
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Service is temporarily unavailable.",
    );
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Analysis complete.")).toBeVisible();
    expect(send).toHaveBeenCalledTimes(2);
    expect(send).toHaveBeenLastCalledWith(
      { message: "Summarize NPT" },
      expect.any(AbortSignal),
    );
  });

  it("reuses the backend conversation ID for the next turn", async () => {
    const requests: ChatRequest[] = [];
    const api: ChatApi = {
      send: vi.fn(async (request) => {
        requests.push(request);
        return response(
          "server-conversation-42",
          `assistant-${requests.length.toString()}`,
        );
      }),
    };
    const user = userEvent.setup();
    render(<ChatApp api={api} />);
    const input = screen.getByRole("textbox", {
      name: "Ask about drill-run history",
    });

    await user.type(input, "Compare ROP");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Analysis complete.");

    await user.type(input, "Break that down by formation");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(requests).toHaveLength(2));

    expect(requests).toEqual([
      { message: "Compare ROP" },
      {
        message: "Break that down by formation",
        conversationId: "server-conversation-42",
      },
    ]);
  });
});
