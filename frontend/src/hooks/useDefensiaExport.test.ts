import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDefensiaExport } from "./useDefensiaExport";

const originalFetch = global.fetch;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevoke = URL.revokeObjectURL;

beforeEach(() => {
  localStorage.setItem("access_token", "fake-jwt");
  URL.createObjectURL = vi.fn(() => "blob:fake");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  URL.createObjectURL = originalCreateObjectURL;
  URL.revokeObjectURL = originalRevoke;
  localStorage.clear();
});

function makeClick() {
  const click = vi.fn();
  const spy = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(click);
  return { click, spy };
}

describe("useDefensiaExport", () => {
  it("exportar('docx') descarga blob", async () => {
    const blob = new Blob(["FAKE_DOCX"], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => blob,
    });
    const { click } = makeClick();

    const { result } = renderHook(() => useDefensiaExport());
    await act(async () => {
      await result.current.exportar("exp-1", "esc-1", "docx", true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("formato=docx"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(click).toHaveBeenCalled();
  });

  it("exportar('pdf') también descarga blob", async () => {
    const blob = new Blob(["FAKE_PDF"], { type: "application/pdf" });
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => blob,
    });
    const { click } = makeClick();

    const { result } = renderHook(() => useDefensiaExport());
    await act(async () => {
      await result.current.exportar("exp-1", "esc-1", "pdf", true);
    });
    expect(click).toHaveBeenCalled();
  });

  it("error 428 (sin disclaimer aceptado) setea needsDisclaimer=true", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 428,
      json: async () => ({ detail: "Disclaimer no aceptado" }),
    });

    const { result } = renderHook(() => useDefensiaExport());
    await act(async () => {
      await result.current.exportar("exp-1", "esc-1", "docx", false);
    });

    expect(result.current.needsDisclaimer).toBe(true);
  });

  it("error 402 (cuota agotada) setea error con mensaje de cuota", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 402,
      json: async () => ({ detail: "Cuota mensual agotada" }),
    });

    const { result } = renderHook(() => useDefensiaExport());
    await act(async () => {
      await result.current.exportar("exp-1", "esc-1", "docx", true);
    });

    expect(result.current.error).toMatch(/cuota/i);
  });
});
