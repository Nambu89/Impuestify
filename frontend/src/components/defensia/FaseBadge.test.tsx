import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FaseBadge } from "./FaseBadge";
import type { Fase } from "../../types/defensia";
import { FASE_LABELS } from "../../types/defensia";

const fases: Fase[] = [
  "COMPROBACION_REQUERIMIENTO",
  "COMPROBACION_PROPUESTA",
  "COMPROBACION_POST_ALEGACIONES",
  "LIQUIDACION_FIRME_PLAZO_RECURSO",
  "SANCIONADOR_INICIADO",
  "SANCIONADOR_PROPUESTA",
  "SANCIONADOR_IMPUESTA",
  "REPOSICION_INTERPUESTA",
  "TEAR_INTERPUESTA",
  "TEAR_AMPLIACION_POSIBLE",
  "FUERA_DE_ALCANCE",
  "INDETERMINADA",
];

describe("FaseBadge", () => {
  it.each(fases)("renderiza la fase %s con data-fase y aria-label", (fase) => {
    const { container } = render(<FaseBadge fase={fase} />);
    const el = container.querySelector(".fase-badge")!;
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute("data-fase", fase);
    expect(screen.getByLabelText(new RegExp(FASE_LABELS[fase], "i"))).toBeInTheDocument();
  });
});
