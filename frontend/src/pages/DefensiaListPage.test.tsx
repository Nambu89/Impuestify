import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { DefensiaListPage } from "./DefensiaListPage";
import type { Expediente } from "../types/defensia";

const hookState = {
  expedientes: [] as Expediente[],
  loading: false,
  error: null as string | null,
  refetch: vi.fn(),
};

vi.mock("../hooks/useDefensiaExpedientes", () => ({
  useDefensiaExpedientes: () => hookState,
}));

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("../hooks/useSEO", () => ({ useSEO: () => {} }));

const base: Expediente = {
  id: "e1",
  titulo: "IRPF 2023",
  tributo: "IRPF",
  ccaa: "Madrid",
  estado: "en_analisis",
  fase_detectada: "COMPROBACION_REQUERIMIENTO",
  fase_confianza: 0.9,
  num_documentos: 2,
  dias_restantes: 10,
  creado_en: "2026-04-01T00:00:00Z",
  actualizado_en: "2026-04-10T00:00:00Z",
};

describe("DefensiaListPage", () => {
  beforeEach(() => {
    hookState.expedientes = [];
    hookState.loading = false;
    hookState.error = null;
    navigateMock.mockReset();
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <DefensiaListPage />
      </MemoryRouter>,
    );
  }

  it("renderiza 3 cards cuando hay 3 expedientes", () => {
    hookState.expedientes = [
      { ...base, id: "e1", titulo: "IRPF 2023" },
      { ...base, id: "e2", titulo: "IVA Q3" },
      { ...base, id: "e3", titulo: "ISD herencia" },
    ];
    renderPage();
    expect(screen.getByText("IRPF 2023")).toBeInTheDocument();
    expect(screen.getByText("IVA Q3")).toBeInTheDocument();
    expect(screen.getByText("ISD herencia")).toBeInTheDocument();
  });

  it("muestra empty state y botón crear cuando no hay expedientes", () => {
    renderPage();
    expect(screen.getByText(/ningún expediente/i)).toBeInTheDocument();
    // Dos botones "Crear expediente": header + empty state
    expect(
      screen.getAllByRole("button", { name: /crear expediente/i }),
    ).toHaveLength(2);
  });

  it("muestra skeleton en loading", () => {
    hookState.loading = true;
    const { container } = renderPage();
    expect(container.querySelector(".defensia-list-skeleton")).toBeInTheDocument();
  });

  it("muestra error con botón retry", async () => {
    hookState.error = "Error 500";
    renderPage();
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: /reintentar/i });
    await userEvent.click(retry);
    expect(hookState.refetch).toHaveBeenCalled();
  });

  it("click en 'crear expediente' navega a /defensia/nuevo", async () => {
    renderPage();
    const botones = screen.getAllByRole("button", {
      name: /crear expediente/i,
    });
    await userEvent.click(botones[0]);
    expect(navigateMock).toHaveBeenCalledWith("/defensia/nuevo");
  });
});
