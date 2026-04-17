import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EscritoEditor } from "./EscritoEditor";

const originalFetch = global.fetch;

beforeEach(() => {
  localStorage.setItem("access_token", "fake-jwt");
});

afterEach(() => {
  global.fetch = originalFetch;
  localStorage.clear();
});

describe("EscritoEditor", () => {
  it("renderiza el contenido inicial del escrito", () => {
    render(
      <EscritoEditor
        expedienteId="exp-1"
        escritoId="esc-1"
        contenidoInicial="# Título\n\nCuerpo del escrito."
        onSaved={() => {}}
      />,
    );
    expect(screen.getByText(/Título/)).toBeInTheDocument();
  });

  it("dispara onChange cuando el usuario edita", async () => {
    const onChange = vi.fn();
    render(
      <EscritoEditor
        expedienteId="exp-1"
        escritoId="esc-1"
        contenidoInicial="Hola"
        onChange={onChange}
        onSaved={() => {}}
      />,
    );
    const editor = screen.getByRole("textbox");
    await userEvent.click(editor);
    await userEvent.keyboard(" mundo");
    await waitFor(() => expect(onChange).toHaveBeenCalled());
  });

  it("click en Guardar llama PATCH al endpoint del escrito", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "esc-1" }),
    });
    const onSaved = vi.fn();
    render(
      <EscritoEditor
        expedienteId="exp-1"
        escritoId="esc-1"
        contenidoInicial="Texto"
        onSaved={onSaved}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/defensia/expedientes/exp-1/escrito/esc-1"),
        expect.objectContaining({ method: "PATCH" }),
      );
      expect(onSaved).toHaveBeenCalled();
    });
  });

  it("muestra mensaje de error si el guardado falla", async () => {
    // @ts-expect-error - mocked
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Error interno" }),
    });
    render(
      <EscritoEditor
        expedienteId="exp-1"
        escritoId="esc-1"
        contenidoInicial="X"
        onSaved={() => {}}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));
    await waitFor(() =>
      expect(screen.getByText(/error/i)).toBeInTheDocument(),
    );
  });
});
