import { useEffect, useRef, useState } from "react";
import { Composer } from "./components/Composer";
import { ConversationView } from "./components/ConversationView";
import { ErrorNotice } from "./components/ErrorNotice";
import { Header } from "./components/Header";
import { HistorySidebar } from "./components/HistorySidebar";
import { ChatApiError, createChatApi } from "./lib/api";
import {
  loadConversations,
  saveConversations,
  titleFromQuestion,
} from "./lib/storage";
import type {
  AssistantMessage,
  ChatApi,
  StoredConversation,
  UserMessage,
} from "./types";

interface ChatAppProps {
  api?: ChatApi;
}

interface FailedRequest {
  message: string;
  localId: string;
  conversationId?: string;
}

interface ErrorState {
  message: string;
  retryable: boolean;
  request?: FailedRequest;
}

export function App() {
  return <ChatApp />;
}

export function ChatApp({ api = createChatApi() }: ChatAppProps) {
  const [conversations, setConversations] =
    useState<StoredConversation[]>(loadConversations);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorState | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const currentConversation =
    conversations.find((conversation) => conversation.localId === currentId) ??
    null;

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  const executeRequest = async (
    message: string,
    localId: string,
    conversationId?: string,
  ) => {
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await api.send(
        {
          message,
          ...(conversationId ? { conversationId } : {}),
        },
        controller.signal,
      );

      const assistantMessage: AssistantMessage = {
        id: response.message.id,
        role: "assistant",
        markdown: response.message.markdown,
        createdAtUtc: response.message.createdAtUtc,
        visuals: response.visuals,
        toolCalls: response.toolCalls,
        sources: response.sources,
        ...(response.usage ? { usage: response.usage } : {}),
        ...(response.latencyMs !== undefined
          ? { latencyMs: response.latencyMs }
          : {}),
      };
      const updatedAtUtc = new Date().toISOString();

      setConversations((previous) =>
        sortConversations(
          previous.map((conversation) =>
            conversation.localId === localId
              ? {
                  ...conversation,
                  conversationId: response.conversationId,
                  messages: [...conversation.messages, assistantMessage],
                  updatedAtUtc,
                }
              : conversation,
          ),
        ),
      );
    } catch (caught) {
      if (controller.signal.aborted) return;
      const apiError =
        caught instanceof ChatApiError
          ? caught
          : new ChatApiError(
              caught instanceof Error
                ? caught.message
                : "The analysis could not be completed.",
            );
      setError({
        message: apiError.message,
        retryable: apiError.retryable,
        request: {
          message,
          localId,
          ...(conversationId ? { conversationId } : {}),
        },
      });
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
    }
  };

  const sendMessage = async (message: string) => {
    const now = new Date().toISOString();
    const localId = currentConversation?.localId ?? createId();
    const conversationId = currentConversation?.conversationId;
    const userMessage: UserMessage = {
      id: createId(),
      role: "user",
      text: message,
      createdAtUtc: now,
    };

    setCurrentId(localId);
    setConversations((previous) => {
      const existing = previous.find(
        (conversation) => conversation.localId === localId,
      );
      if (existing) {
        return sortConversations(
          previous.map((conversation) =>
            conversation.localId === localId
              ? {
                  ...conversation,
                  messages: [...conversation.messages, userMessage],
                  updatedAtUtc: now,
                }
              : conversation,
          ),
        );
      }

      return [
        {
          localId,
          title: titleFromQuestion(message),
          messages: [userMessage],
          createdAtUtc: now,
          updatedAtUtc: now,
        },
        ...previous,
      ];
    });

    await executeRequest(message, localId, conversationId);
  };

  const startNewChat = () => {
    abortRef.current?.abort();
    setCurrentId(null);
    setError(null);
    setDrawerOpen(false);
  };

  const clearCurrent = () => {
    if (!currentId) return;
    abortRef.current?.abort();
    setConversations((previous) =>
      previous.filter((conversation) => conversation.localId !== currentId),
    );
    setCurrentId(null);
    setError(null);
  };

  const deleteConversation = (id: string) => {
    if (id === currentId) {
      abortRef.current?.abort();
      setCurrentId(null);
      setError(null);
    }
    setConversations((previous) =>
      previous.filter((conversation) => conversation.localId !== id),
    );
  };

  const retry = () => {
    if (!error?.request || busy) return;
    const request = error.request;
    void executeRequest(
      request.message,
      request.localId,
      request.conversationId,
    );
  };

  return (
    <div className="app-shell">
      <title>Drill Advisor</title>
      <HistorySidebar
        conversations={conversations}
        currentId={currentId}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onDelete={deleteConversation}
        onNewChat={startNewChat}
        onRename={(id, title) =>
          setConversations((previous) =>
            previous.map((conversation) =>
              conversation.localId === id
                ? { ...conversation, title }
                : conversation,
            ),
          )
        }
        onSelect={(id) => {
          abortRef.current?.abort();
          setCurrentId(id);
          setError(null);
          setDrawerOpen(false);
        }}
      />
      <div className="workspace">
        <Header
          hasConversation={Boolean(currentConversation)}
          onClear={clearCurrent}
          onMenu={() => setDrawerOpen(true)}
          onNewChat={startNewChat}
        />
        <main className="chat-main">
          <ConversationView
            busy={busy}
            messages={currentConversation?.messages ?? []}
            onSuggestion={(suggestion) => void sendMessage(suggestion)}
          />
          {error && (
            <ErrorNotice
              message={error.message}
              retryable={error.retryable && Boolean(error.request)}
              onDismiss={() => setError(null)}
              onRetry={retry}
            />
          )}
          <Composer
            busy={busy}
            onSend={sendMessage}
            onStop={() => abortRef.current?.abort()}
          />
        </main>
      </div>
    </div>
  );
}

function sortConversations(
  conversations: StoredConversation[],
): StoredConversation[] {
  return [...conversations].sort((a, b) =>
    b.updatedAtUtc.localeCompare(a.updatedAtUtc),
  );
}

function createId(): string {
  return globalThis.crypto.randomUUID();
}
