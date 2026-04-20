import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useDefensiaExpediente } from "./useDefensiaExpediente";

const apiRequestMock = vi.fn();

vi.mock("./useApi", () => ({
  useApi: () => ({ apiRequest: apiRequestMock }),
}));

describe("useDefensiaExpediente", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
  });

  it("llama al endpoint con el id y devuelve el expediente", async () => {
    apiRequestMock.mockResolvedValueOnce({
      id: "exp-1",
      titulo: "IRPF 2023",
      argumentos: [],
    });
    const { result } = renderHook(() => useDefensiaExpediente("exp-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiRequestMock).toHaveBeenCalledWith("/api/defensia/expedientes/exp-1");
    expect(result.current.expediente?.id).toBe("exp-1");
  });

  it("mutate() refresca el expediente", async () => {
    apiRequestMock.mockResolvedValue({ id: "exp-1", titulo: "IRPF 2023" });
    const { result } = renderHook(() => useDefensiaExpediente("exp-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiRequestMock).toHaveBeenCalledTimes(1);
    await act(async () => {
      await result.current.mutate();
    });
    expect(apiRequestMock).toHaveBeenCalledTimes(2);
  });

  it("no llama al endpoint si el id es null", async () => {
    const { result } = renderHook(() => useDefensiaExpediente(null));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiRequestMock).not.toHaveBeenCalled();
  });
});
