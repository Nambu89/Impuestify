import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDefensiaAnalyze } from "./useDefensiaAnalyze";

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

describe("useDefensiaAnalyze", () => {
  it("dispara POST al endpoint analyze con auth header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([{ event: "done", data: "{}" }]),
    });
    // @ts-expect-error - mocked
    global.fetch = fetchMock;

    const { result } = renderHook(() => useDefensiaAnalyze());
    await act(async () => {
      await result.current.analyze("exp-1", {});
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/defensia/expedientes/exp-1/analyze"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer fake-jwt",
        }),
      }),
    );
  });

  it("propaga eventos phase_detected y dictamen_listo a los callbacks", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([
        { event: "phase_detected", data: '{"fase":"COMPROBACION_PROPUESTA"}' },
        { event: "candidatos_generados", data: '{"count":5}' },
        { event: "dictamen_listo", data: '{"id":"dic-1"}' },
        { event: "done", data: "{}" },
      ]),
    });

    const onPhase = vi.fn();
    const onCandidatos = vi.fn();
    const onDictamen = vi.fn();
    const onDone = vi.fn();

    const { result } = renderHook(() => useDefensiaAnalyze());
    await act(async () => {
      await result.current.analyze("exp-1", {
        onPhase,
        onCandidatos,
        onDictamen,
        onDone,
      });
    });

    expect(onPhase).toHaveBeenCalledWith(
      expect.objectContaining({ fase: "COMPROBACION_PROPUESTA" }),
    );
    expect(onCandidatos).toHaveBeenCalledWith(expect.objectContaining({ count: 5 }));
    expect(onDictamen).toHaveBeenCalledWith(expect.objectContaining({ id: "dic-1" }));
    expect(onDone).toHaveBeenCalled();
  });

  it("setea error si el backend devuelve 400 (brief vacío)", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Brief vacío" }),
    });

    const { result } = renderHook(() => useDefensiaAnalyze());
    await act(async () => {
      await result.current.analyze("exp-1", {});
    });

    expect(result.current.error).toMatch(/brief/i);
  });

  it("resetea analyzing a false tras finalizar", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: sseStream([{ event: "done", data: "{}" }]),
    });

    const { result } = renderHook(() => useDefensiaAnalyze());
    await act(async () => {
      await result.current.analyze("exp-1", {});
    });

    expect(result.current.analyzing).toBe(false);
  });
});
