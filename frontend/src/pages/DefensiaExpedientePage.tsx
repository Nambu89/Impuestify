import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, FileText, AlertCircle, ArrowLeft, Scale } from "lucide-react";
import { useDefensiaExpediente } from "../hooks/useDefensiaExpediente";
import { useDefensiaExport } from "../hooks/useDefensiaExport";
import { useSEO } from "../hooks/useSEO";
import { DisclaimerBanner } from "../components/defensia/DisclaimerBanner";
import { FaseBadge } from "../components/defensia/FaseBadge";
import { PlazoBadge } from "../components/defensia/PlazoBadge";
import { ArgumentoCard } from "../components/defensia/ArgumentoCard";
import { EscritoEditor } from "../components/defensia/EscritoEditor";
import { PreExportModal } from "../components/defensia/PreExportModal";
import { DefensiaChat } from "../components/defensia/DefensiaChat";
import { TRIBUTO_LABELS } from "../types/defensia";
import "./DefensiaExpedientePage.css";

type Tab = "resumen" | "argumentos" | "escrito" | "chat";

export function DefensiaExpedientePage() {
  const { id } = useParams<{ id: string }>();
  const { expediente, loading, error, mutate } = useDefensiaExpediente(id ?? null);
  const { exportar, exporting, needsDisclaimer, resetDisclaimer, error: exportError } = useDefensiaExport();
  const [tab, setTab] = useState<Tab>("resumen");
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportFormato, setExportFormato] = useState<"docx" | "pdf">("docx");

  useSEO({
    title: expediente ? `DefensIA — ${expediente.titulo}` : "DefensIA — Expediente",
    description: "Expediente DefensIA con argumentos verificados y escrito.",
    noindex: true,
  });

  const handleExportClick = (formato: "docx" | "pdf") => {
    setExportFormato(formato);
    setExportModalOpen(true);
  };

  const handleExportConfirm = async (disclaimerAceptado: boolean) => {
    if (!expediente || !expediente.escritos[0]) return;
    await exportar(expediente.id, expediente.escritos[0].id, exportFormato, disclaimerAceptado);
    if (!needsDisclaimer && !exportError) {
      setExportModalOpen(false);
    }
  };

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
        <Link to="/defensia" className="defensia-back-link">
          <ArrowLeft size={16} aria-hidden="true" /> Volver a expedientes
        </Link>
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
      <Link to="/defensia" className="defensia-back-link">
        <ArrowLeft size={16} aria-hidden="true" /> Volver a expedientes
      </Link>
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

      <nav className="defensia-expediente-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "resumen"}
          className={`defensia-tab ${tab === "resumen" ? "active" : ""}`}
          onClick={() => setTab("resumen")}
        >
          Resumen
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "argumentos"}
          className={`defensia-tab ${tab === "argumentos" ? "active" : ""}`}
          onClick={() => setTab("argumentos")}
        >
          Argumentos
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "escrito"}
          className={`defensia-tab ${tab === "escrito" ? "active" : ""}`}
          onClick={() => setTab("escrito")}
        >
          Escrito
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "chat"}
          className={`defensia-tab ${tab === "chat" ? "active" : ""}`}
          onClick={() => setTab("chat")}
        >
          Chat
        </button>
      </nav>

      {tab === "resumen" && (
        <section className="defensia-expediente-section" aria-labelledby="brief-title">
          <h2 id="brief-title">Tu caso</h2>
          {expediente.brief ? (
            <p className="defensia-expediente-brief">{expediente.brief.texto}</p>
          ) : (
            <p className="defensia-expediente-placeholder">Aún no has escrito tu brief.</p>
          )}
        </section>
      )}

      {tab === "argumentos" && (
        <section className="defensia-expediente-section" aria-labelledby="argumentos-title">
          <div className="defensia-expediente-section-header">
            <h2 id="argumentos-title">Argumentos verificados</h2>
          </div>
          {expediente.dictamen && expediente.dictamen.argumentos.length > 0 ? (
            <div className="defensia-expediente-argumentos">
              {expediente.dictamen.argumentos.map((arg) => (
                <ArgumentoCard
                  key={arg.regla_id}
                  argumento={arg}
                  onVerFuente={(rid) => console.log("ver fuente", rid)}
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
      )}

      {tab === "escrito" && (
        <section className="defensia-expediente-section" aria-labelledby="escrito-title">
          <div className="defensia-expediente-section-header">
            <h2 id="escrito-title">Escrito de alegaciones</h2>
            {expediente.escritos[0] && (
              <div className="defensia-expediente-export-group">
                <button
                  type="button"
                  className="defensia-expediente-export-btn"
                  onClick={() => handleExportClick("docx")}
                  disabled={exporting}
                >
                  <Download size={16} aria-hidden="true" />
                  DOCX
                </button>
                <button
                  type="button"
                  className="defensia-expediente-export-btn"
                  onClick={() => handleExportClick("pdf")}
                  disabled={exporting}
                >
                  <Download size={16} aria-hidden="true" />
                  PDF
                </button>
              </div>
            )}
          </div>
          {expediente.escritos[0] ? (
            <EscritoEditor
              expedienteId={expediente.id}
              escritoId={expediente.escritos[0].id}
              contenidoInicial={expediente.escritos[0].contenido_markdown}
              readOnly={expediente.escritos[0].exportado}
              onSaved={() => void mutate()}
            />
          ) : (
            <div className="defensia-expediente-empty">
              <FileText size={32} aria-hidden="true" />
              <p>
                El escrito se generará automáticamente cuando DefensIA termine el
                análisis del expediente.
              </p>
            </div>
          )}
        </section>
      )}

      {tab === "chat" && (
        <section className="defensia-expediente-section" aria-labelledby="chat-title">
          <h2 id="chat-title">Chat con DefensIA</h2>
          <DefensiaChat expedienteId={expediente.id} />
        </section>
      )}

      <PreExportModal
        open={exportModalOpen}
        formato={exportFormato}
        onClose={() => {
          setExportModalOpen(false);
          resetDisclaimer();
        }}
        onConfirm={handleExportConfirm}
      />
    </div>
  );
}

export default DefensiaExpedientePage;
