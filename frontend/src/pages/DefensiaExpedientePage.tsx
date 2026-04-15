import { useParams } from "react-router-dom";
import { Download, FileText, AlertCircle, Scale } from "lucide-react";
import { useDefensiaExpediente } from "../hooks/useDefensiaExpediente";
import { useSEO } from "../hooks/useSEO";
import { DisclaimerBanner } from "../components/defensia/DisclaimerBanner";
import { FaseBadge } from "../components/defensia/FaseBadge";
import { PlazoBadge } from "../components/defensia/PlazoBadge";
import { ArgumentoCard } from "../components/defensia/ArgumentoCard";
import { TRIBUTO_LABELS } from "../types/defensia";
import "./DefensiaExpedientePage.css";

export function DefensiaExpedientePage() {
  const { id } = useParams<{ id: string }>();
  const { expediente, loading, error } = useDefensiaExpediente(id ?? null);

  useSEO({
    title: expediente ? `DefensIA — ${expediente.titulo}` : "DefensIA — Expediente",
    description: "Expediente DefensIA con argumentos verificados y escrito.",
    noindex: true,
  });

  if (loading) {
    return (
      <div className="defensia-expediente-page">
        <div className="defensia-expediente-skeleton" aria-busy="true">
          <div className="skeleton-block" />
          <div className="skeleton-block" />
          <div className="skeleton-block" />
        </div>
      </div>
    );
  }

  if (error || !expediente) {
    return (
      <div className="defensia-expediente-page">
        <div className="defensia-expediente-404">
          <AlertCircle size={48} aria-hidden="true" />
          <h2>No se encontró el expediente</h2>
          <p>
            Es posible que el enlace haya caducado o que no tengas permisos
            para acceder a este expediente.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="defensia-expediente-page">
      <header className="defensia-expediente-header">
        <div className="defensia-expediente-title-block">
          <Scale size={24} aria-hidden="true" />
          <div>
            <h1>{expediente.titulo}</h1>
            <p>
              {TRIBUTO_LABELS[expediente.tributo]} · {expediente.ccaa} ·{" "}
              {expediente.num_documentos} documentos
            </p>
          </div>
        </div>
        <div className="defensia-expediente-badges">
          <FaseBadge fase={expediente.fase_detectada} />
          <PlazoBadge dias_restantes={expediente.dias_restantes} />
        </div>
      </header>

      <DisclaimerBanner />

      <section className="defensia-expediente-section" aria-labelledby="brief-title">
        <h2 id="brief-title">Tu caso</h2>
        {expediente.brief ? (
          <p className="defensia-expediente-brief">{expediente.brief.texto}</p>
        ) : (
          <p className="defensia-expediente-placeholder">Aún no has escrito tu brief.</p>
        )}
      </section>

      <section className="defensia-expediente-section" aria-labelledby="argumentos-title">
        <div className="defensia-expediente-section-header">
          <h2 id="argumentos-title">Argumentos verificados</h2>
          {expediente.dictamen && expediente.dictamen.argumentos.length > 0 && (
            <button type="button" className="defensia-expediente-export-btn">
              <Download size={16} aria-hidden="true" />
              Exportar escrito
            </button>
          )}
        </div>
        {expediente.dictamen && expediente.dictamen.argumentos.length > 0 ? (
          <div className="defensia-expediente-argumentos">
            {expediente.dictamen.argumentos.map((arg) => (
              <ArgumentoCard
                key={arg.regla_id}
                argumento={arg}
                onVerFuente={(id) => console.log("ver fuente", id)}
              />
            ))}
          </div>
        ) : (
          <div className="defensia-expediente-empty">
            <FileText size={32} aria-hidden="true" />
            <p>
              Dictamen pendiente. Cuando termines de escribir tu brief pulsa
              "Analizar" para que DefensIA genere los argumentos.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

export default DefensiaExpedientePage;
