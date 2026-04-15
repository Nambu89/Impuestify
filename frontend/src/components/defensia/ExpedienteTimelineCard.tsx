import { FileText, MapPin } from "lucide-react";
import type { Expediente } from "../../types/defensia";
import { TRIBUTO_LABELS } from "../../types/defensia";
import { FaseBadge } from "./FaseBadge";
import { PlazoBadge } from "./PlazoBadge";
import "./ExpedienteTimelineCard.css";

interface Props {
  expediente: Expediente;
  onClick: (id: string) => void;
}

function formatFecha(iso: string): string {
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(d);
  } catch {
    return iso;
  }
}

export function ExpedienteTimelineCard({ expediente, onClick }: Props) {
  const docs = expediente.num_documentos;
  const docsTexto = docs === 1 ? "1 documento" : `${docs} documentos`;

  return (
    <button
      type="button"
      className="expediente-card"
      aria-label={expediente.titulo}
      onClick={() => onClick(expediente.id)}
    >
      <div className="expediente-card-header">
        <h3 className="expediente-card-title">{expediente.titulo}</h3>
        <PlazoBadge dias_restantes={expediente.dias_restantes} />
      </div>
      <div className="expediente-card-meta">
        <span className="expediente-card-tributo">
          {TRIBUTO_LABELS[expediente.tributo]}
        </span>
        <span className="expediente-card-ccaa">
          <MapPin size={14} aria-hidden="true" />
          {expediente.ccaa}
        </span>
        <span className="expediente-card-docs">
          <FileText size={14} aria-hidden="true" />
          {docsTexto}
        </span>
      </div>
      <div className="expediente-card-footer">
        <FaseBadge fase={expediente.fase_detectada} />
        <span className="expediente-card-fecha">
          Actualizado {formatFecha(expediente.actualizado_en)}
        </span>
      </div>
    </button>
  );
}
