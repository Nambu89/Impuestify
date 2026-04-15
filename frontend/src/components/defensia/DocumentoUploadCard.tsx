import { useId } from "react";
import { FileText, X, Upload } from "lucide-react";
import "./DocumentoUploadCard.css";

export interface UploadDocumento {
  id: string;
  nombre: string;
  progreso: number;
  estado: "subiendo" | "completado" | "error";
  error?: string;
}

interface Props {
  documento: UploadDocumento | null;
  onRemove: (id: string) => void;
  onFileSelected?: (file: File) => void;
  accept?: string;
}

export function DocumentoUploadCard({
  documento,
  onRemove,
  onFileSelected,
  accept = ".pdf,.jpg,.jpeg,.png,.xml,.xlsx,image/*",
}: Props) {
  const inputId = useId();

  if (documento === null) {
    return (
      <label htmlFor={inputId} className="upload-card upload-card-empty">
        <Upload size={24} aria-hidden="true" />
        <span className="upload-card-hint">Arrastra o selecciona un archivo</span>
        <input
          id={inputId}
          type="file"
          accept={accept}
          className="upload-input"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f && onFileSelected) onFileSelected(f);
          }}
        />
      </label>
    );
  }

  const pct = Math.round(documento.progreso * 100);
  const completado = documento.estado === "completado";
  const error = documento.estado === "error";

  return (
    <div className={`upload-card upload-card-filled ${error ? "error" : ""}`}>
      <FileText size={20} aria-hidden="true" />
      <div className="upload-card-body">
        <span className="upload-card-name">{documento.nombre}</span>
        {!completado && !error && (
          <div
            className="upload-progress"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="upload-progress-bar" style={{ width: `${pct}%` }} />
          </div>
        )}
        {error && <span className="upload-error">{documento.error || "Error al subir"}</span>}
      </div>
      <button
        type="button"
        className="upload-remove"
        aria-label={`Eliminar ${documento.nombre}`}
        onClick={() => onRemove(documento.id)}
      >
        <X size={18} />
      </button>
    </div>
  );
}
