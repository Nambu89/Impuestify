import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PlazoBadge } from "./PlazoBadge";

describe("PlazoBadge", () => {
  it.each([
    [20, "plazo-verde", "20 días"],
    [15, "plazo-ambar", "15 días"],
    [10, "plazo-ambar", "10 días"],
    [5, "plazo-ambar", "5 días"],
    [4, "plazo-rojo", "4 días"],
    [1, "plazo-rojo", "1 día"],
    [0, "plazo-rojo", "0 días"],
    [-2, "plazo-gris", "Vencido"],
  ])("dias=%s => class %s, texto '%s'", (dias, clase, texto) => {
    const { container } = render(<PlazoBadge dias_restantes={dias} />);
    const span = container.querySelector(".plazo-badge")!;
    expect(span).toHaveClass(clase);
    expect(span).toHaveTextContent(texto);
  });

  it("devuelve null si dias_restantes es null", () => {
    const { container } = render(<PlazoBadge dias_restantes={null} />);
    expect(container.querySelector(".plazo-badge")).toBeNull();
  });

  it("tiene aria-label descriptivo", () => {
    render(<PlazoBadge dias_restantes={10} />);
    const badge = screen.getByLabelText(/plazo/i);
    expect(badge).toBeInTheDocument();
  });
});
