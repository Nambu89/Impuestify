import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DefensiaExpedientePage } from "./DefensiaExpedientePage";
import type { ExpedienteDetalle } from "../types/defensia";

const hookState = {
  expediente: null as ExpedienteDetalle | null,
  loading: false,
  error: null as string | null,
  mutate: vi.fn(),
};

vi.mock("../hooks/useDefensiaExpediente", () => ({
  useDefensiaExpediente: () => hookState,
}));

vi.mock("../hooks/useSEO", () => ({ useSEO: () => {} }));

const expedienteMock: ExpedienteDetalle = {
  id: "exp-1",
  titulo: "IRPF 2023",
  tributo: "IRPF",
  ccaa: "Madrid",
  estado: "dictamen_listo",
  fase_detectada: "COMPROBACION_PROPUESTA",
  fase_confianza: 0.9,
  num_documentos: 4,
  dias_restantes: 14,
  creado_en: "2026-04-01T00:00:00Z",
  actualizado_en: "2026-04-10T00:00:00Z",
  documentos: [],
  brief: {
    id: "br-1",
    texto: "La Hacienda me reclama…",
    chat_history: [],
    creado_en: "2026-04-02T00:00:00Z",
  },
  dictamen: {
    id: "dict-1",
    expediente_id: "exp-1",
    argumentos: [
      {
        regla_id: "R001",
        descripcion: "Motivación insuficiente",
        cita_verificada: "Art. 102.2.c LGT",
        referencia_normativa_canonica: "Art. 102.2.c LGT",
        confianza: 0.95,
        datos_disparo: {},
        impacto_estimado: "Anulación",
      },
    ],
    resumen: "Resumen del dictamen",
    creado_en: "2026-04-10T00:00:00Z",
  },
  escritos: [],
};

function renderAt(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/defensia/${id}`]}>
      <Routes>
        <Route path="/defensia/:id" element={<DefensiaExpedientePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DefensiaExpedientePage", () => {
  beforeEach(() => {
    hookState.expediente = null;
    hookState.loading = false;
    hookState.error = null;
    hookState.mutate.mockReset();
  });

  it("muestra loading mientras carga", () => {
    hookState.loading = true;
    const { container } = renderAt("exp-1");
    expect(container.querySelector(".defensia-expediente-skeleton")).toBeInTheDocument();
  });

  it("muestra 404 si error de carga", () => {
    hookState.error = "Not found";
    renderAt("exp-1");
    expect(screen.getByText(/no se encontró el expediente/i)).toBeInTheDocument();
  });

  it("renderiza título, fase, argumentos verificados y disclaimer", () => {
    hookState.expediente = expedienteMock;
    renderAt("exp-1");
    expect(screen.getByText("IRPF 2023")).toBeInTheDocument();
    expect(screen.getByLabelText(/propuesta de liquidación/i)).toBeInTheDocument();
    expect(screen.getByText("Motivación insuficiente")).toBeInTheDocument();
    expect(
      screen.getAllByText(/no sustituye asesoramiento profesional/i).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("muestra botón exportar si hay dictamen", () => {
    hookState.expediente = expedienteMock;
    renderAt("exp-1");
    expect(
      screen.getByRole("button", { name: /exportar/i }),
    ).toBeInTheDocument();
  });

  it("muestra mensaje si aún no hay dictamen", () => {
    hookState.expediente = { ...expedienteMock, dictamen: null };
    renderAt("exp-1");
    expect(
      screen.getByText(/dictamen pendiente|aún no hay dictamen/i),
    ).toBeInTheDocument();
  });
});
