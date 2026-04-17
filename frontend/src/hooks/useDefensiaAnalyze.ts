import { useCallback, useRef, useState } from "react";
import { createParser, type EventSourceMessage } from "eventsource-parser";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface AnalyzeCallbacks {
  onPhase?: (data: { fase: string; confianza?: number }) => void;
  onCandidatos?: (data: { count: number }) => void;
  onVerificando?: (data: { regla_id: string }) => void;
  onDictamen?: (data: { id: string }) => void;
  onEscrito?: (data: { id: string }) => void;
  onDone?: () => void;
}

export function useDefensiaAnalyze() {
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const analyze = useCallback(async (expedienteId: string, cbs: AnalyzeCallbacks) => {
    setError(null);
    setAnalyzing(true);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${API_URL}/defensia/expedientes/${expedienteId}/analyze`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          signal: controller.signal,
        },
      );

      if (!res.ok) {
        let detail = `Error HTTP ${res.status}`;
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch {
          // ignore
        }
        setError(detail);
        setAnalyzing(false);
        return;
      }

      if (!res.body) {
        setError("Respuesta vacía del servidor");
        setAnalyzing(false);
        return;
      }

      const parser = createParser({
        onEvent(ev: EventSourceMessage) {
          const type = ev.event || "message";
          let data: Record<string, unknown> = {};
          try {
            data = JSON.parse(ev.data);
          } catch {
            data = {};
          }
          switch (type) {
            case "phase_detected":
              cbs.onPhase?.(data as { fase: string });
              break;
            case "candidatos_generados":
              cbs.onCandidatos?.(data as { count: number });
              break;
            case "verificando":
              cbs.onVerificando?.(data as { regla_id: string });
              break;
            case "dictamen_listo":
              cbs.onDictamen?.(data as { id: string });
              break;
            case "escrito_listo":
              cbs.onEscrito?.(data as { id: string });
              break;
            case "done":
              cbs.onDone?.();
              break;
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
      setAnalyzing(false);
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setAnalyzing(false);
  }, []);

  return { analyze, analyzing, error, cancel };
}
