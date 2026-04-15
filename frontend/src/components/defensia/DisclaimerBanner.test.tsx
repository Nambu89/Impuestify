import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DisclaimerBanner } from "./DisclaimerBanner";

describe("DisclaimerBanner", () => {
  it("contiene el disclaimer obligatorio", () => {
    render(<DisclaimerBanner />);
    expect(
      screen.getByText(/DefensIA no sustituye asesoramiento profesional/i),
    ).toBeInTheDocument();
  });

  it("no tiene botón de cerrar (persistente)", () => {
    render(<DisclaimerBanner />);
    expect(
      screen.queryByRole("button", { name: /cerrar/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/cerrar/i)).not.toBeInTheDocument();
  });

  it("tiene role alert para accesibilidad", () => {
    render(<DisclaimerBanner />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
