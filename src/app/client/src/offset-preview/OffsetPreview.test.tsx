import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import DevWorkspace from "./DevWorkspace";
import OffsetPreview from "./OffsetPreview";

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  window.localStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function selects() {
  return screen.queryAllByRole("checkbox", { name: /^Select SYN-WELL-/ });
}

describe("offset development workflow", () => {
  it("starts unselected with twelve planned targets and accessible defaults", () => {
    render(<OffsetPreview />);
    expect(screen.getAllByRole("option")).toHaveLength(12);
    expect(screen.getByRole("spinbutton", { name: /Surface radius/ })).toHaveValue(10000);
    expect(screen.getByRole("checkbox", { name: "Same canonical formation" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Same hole size" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Strict planned MD/ })).not.toBeChecked();
    expect(selects()).toHaveLength(6);
    expect(selects().every((checkbox) => !(checkbox as HTMLInputElement).checked)).toBe(true);
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
    expect(screen.getByText("OFFLINE SYNTHETIC PREVIEW")).toBeVisible();
    expect(screen.getByText(/Dataset v1.1.0 · not connected to Fabric/)).toBeVisible();
    expect(screen.getByText(/Fictional surface proximity is not subsurface/)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live offset chat is unavailable" })).toBeVisible();
  });

  it("requires explicit comparison, limits selection to five, and clears comparison on any selection change", async () => {
    const user = userEvent.setup();
    render(<OffsetPreview />);
    for (const checkbox of selects().slice(0, 5)) await user.click(checkbox);
    expect(selects()[5]).toBeDisabled();
    expect(screen.getByText(/Limit reached/)).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Compare selected (5)" }));
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(6);
    expect(within(table).getByRole("rowheader", { name: "Historical summary (ft/hour)" })).toBeVisible();
    expect(within(table).getByRole("rowheader", { name: "Quarantined runs (excluded)" })).toBeVisible();
    await user.click(selects()[0]!);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(selects()[5]).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Clear selection" }));
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
  });

  it.each(["target", "radius", "formation", "hole", "md"] as const)("invalidates stale selection and comparison when %s changes", async (control) => {
    const user = userEvent.setup();
    render(<OffsetPreview />);
    await user.click(selects()[0]!);
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    expect(screen.getByRole("table")).toBeVisible();
    if (control === "target") await user.selectOptions(screen.getByLabelText("Planned target"), "SYN-TARGET-0002");
    if (control === "radius") fireEvent.change(screen.getByLabelText("Surface radius (ft)"), { target: { value: "5000" } });
    if (control === "formation") await user.click(screen.getByLabelText("Same canonical formation"));
    if (control === "hole") await user.click(screen.getByLabelText("Same hole size"));
    if (control === "md") await user.click(screen.getByLabelText("Strict planned MD overlap (optional)"));
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
    expect(selects().every((checkbox) => !(checkbox as HTMLInputElement).checked)).toBe(true);
  });

  it("shows meaningful empty/invalid states without widening and restores defaults explicitly", async () => {
    const user = userEvent.setup();
    render(<OffsetPreview />);
    const radius = screen.getByLabelText("Surface radius (ft)");
    fireEvent.change(radius, { target: { value: "0" } });
    expect(screen.getByText("No matching historical wells")).toBeVisible();
    expect(radius).toHaveValue(0);
    expect(selects()).toHaveLength(0);
    fireEvent.change(radius, { target: { value: "3000001" } });
    expect(radius).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Set a valid radius to explore")).toBeVisible();
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(radius).toHaveValue(10000);
    expect(selects()).toHaveLength(6);
  });

  it("paginates a complete wide candidate set while retaining explicit selections across pages", async () => {
    const user = userEvent.setup();
    render(<OffsetPreview />);
    fireEvent.change(screen.getByLabelText("Surface radius (ft)"), { target: { value: "3000000" } });
    await user.click(screen.getByLabelText("Same canonical formation"));
    await user.click(screen.getByLabelText("Same hole size"));
    expect(selects()).toHaveLength(25);
    expect(screen.getByText("100 eligible")).toBeVisible();
    const first = selects()[0]!;
    const firstLabel = first.getAttribute("aria-label")!;
    await user.click(first);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText(/Page 2 of 4/)).toBeVisible();
    await user.click(selects()[0]!);
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getByRole("checkbox", { name: firstLabel })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Compare selected (2)" }));
    expect(within(screen.getByRole("table")).getAllByRole("columnheader")).toHaveLength(3);
  });

  it("supports the direct local URL, browser navigation and isolated state with no HTTP or chat-context writes", async () => {
    const fetch = vi.fn(() => { throw new Error("Preview must not call HTTP"); });
    vi.stubGlobal("fetch", fetch);
    const xhr = vi.fn();
    vi.stubGlobal("XMLHttpRequest", xhr);
    window.localStorage.setItem("existing-chat-context", "preserve");
    const readContext = vi.spyOn(window.localStorage, "getItem");
    const writeContext = vi.spyOn(window.localStorage, "setItem");
    window.history.replaceState(null, "", "/?view=offset-preview");
    const user = userEvent.setup();
    render(<DevWorkspace />);
    await screen.findByRole("heading", { name: "Offset well analysis" });
    await user.selectOptions(screen.getByLabelText("Planned target"), "SYN-TARGET-0003");
    await user.click(selects()[0]!);
    await user.click(screen.getByRole("button", { name: "Compare selected (1)" }));
    await user.click(screen.getByLabelText("Same hole size"));
    await user.click(screen.getByLabelText("Same canonical formation"));
    await user.click(screen.getByLabelText("Strict planned MD overlap (optional)"));
    fireEvent.change(screen.getByLabelText("Surface radius (ft)"), { target: { value: "0" } });
    await user.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(fetch).not.toHaveBeenCalled();
    expect(xhr).not.toHaveBeenCalled();
    expect(readContext).not.toHaveBeenCalled();
    expect(writeContext).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Historical chat" }));
    expect(window.location.search).toBe("");
    expect(screen.queryByRole("heading", { name: "Offset well analysis" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Offset well preview" }));
    expect(window.location.search).toBe("?view=offset-preview");
    expect(screen.getByRole("button", { name: "Compare selected (0)" })).toBeDisabled();
    window.history.replaceState(null, "", "/");
    fireEvent.popState(window);
    expect(screen.queryByRole("heading", { name: "Offset well analysis" })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("leaves historical chat as the default development view", () => {
    render(<DevWorkspace />);
    expect(screen.getByRole("button", { name: "Historical chat" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("heading", { name: "Offset well analysis" })).not.toBeInTheDocument();
  });
});
