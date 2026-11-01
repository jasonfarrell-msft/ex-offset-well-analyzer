import { render, screen } from "@testing-library/react";
import { ResponseDetails } from "./ResponseDetails";

describe("ResponseDetails", () => {
  it("renders nullable API metadata without crashing", () => {
    render(
      <ResponseDetails
        toolCalls={[
          {
            id: "list-1",
            type: "mcp_list_tools",
            name: null,
            server: "fabric-dataagent-mi-bridge",
            status: null,
            toolCount: null,
          },
        ]}
        sources={[]}
        usage={{
          inputTokens: null,
          outputTokens: 42,
          totalTokens: null,
        }}
        latencyMs={1234}
      />,
    );

    expect(screen.getByText("Mcp_list_tools")).toBeInTheDocument();
    expect(screen.getByText("fabric-dataagent-mi-bridge")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
