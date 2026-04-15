import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ArgumentoCard } from "./ArgumentoCard";
import type { ArgumentoVerificado } from "../../types/defensia";

const argumento: ArgumentoVerificado = {
  regla_id: "R001",
  descripcion: "Motivación insuficiente en la propuesta de liquidación",
  cita_verificada:
    "El artículo 102.2 c) LGT exige expresión de los hechos y fundamentos de derecho.",
  referencia_normativa_canonica: "Art. 102.2.c LGT",
  confianza: 0.94,
  datos_disparo: { casilla: "0505" },
  impacto_estimado: "Anulación de la liquidación",
};

describe("ArgumentoCard", () => {
  it("muestra id de regla, cita canónica y confianza", () => {
    render(<ArgumentoCard argumento={argumento} onVerFuente={() => {}} />);
    expect(screen.getByText(/R001/)).toBeInTheDocument();
    expect(screen.getByText(/Art\. 102\.2\.c LGT/)).toBeInTheDocument();
    // Confianza como porcentaje (94%)
    expect(screen.getByText(/94\s*%/)).toBeInTheDocument();
  });

  it("incluye el disclaimer corto en el pie", () => {
    render(<ArgumentoCard argumento={argumento} onVerFuente={() => {}} />);
    expect(
      screen.getByText(/no sustituye asesoramiento profesional/i),
    ).toBeInTheDocument();
  });

  it("click en 'Ver fuente' dispara onVerFuente con la regla_id", async () => {
    const user = userEvent.setup();
    const onVerFuente = vi.fn();
    render(<ArgumentoCard argumento={argumento} onVerFuente={onVerFuente} />);
    await user.click(screen.getByRole("button", { name: /ver fuente/i }));
    expect(onVerFuente).toHaveBeenCalledWith("R001");
  });

  it("renderiza tildes correctas en descripción", () => {
    render(<ArgumentoCard argumento={argumento} onVerFuente={() => {}} />);
    expect(screen.getByText(/Motivación/)).toBeInTheDocument();
  });
});
