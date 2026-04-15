import { useCallback, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface UploadError extends Error {
  code: "FILE_TOO_LARGE" | "UNAUTHORIZED" | "NETWORK" | "UNKNOWN";
  status?: number;
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

      return new Promise<{ id: string }>((resolve, reject) => {
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
              const data = JSON.parse(xhr.responseText);
              resolve(data);
            } catch {
              resolve({ id: "" });
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
          `${API_URL}/api/defensia/expedientes/${expedienteId}/documentos`,
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
