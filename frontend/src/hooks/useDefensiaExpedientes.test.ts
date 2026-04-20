import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useDefensiaExpedientes } from "./useDefensiaExpedientes";

const apiRequestMock = vi.fn();

vi.mock("./useApi", () => ({
  useApi: () => ({ apiRequest: apiRequestMock }),
}));

describe("useDefensiaExpedientes", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
  });

  it("carga expedientes y devuelve loading=false tras fetch", async () => {
    apiRequestMock.mockResolvedValueOnce({
      expedientes: [
        { id: "e1", titulo: "IRPF 2023" },
        { id: "e2", titulo: "IVA Q3" },
      ],
    });
    const { result } = renderHook(() => useDefensiaExpedientes());
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.expedientes).toHaveLength(2);
    expect(result.current.error).toBeNull();
  });

  it("propaga el error en error state", async () => {
    apiRequestMock.mockRejectedValueOnce(new Error("Error 500"));
    const { result } = renderHook(() => useDefensiaExpedientes());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatch(/error/i);
    expect(result.current.expedientes).toEqual([]);
  });

  it("refetch dispara una nueva llamada al endpoint", async () => {
    apiRequestMock.mockResolvedValue({ expedientes: [] });
    const { result } = renderHook(() => useDefensiaExpedientes());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiRequestMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      await result.current.refetch();
    });
    expect(apiRequestMock).toHaveBeenCalledTimes(2);
  });

  it("llama al endpoint correcto", async () => {
    apiRequestMock.mockResolvedValue({ expedientes: [] });
    renderHook(() => useDefensiaExpedientes());
    await waitFor(() =>
      expect(apiRequestMock).toHaveBeenCalledWith("/api/defensia/expedientes"),
    );
  });
});
