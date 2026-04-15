import { useCallback, useRef, useState } from "react";
import { createParser, type EventSourceMessage } from "eventsource-parser";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function useDefensiaChat(expedienteId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string) => {
      setError(null);
      setStreaming(true);

      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: "" },
      ]);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const token = localStorage.getItem("access_token");
        const res = await fetch(`${API_URL}/api/defensia/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ expediente_id: expedienteId, message: text }),
          signal: controller.signal,
        });

        if (!res.ok) {
          let detail = `Error HTTP ${res.status}`;
          try {
            const data = await res.json();
            detail = data.detail || detail;
          } catch {
            // ignore
          }
          setError(detail);
          setStreaming(false);
          return;
        }

        if (!res.body) {
          setError("Respuesta vacía del servidor");
          setStreaming(false);
          return;
        }

        const parser = createParser({
          onEvent(ev: EventSourceMessage) {
            const type = ev.event || "message";
            if (type === "content_chunk") {
              // chunk viene como JSON string, parseamos
              let chunk = ev.data;
              try {
                chunk = JSON.parse(ev.data);
              } catch {
                // ya era texto
              }
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last && last.role === "assistant") {
                  copy[copy.length - 1] = {
                    ...last,
                    content: last.content + chunk,
                  };
                }
                return copy;
              });
            }
            if (type === "done") {
              setStreaming(false);
            }
            if (type === "error") {
              setError(ev.data);
              setStreaming(false);
            }
          },
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value, { stream: true }));
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setStreaming(false);
      }
    },
    [expedienteId],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    setStreaming(false);
  }, []);

  return { messages, streaming, error, send, reset };
}
