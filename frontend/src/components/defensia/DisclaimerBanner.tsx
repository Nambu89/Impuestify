import { AlertTriangle } from "lucide-react";
import "./DisclaimerBanner.css";

export function DisclaimerBanner() {
  return (
    <div className="defensia-disclaimer" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <p>
        <strong>DefensIA no sustituye asesoramiento profesional.</strong>{" "}
        Las sugerencias generadas son orientativas. Antes de presentar cualquier
        escrito, valídalo con un asesor fiscal o abogado colegiado.
      </p>
    </div>
  );
}
