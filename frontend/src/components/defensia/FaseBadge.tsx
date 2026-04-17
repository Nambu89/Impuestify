import type { Fase } from "../../types/defensia";
import { FASE_LABELS } from "../../types/defensia";
import "./FaseBadge.css";

interface Props {
  fase: Fase;
}

const FASE_COLOR_CLASS: Record<Fase, string> = {
  COMPROBACION_REQUERIMIENTO: "fase-azul",
  COMPROBACION_PROPUESTA: "fase-azul",
  COMPROBACION_POST_ALEGACIONES: "fase-cyan",
  LIQUIDACION_FIRME_PLAZO_RECURSO: "fase-naranja",
  SANCIONADOR_INICIADO: "fase-rojo-claro",
  SANCIONADOR_PROPUESTA: "fase-rojo",
  SANCIONADOR_IMPUESTA: "fase-rojo-oscuro",
  REPOSICION_INTERPUESTA: "fase-morado",
  TEAR_INTERPUESTA: "fase-indigo",
  TEAR_AMPLIACION_POSIBLE: "fase-indigo-claro",
  FUERA_DE_ALCANCE: "fase-gris",
  INDETERMINADA: "fase-gris",
};

export function FaseBadge({ fase }: Props) {
  const label = FASE_LABELS[fase];
  const clase = FASE_COLOR_CLASS[fase];
  return (
    <span
      className={`fase-badge ${clase}`}
      data-fase={fase}
      aria-label={`Fase ${label}`}
    >
      {label}
    </span>
  );
}
