import { useCallback, useEffect, useState } from "react";
import { useApi } from "./useApi";
import type { ExpedienteDetalle } from "../types/defensia";

export function useDefensiaExpediente(id: string | null) {
  const { apiRequest } = useApi();
  const [expediente, setExpediente] = useState<ExpedienteDetalle | null>(null);
  const [loading, setLoading] = useState<boolean>(id !== null);
  const [error, setError] = useState<string | null>(null);

  const fetchExpediente = useCallback(async () => {
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest<ExpedienteDetalle>(
        `/api/defensia/expedientes/${id}`,
      );
      setExpediente(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al cargar expediente";
      setError(msg);
      setExpediente(null);
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useEffect(() => {
    void fetchExpediente();
  }, [fetchExpediente]);

  return {
    expediente,
    loading,
    error,
    mutate: fetchExpediente,
  };
}
