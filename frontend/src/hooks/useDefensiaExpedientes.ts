import { useCallback, useEffect, useState } from "react";
import { useApi } from "./useApi";
import type { Expediente } from "../types/defensia";

interface ExpedientesResponse {
  expedientes: Expediente[];
}

export function useDefensiaExpedientes() {
  const { apiRequest } = useApi();
  const [expedientes, setExpedientes] = useState<Expediente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExpedientes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest<ExpedientesResponse>("/api/defensia/expedientes");
      setExpedientes(res.expedientes ?? []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al cargar expedientes";
      setError(msg);
      setExpedientes([]);
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useEffect(() => {
    void fetchExpedientes();
  }, [fetchExpedientes]);

  return {
    expedientes,
    loading,
    error,
    refetch: fetchExpedientes,
  };
}
