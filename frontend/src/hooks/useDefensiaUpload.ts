import { useCallback, useState } from "react";
import type { Fase, TipoDocumento } from "../types/defensia";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface UploadError extends Error {
  code: "FILE_TOO_LARGE" | "UNAUTHORIZED" | "NETWORK" | "UNKNOWN";
  status?: number;
}

/**
 * Respuesta enriquecida de POST /api/defensia/expedientes/:id/documentos.
 *
 * El backend ejecuta la Fase 1 automatica (classifier + extractor + phase
 * detector) al subir el documento. Los campos auto-detectados se devuelven
 * para que la UI los muestre sin necesidad de otro round-trip.
 *
 * Cualquiera de los campos opcionales puede venir `null` si el classifier
 * o el extractor fallaron (best-effort).
 */
export interface UploadResponse {
  id: string;
  nombre_original: string;
  tipo_documento: TipoDocumento | null;
  clasificacion_confianza: number | null;
  fecha_acto: string | null;
  fase_detectada: Fase | null;
  fase_confianza: number | null;
  created_at: string;
}

function makeError(code: UploadError["code"], message: string, status?: number): UploadError {
  const err = new Error(message) as UploadError;
  err.code = code;
  err.status = status;
  return err;
}

export function useDefensiaUpload(expedienteId: string) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const upload = useCallback(
    (file: File, tipo: string, onProgress?: (p: number) => void) => {
      setUploading(true);
      setProgress(0);

      return new Promise<UploadResponse>((resolve, reject) => {
        const form = new FormData();
        form.append("file", file);
        form.append("tipo_documento", tipo);

        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const p = e.loaded / e.total;
            setProgress(p);
            onProgress?.(p);
          }
        };

        xhr.onload = () => {
          setUploading(false);
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText) as Partial<UploadResponse>;
              resolve({
                id: data.id ?? "",
                nombre_original: data.nombre_original ?? file.name,
                tipo_documento: data.tipo_documento ?? null,
                clasificacion_confianza: data.clasificacion_confianza ?? null,
                fecha_acto: data.fecha_acto ?? null,
                fase_detectada: data.fase_detectada ?? null,
                fase_confianza: data.fase_confianza ?? null,
                created_at: data.created_at ?? new Date().toISOString(),
              });
            } catch {
              reject(makeError("UNKNOWN", "Respuesta del servidor no válida"));
            }
            return;
          }
          if (xhr.status === 413) {
            reject(makeError("FILE_TOO_LARGE", "El archivo excede 20 MB", 413));
            return;
          }
          if (xhr.status === 401) {
            reject(makeError("UNAUTHORIZED", "Sesión expirada", 401));
            return;
          }
          reject(makeError("UNKNOWN", `Error HTTP ${xhr.status}`, xhr.status));
        };

        xhr.onerror = () => {
          setUploading(false);
          reject(makeError("NETWORK", "Error de red"));
        };

        xhr.open(
          "POST",
          `${API_URL}/defensia/expedientes/${expedienteId}/documentos`,
        );

        const token = localStorage.getItem("access_token");
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

        xhr.send(form);
      });
    },
    [expedienteId],
  );

  return { upload, progress, uploading };
}
