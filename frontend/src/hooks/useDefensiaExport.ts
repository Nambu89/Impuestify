import { useCallback, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export type Formato = "docx" | "pdf";

export function useDefensiaExport() {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsDisclaimer, setNeedsDisclaimer] = useState(false);

  const exportar = useCallback(
    async (
      expedienteId: string,
      escritoId: string,
      formato: Formato,
      disclaimerAceptado: boolean,
    ) => {
      setError(null);
      setNeedsDisclaimer(false);
      setExporting(true);

      try {
        const token = localStorage.getItem("access_token");
        const url = `${API_URL}/defensia/expedientes/${expedienteId}/escrito/${escritoId}/export?formato=${formato}`;
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ disclaimer_aceptado: disclaimerAceptado }),
        });

        if (res.status === 428) {
          setNeedsDisclaimer(true);
          setExporting(false);
          return;
        }

        if (res.status === 402) {
          setError("Cuota mensual agotada. Compra un expediente extra desde Ajustes.");
          setExporting(false);
          return;
        }

        if (!res.ok) {
          let detail = `Error HTTP ${res.status}`;
          try {
            const data = await res.json();
            detail = data.detail || detail;
          } catch {
            // ignore
          }
          setError(detail);
          setExporting(false);
          return;
        }

        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        const filename = `defensia_${expedienteId}.${formato}`;
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(objectUrl);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Error al exportar";
        setError(msg);
      } finally {
        setExporting(false);
      }
    },
    [],
  );

  const resetDisclaimer = useCallback(() => setNeedsDisclaimer(false), []);

  return { exportar, exporting, error, needsDisclaimer, resetDisclaimer };
}
