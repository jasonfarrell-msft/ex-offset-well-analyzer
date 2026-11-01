import { render, screen, within } from "@testing-library/react";
import { MarkdownContent } from "./MarkdownContent";
import { SYNTHETIC_DISCLOSURE } from "../lib/disclosure";

describe("MarkdownContent", () => {
  it("renders GFM tables with accessible table semantics", () => {
    render(
      <MarkdownContent
        markdown={`## Run comparison

| Well | ROP |
| --- | ---: |
| Aster-01 | 87.35 |`}
      />,
    );

    const table = screen.getByRole("table");
    expect(screen.getByRole("heading", { name: "Run comparison" })).toBeVisible();
    expect(within(table).getByRole("columnheader", { name: "Well" })).toBeVisible();
    expect(within(table).getByRole("cell", { name: "87.35" })).toBeVisible();
  });

  it("promotes only the exact first-line disclosure to a banner", () => {
    const { rerender } = render(
      <MarkdownContent markdown={`${SYNTHETIC_DISCLOSURE}\n\nAnalysis body.`} />,
    );

    const banner = screen.getByRole("note", { name: "Data disclosure" });
    expect(banner).toHaveTextContent(SYNTHETIC_DISCLOSURE);
    expect(banner).toHaveClass("synthetic-banner");
    expect(screen.getByText("Analysis body.")).toBeVisible();

    rerender(
      <MarkdownContent
        markdown={`Analysis body.\n\n${SYNTHETIC_DISCLOSURE}`}
      />,
    );
    expect(screen.queryByRole("note", { name: "Data disclosure" })).toBeNull();
  });

  it("promotes the legacy versioned historical disclosure for older conversations", () => {
    render(
      <MarkdownContent
        markdown={`SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY

Historical answer.`}
      />,
    );

    const banner = screen.getByRole("note", { name: "Data disclosure" });
    expect(banner).toHaveTextContent(
      "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY",
    );
    expect(screen.getByText("Historical answer.")).toBeVisible();
  });

  it("promotes offset disclosures emitted by chat endpoint context variants", () => {
    const { rerender } = render(
      <MarkdownContent
        markdown={`SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY

Offset answer.`}
      />,
    );

    expect(screen.getByRole("note", { name: "Data disclosure" })).toHaveTextContent(
      "SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY",
    );
    expect(screen.getByText("Offset answer.")).toBeVisible();

    rerender(
      <MarkdownContent
        markdown={`SYNTHETIC DATA • v1.2.0 • DEVELOPMENT / OFFSET COMPARISON ONLY

Versioned offset answer.`}
      />,
    );
    expect(screen.getByRole("note", { name: "Data disclosure" })).toHaveTextContent(
      "SYNTHETIC DATA • v1.2.0 • DEVELOPMENT / OFFSET COMPARISON ONLY",
    );
    expect(screen.getByText("Versioned offset answer.")).toBeVisible();
  });
});
