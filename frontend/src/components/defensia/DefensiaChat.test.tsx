import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DefensiaChat } from "./DefensiaChat";
import type { ChatMessage } from "../../hooks/useDefensiaChat";

const hookState = {
  messages: [] as ChatMessage[],
  streaming: false,
  error: null as string | null,
  send: vi.fn(),
  reset: vi.fn(),
};

vi.mock("../../hooks/useDefensiaChat", () => ({
  useDefensiaChat: () => hookState,
}));

describe("DefensiaChat", () => {
  beforeEach(() => {
    hookState.messages = [];
    hookState.streaming = false;
    hookState.error = null;
    hookState.send.mockReset();
  });

  it("muestra disclaimer persistente + input + botón enviar", () => {
    render(<DefensiaChat expedienteId="exp-1" />);
    expect(
      screen.getByText(/no sustituye asesoramiento profesional/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enviar/i })).toBeInTheDocument();
  });

  it("escribir y enviar dispara send() con el texto", async () => {
    render(<DefensiaChat expedienteId="exp-1" />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "¿Qué puedo alegar?");
    await userEvent.click(screen.getByRole("button", { name: /enviar/i }));
    expect(hookState.send).toHaveBeenCalledWith("¿Qué puedo alegar?");
  });

  it("renderiza mensajes existentes (usuario + asistente)", () => {
    hookState.messages = [
      { role: "user", content: "Hola" },
      { role: "assistant", content: "Según el art. 102 LGT…" },
    ];
    render(<DefensiaChat expedienteId="exp-1" />);
    expect(screen.getByText("Hola")).toBeInTheDocument();
    expect(screen.getByText(/Según el art\. 102 LGT/)).toBeInTheDocument();
  });
});
