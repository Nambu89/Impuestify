import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDefensiaUpload } from "./useDefensiaUpload";

// Mock XHR
class MockXhr {
  upload = { onprogress: null as ((e: ProgressEvent) => void) | null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  status = 201;
  responseText = JSON.stringify({ id: "doc-1" });
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();

  _simulateProgress(loaded: number, total: number) {
    this.upload.onprogress?.({
      lengthComputable: true,
      loaded,
      total,
    } as ProgressEvent);
  }
  _simulateLoad() {
    this.onload?.();
  }
}

let mockXhr: MockXhr;
const originalXhr = global.XMLHttpRequest;

beforeEach(() => {
  mockXhr = new MockXhr();
  // @ts-expect-error - mocking XMLHttpRequest constructor
  global.XMLHttpRequest = function () {
    return mockXhr;
  } as unknown as typeof XMLHttpRequest;
  localStorage.setItem("access_token", "fake-jwt");
});

afterEach(() => {
  global.XMLHttpRequest = originalXhr;
  localStorage.clear();
});

describe("useDefensiaUpload", () => {
  it("envia POST con FormData al endpoint documentos del expediente", async () => {
    const { result } = renderHook(() => useDefensiaUpload("exp-1"));
    const file = new File(["hi"], "test.pdf", { type: "application/pdf" });
    const promise = act(async () => {
      const p = result.current.upload(file, "REQUERIMIENTO");
      mockXhr._simulateLoad();
      await p;
    });
    await promise;
    expect(mockXhr.open).toHaveBeenCalledWith(
      "POST",
      expect.stringContaining("/defensia/expedientes/exp-1/documentos"),
    );
    expect(mockXhr.setRequestHeader).toHaveBeenCalledWith(
      "Authorization",
      "Bearer fake-jwt",
    );
    expect(mockXhr.send).toHaveBeenCalled();
  });

  it("reporta progreso via callback onProgress", async () => {
    const { result } = renderHook(() => useDefensiaUpload("exp-1"));
    const file = new File(["hi"], "test.pdf");
    const onProgress = vi.fn();
    await act(async () => {
      const p = result.current.upload(file, "OTROS", onProgress);
      mockXhr._simulateProgress(25, 100);
      mockXhr._simulateProgress(100, 100);
      mockXhr._simulateLoad();
      await p;
    });
    expect(onProgress).toHaveBeenCalledWith(0.25);
    expect(onProgress).toHaveBeenCalledWith(1);
  });

  it("rechaza con FILE_TOO_LARGE si el backend devuelve 413", async () => {
    mockXhr.status = 413;
    mockXhr.responseText = JSON.stringify({ detail: "archivo excede 20MB" });
    const { result } = renderHook(() => useDefensiaUpload("exp-1"));
    const file = new File(["hi"], "big.pdf");
    await expect(
      act(async () => {
        const p = result.current.upload(file, "OTROS");
        mockXhr._simulateLoad();
        await p;
      }),
    ).rejects.toMatchObject({
      code: "FILE_TOO_LARGE",
    });
  });
});
