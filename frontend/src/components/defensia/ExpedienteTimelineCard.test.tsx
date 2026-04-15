import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExpedienteTimelineCard } from "./ExpedienteTimelineCard";
import type { Expediente } from "../../types/defensia";

const expedienteMock: Expediente = {
  id: "exp-1",
  titulo: "IRPF Ejercicio 2023",
  tributo: "IRPF",
  ccaa: "Madrid",
  estado: "en_analisis",
  fase_detectada: "COMPROBACION_PROPUESTA",
  fase_confianza: 0.92,
  num_documentos: 4,
  dias_restantes: 12,
  creado_en: "2026-04-01T10:00:00Z",
  actualizado_en: "2026-04-10T14:30:00Z",
};

describe("ExpedienteTimelineCard", () => {
  it("renderiza título, fase, plazo y número de documentos", () => {
    render(<ExpedienteTimelineCard expediente={expedienteMock} onClick={() => {}} />);
    expect(screen.getByText("IRPF Ejercicio 2023")).toBeInTheDocument();
    expect(screen.getByLabelText(/propuesta de liquidación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/plazo 12 días/i)).toBeInTheDocument();
    expect(screen.getByText(/4 documentos/i)).toBeInTheDocument();
  });

  it("click dispara onClick con el id del expediente", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<ExpedienteTimelineCard expediente={expedienteMock} onClick={onClick} />);
    await user.click(screen.getByRole("button", { name: /IRPF Ejercicio 2023/ }));
    expect(onClick).toHaveBeenCalledWith("exp-1");
  });

  it("usa tildes correctas en textos visibles", () => {
    render(<ExpedienteTimelineCard expediente={expedienteMock} onClick={() => {}} />);
    // "liquidación" con tilde (via FaseBadge)
    expect(screen.getByText(/liquidación/i)).toBeInTheDocument();
  });

  it("formatea 1 documento en singular", () => {
    render(
      <ExpedienteTimelineCard
        expediente={{ ...expedienteMock, num_documentos: 1 }}
        onClick={() => {}}
      />,
    );
    expect(screen.getByText(/1 documento\b/i)).toBeInTheDocument();
  });
});
