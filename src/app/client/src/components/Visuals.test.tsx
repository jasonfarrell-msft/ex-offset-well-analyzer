import { render, screen, within } from "@testing-library/react";
import { Visuals } from "./Visuals";
import type { VisualBlock } from "../types";

const visuals: VisualBlock[] = [
  {
    type: "kpi-grid",
    title: "Run KPIs",
    items: [{ label: "Average ROP", value: 87.35, unit: "ft/hr" }],
  },
  {
    type: "bar-chart",
    title: "ROP by formation",
    unit: "ft/hr",
    data: [
      { label: "Synthetic Aster", value: 91.125 },
      { label: "Synthetic Ember", value: 74.5 },
    ],
  },
  {
    type: "data-table",
    title: "Run detail",
    columns: [
      { key: "well", label: "Well" },
      { key: "npt", label: "NPT", unit: "hr", align: "right" },
    ],
    rows: [{ well: "ASTER-01", npt: 1.275 }],
  },
];

describe("Visuals", () => {
  it("renders each typed visual with exact numeric values and units", () => {
    render(<Visuals visuals={visuals} />);

    expect(screen.getByText("87.35")).toBeVisible();
    expect(screen.getAllByText("ft/hr").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("img", {
        name: /Synthetic Aster: 91.125 ft\/hr.*Synthetic Ember: 74.5 ft\/hr/,
      }),
    ).toBeVisible();

    const runTable = screen.getByRole("table", { name: "Run detail" });
    expect(within(runTable).getByText("ASTER-01")).toBeVisible();
    expect(within(runTable).getByText("1.275")).toBeVisible();
    expect(within(runTable).getByText("(hr)")).toBeVisible();
  });

  it("provides an HTML table fallback for the bar chart", () => {
    render(<Visuals visuals={[visuals[1]!]} />);
    expect(screen.getByText("View chart as table")).toBeVisible();
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});
