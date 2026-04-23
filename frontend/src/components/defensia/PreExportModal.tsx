import { useState, useEffect } from "react";
import { X, Download, AlertTriangle } from "lucide-react";
import "./PreExportModal.css";

interface Props {
  open: boolean;
  formato: "docx" | "pdf";
  onClose: () => void;
  onConfirm: (disclaimerAceptado: boolean) => void;
}

export function PreExportModal({ open, formato, onClose, onConfirm }: Props) {
  const [aceptado, setAceptado] = useState(false);

  useEffect(() => {
    if (!open) setAceptado(false);
  }, [open]);

  if (!open) return null;

  return (
    <div className="pre-export-backdrop" role="dialog" aria-modal="true">
      <div className="pre-export-modal">
        <header className="pre-export-header">
          <h2>Exportar escrito</h2>
          <button
            type="button"
            className="pre-export-close"
            onClick={onClose}
            aria-label="Cerrar"
          >
            <X size={18} />
          </button>
        </header>

        <div className="pre-export-body">
          <div className="pre-export-warning">
            <AlertTriangle size={20} aria-hidden="true" />
            <div>
              <strong>Aviso legal importante</strong>
              <p>
                El escrito que genera DefensIA es orientativo: se apoya en
                reglas fiscales deterministas y jurisprudencia verificada,
                pero <strong>no sustituye asesoramiento profesional</strong>.
                Antes de presentarlo ante la Administración tributaria,
                revísalo con un asesor fiscal o con un abogado colegiado.
              </p>
            </div>
          </div>

          <label className="pre-export-checkbox">
            <input
              type="checkbox"
              checked={aceptado}
              onChange={(e) => setAceptado(e.target.checked)}
            />
            <span>He leído y entendido el aviso legal.</span>
          </label>
        </div>

        <footer className="pre-export-footer">
          <button
            type="button"
            className="pre-export-cancel"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="pre-export-confirm"
            disabled={!aceptado}
            onClick={() => onConfirm(true)}
          >
            <Download size={16} aria-hidden="true" />
            Exportar {formato.toUpperCase()}
          </button>
        </footer>
      </div>
    </div>
  );
}
