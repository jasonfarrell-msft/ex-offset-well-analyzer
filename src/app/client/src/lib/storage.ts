import type { StoredConversation } from "../types";

export const HISTORY_STORAGE_KEY = "drill-advisor:conversations:v1";

export function loadConversations(): StoredConversation[] {
  try {
    const stored = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!stored) return [];

    const parsed: unknown = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];

    return parsed.filter(isStoredConversation).sort((a, b) =>
      b.updatedAtUtc.localeCompare(a.updatedAtUtc),
    );
  } catch {
    return [];
  }
}

export function saveConversations(conversations: StoredConversation[]): void {
  try {
    window.localStorage.setItem(
      HISTORY_STORAGE_KEY,
      JSON.stringify(conversations),
    );
  } catch {
    // Storage can be unavailable or full. Chat remains usable in memory.
  }
}

export function titleFromQuestion(question: string): string {
  const normalized = question.replace(/\s+/g, " ").trim();
  if (normalized.length <= 46) return normalized;
  return `${normalized.slice(0, 43).trimEnd()}…`;
}

function isStoredConversation(value: unknown): value is StoredConversation {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<StoredConversation>;
  return (
    typeof candidate.localId === "string" &&
    typeof candidate.title === "string" &&
    Array.isArray(candidate.messages) &&
    typeof candidate.createdAtUtc === "string" &&
    typeof candidate.updatedAtUtc === "string"
  );
}
