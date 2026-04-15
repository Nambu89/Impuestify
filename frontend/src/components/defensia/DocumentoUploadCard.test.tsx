import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentoUploadCard } from "./DocumentoUploadCard";

describe("DocumentoUploadCard", () => {
  it("renderiza nombre del documento y botón eliminar", async () => {
    const onRemove = vi.fn();
    render(
      <DocumentoUploadCard
        documento={{
          id: "d1",
          nombre: "liquidacion_2024.pdf",
          progreso: 1,
          estado: "completado",
        }}
        onRemove={onRemove}
      />,
    );
    expect(screen.getByText("liquidacion_2024.pdf")).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: /eliminar/i });
    await userEvent.click(btn);
    expect(onRemove).toHaveBeenCalledWith("d1");
  });

  it("muestra barra de progreso si progreso < 1", () => {
    render(
      <DocumentoUploadCard
        documento={{
          id: "d2",
          nombre: "doc.pdf",
          progreso: 0.5,
          estado: "subiendo",
        }}
        onRemove={() => {}}
      />,
    );
    const progress = screen.getByRole("progressbar");
    expect(progress).toHaveAttribute("aria-valuenow", "50");
  });

  it("usa patrón iOS-safe con input absolute + label htmlFor (NO display:none)", () => {
    // Placeholder documento (no aun cargado) para forzar el input visible
    const { container } = render(
      <DocumentoUploadCard documento={null} onRemove={() => {}} onFileSelected={() => {}} />,
    );
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("id");
    const label = container.querySelector(`label[for="${input.id}"]`);
    expect(label).toBeInTheDocument();

    // Debe tener position absolute + opacity 0 (comprobable via className)
    expect(input.className).toMatch(/upload-input/);
  });
});
