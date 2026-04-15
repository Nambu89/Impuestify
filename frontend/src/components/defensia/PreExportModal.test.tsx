import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreExportModal } from "./PreExportModal";

describe("PreExportModal", () => {
  it("checkbox inicialmente unchecked y botón exportar disabled", () => {
    render(
      <PreExportModal
        open={true}
        formato="docx"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    const btn = screen.getByRole("button", { name: /exportar docx/i });
    expect(btn).toBeDisabled();
  });

  it("marcar el checkbox habilita el botón exportar", async () => {
    render(
      <PreExportModal
        open={true}
        formato="pdf"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: /exportar pdf/i })).not.toBeDisabled();
  });

  it("click en exportar llama onConfirm con disclaimer=true", async () => {
    const onConfirm = vi.fn();
    render(
      <PreExportModal
        open={true}
        formato="docx"
        onClose={() => {}}
        onConfirm={onConfirm}
      />,
    );
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /exportar docx/i }));
    expect(onConfirm).toHaveBeenCalledWith(true);
  });

  it("contiene el texto 'aviso legal' con tildes", () => {
    render(
      <PreExportModal
        open={true}
        formato="docx"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByText(/aviso legal importante/i)).toBeInTheDocument();
    expect(
      screen.getByText(/he leído y entendido/i),
    ).toBeInTheDocument();
  });

  it("cuando open=false no renderiza", () => {
    const { container } = render(
      <PreExportModal
        open={false}
        formato="docx"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
