import { BookOpen, Shield } from "lucide-react";
import type { ArgumentoVerificado } from "../../types/defensia";
import "./ArgumentoCard.css";

interface Props {
  argumento: ArgumentoVerificado;
  onVerFuente: (reglaId: string) => void;
}

export function ArgumentoCard({ argumento, onVerFuente }: Props) {
  const confianzaPct = Math.round(argumento.confianza * 100);
  return (
    <article className="argumento-card">
      <header className="argumento-card-header">
        <span className="argumento-card-id">{argumento.regla_id}</span>
        <span className="argumento-card-confianza" aria-label={`Confianza ${confianzaPct}%`}>
          <Shield size={14} aria-hidden="true" />
          {confianzaPct}%
        </span>
      </header>

      <h4 className="argumento-card-desc">{argumento.descripcion}</h4>

      <blockquote className="argumento-card-cita">
        <p>{argumento.cita_verificada}</p>
        <cite>— {argumento.referencia_normativa_canonica}</cite>
      </blockquote>

      {argumento.impacto_estimado && (
        <p className="argumento-card-impacto">
          <strong>Impacto estimado:</strong> {argumento.impacto_estimado}
        </p>
      )}

      <footer className="argumento-card-footer">
        <button
          type="button"
          className="argumento-card-fuente-btn"
          onClick={() => onVerFuente(argumento.regla_id)}
        >
          <BookOpen size={14} aria-hidden="true" />
          Ver fuente RAG
        </button>
        <p className="argumento-card-disclaimer">
          Este contenido no sustituye asesoramiento profesional.
        </p>
      </footer>
    </article>
  );
}
