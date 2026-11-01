export const SYNTHETIC_DISCLOSURE =
  "SYNTHETIC DATA • DEVELOPMENT / HISTORICAL SUMMARY ONLY";

const LEGACY_HISTORICAL_DISCLOSURE =
  "SYNTHETIC DATA • v1.0.0 • DEVELOPMENT / HISTORICAL SUMMARY ONLY";
const OFFSET_DISCLOSURE =
  "SYNTHETIC DATA • DEVELOPMENT / OFFSET COMPARISON ONLY";
const OFFSET_DISCLOSURE_V1 =
  "SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY";
const OFFSET_DISCLOSURE_V2 =
  "SYNTHETIC DATA • v1.2.0 • DEVELOPMENT / OFFSET COMPARISON ONLY";

const RECOGNIZED_DISCLOSURES = new Set<string>([
  SYNTHETIC_DISCLOSURE,
  LEGACY_HISTORICAL_DISCLOSURE,
  OFFSET_DISCLOSURE,
  OFFSET_DISCLOSURE_V1,
  OFFSET_DISCLOSURE_V2,
]);

function resolveDisclosureLine(markdown: string): string | null {
  const [firstLine = ""] = markdown.split(/\r?\n/u, 1);
  if (RECOGNIZED_DISCLOSURES.has(firstLine)) {
    return firstLine;
  }

  return null;
}

export function extractDisclosure(markdown: string): {
  disclosure: string | null;
  body: string;
} {
  const disclosure = resolveDisclosureLine(markdown);
  if (!disclosure) {
    return { disclosure: null, body: markdown };
  }

  const isOnlyDisclosure = markdown === disclosure;
  const newlineLength = markdown.startsWith(`${disclosure}\r\n`)
    ? 2
    : markdown.startsWith(`${disclosure}\n`)
      ? 1
      : 0;
  return {
    disclosure,
    body: isOnlyDisclosure
      ? ""
      : markdown
          .slice(disclosure.length + newlineLength)
          .replace(/^(?:\r?\n)/, ""),
  };
}
