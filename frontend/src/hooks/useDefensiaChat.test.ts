import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useDefensiaChat } from "./useDefensiaChat";

function sseStream(events: Array<{ event: string; data: string }>): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const ev of events) {
        controller.enqueue(encoder.encode(`event: ${ev.event}\ndata: ${ev.data}\n\n`));
      }
      controller.close();
    },
  });
}

const originalFetch = global.fetch;

beforeEach(() => {
  localStorage.setItem("access_token", "fake-jwt");
});

afterEach(() => {
  global.fetch = originalFetch;
  localStorage.clear();
});

describe("useDefensiaChat", () => {
  it("send() agrega mensaje usuario + POST SSE /defensia/chat", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([
        { event: "content_chunk", data: '"Hola"' },
        { event: "done", data: "{}" },
      ]),
    });

    const { result } = renderHook(() => useDefensiaChat("exp-1"));
    await act(async () => {
      await result.current.send("¿Qué puedo alegar?");
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/defensia/chat"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.current.messages[0]?.role).toBe("user");
    expect(result.current.messages[0]?.content).toBe("¿Qué puedo alegar?");
  });

  it("acumula chunks en el último mensaje del asistente", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([
        { event: "content_chunk", data: '"Según"' },
        { event: "content_chunk", data: '" el art. 102"' },
        { event: "done", data: "{}" },
      ]),
    });

    const { result } = renderHook(() => useDefensiaChat("exp-1"));
    await act(async () => {
      await result.current.send("hola");
    });

    await waitFor(() => {
      const last = result.current.messages[result.current.messages.length - 1];
      expect(last.role).toBe("assistant");
      expect(last.content).toContain("Según");
      expect(last.content).toContain("art. 102");
    });
  });

  it("done cierra el stream y setea streaming=false", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([{ event: "done", data: "{}" }]),
    });

    const { result } = renderHook(() => useDefensiaChat("exp-1"));
    await act(async () => {
      await result.current.send("hola");
    });
    expect(result.current.streaming).toBe(false);
  });

  it("error guardrail (400) setea error state", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Guardrail bloqueado" }),
    });

    const { result } = renderHook(() => useDefensiaChat("exp-1"));
    await act(async () => {
      await result.current.send("prompt injection attempt");
    });
    expect(result.current.error).toMatch(/guardrail/i);
  });
});
