import type {
  BarChartVisual,
  DataTableVisual,
  KpiGridVisual,
  ScalarValue,
  VisualBlock,
} from "../types";

interface VisualsProps {
  visuals: VisualBlock[];
}

export function Visuals({ visuals }: VisualsProps) {
  if (visuals.length === 0) return null;

  return (
    <div className="visual-stack" aria-label="Analysis visuals">
      {visuals.map((visual, index) => (
        <Visual
          key={visual.id ?? `${visual.type}-${index.toString()}`}
          visual={visual}
        />
      ))}
    </div>
  );
}

function Visual({ visual }: { visual: VisualBlock }) {
  switch (visual.type) {
    case "kpi-grid":
      return <KpiGrid visual={visual} />;
    case "bar-chart":
      return <BarChart visual={visual} />;
    case "data-table":
      return <DataTable visual={visual} />;
  }
}

function VisualHeader({
  title,
  description,
}: {
  title?: string;
  description?: string;
}) {
  if (!title && !description) return null;
  return (
    <header className="visual-header">
      {title && <h3>{title}</h3>}
      {description && <p>{description}</p>}
    </header>
  );
}

function KpiGrid({ visual }: { visual: KpiGridVisual }) {
  return (
    <section className="visual-card" aria-label={visual.title ?? "Key metrics"}>
      <VisualHeader
        {...(visual.title ? { title: visual.title } : {})}
        {...(visual.description ? { description: visual.description } : {})}
      />
      <dl className="kpi-grid">
        {visual.items.map((item, index) => (
          <div className="kpi" key={item.id ?? `${item.label}-${index.toString()}`}>
            <dt>{item.label}</dt>
            <dd>
              <span>{displayValue(item.value)}</span>
              {item.unit && <small>{item.unit}</small>}
            </dd>
            {item.context && <p>{item.context}</p>}
          </div>
        ))}
      </dl>
    </section>
  );
}

function BarChart({ visual }: { visual: BarChartVisual }) {
  const maxMagnitude = Math.max(
    ...visual.data.map((item) => Math.abs(item.value)),
    0,
  );

  return (
    <section
      className="visual-card"
      aria-label={visual.title ?? "Bar chart"}
    >
      <VisualHeader
        {...(visual.title ? { title: visual.title } : {})}
        {...(visual.description ? { description: visual.description } : {})}
      />
      <div className="bar-chart" role="img" aria-label={barChartLabel(visual)}>
        {visual.data.map((item, index) => {
          const width =
            maxMagnitude === 0 ? 0 : (Math.abs(item.value) / maxMagnitude) * 100;
          const unit = item.unit ?? visual.unit;
          return (
            <div
              className="bar-chart__row"
              key={item.id ?? `${item.label}-${index.toString()}`}
            >
              <span className="bar-chart__label">{item.label}</span>
              <div className="bar-chart__track" aria-hidden="true">
                <span
                  className={`bar-chart__fill${item.value < 0 ? " bar-chart__fill--negative" : ""}`}
                  style={{ width: `${width.toString()}%` }}
                />
              </div>
              <strong className="bar-chart__value">
                {displayValue(item.value)}
                {unit && <small> {unit}</small>}
              </strong>
            </div>
          );
        })}
      </div>
      <details className="chart-data">
        <summary>View chart as table</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col">Value</th>
              <th scope="col">Unit</th>
            </tr>
          </thead>
          <tbody>
            {visual.data.map((item, index) => (
              <tr key={item.id ?? `${item.label}-table-${index.toString()}`}>
                <th scope="row">{item.label}</th>
                <td>{displayValue(item.value)}</td>
                <td>{item.unit ?? visual.unit ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

function DataTable({ visual }: { visual: DataTableVisual }) {
  return (
    <section
      className="visual-card"
      aria-label={visual.title ?? "Analysis data table"}
    >
      <VisualHeader
        {...(visual.title ? { title: visual.title } : {})}
        {...(visual.description ? { description: visual.description } : {})}
      />
      <div className="data-table-scroll" tabIndex={0}>
        <table className="data-table">
          <caption>{visual.caption ?? visual.title ?? "Analysis data"}</caption>
          <thead>
            <tr>
              {visual.columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  style={{ textAlign: column.align ?? "left" }}
                >
                  {column.label}
                  {column.unit && (
                    <span className="column-unit"> ({column.unit})</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visual.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {visual.columns.map((column, columnIndex) => {
                  const Cell = columnIndex === 0 ? "th" : "td";
                  return (
                    <Cell
                      key={column.key}
                      {...(columnIndex === 0 ? { scope: "row" } : {})}
                      style={{ textAlign: column.align ?? "left" }}
                    >
                      {displayValue(row[column.key] ?? null)}
                    </Cell>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function displayValue(value: ScalarValue): string {
  if (value === null) return "—";
  return String(value);
}

function barChartLabel(visual: BarChartVisual): string {
  const values = visual.data
    .map((item) => {
      const unit = item.unit ?? visual.unit;
      return `${item.label}: ${displayValue(item.value)}${unit ? ` ${unit}` : ""}`;
    })
    .join("; ");
  return `${visual.title ?? "Bar chart"}. ${values}`;
}
