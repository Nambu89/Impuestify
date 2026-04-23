import { Link, useNavigate } from "react-router-dom";
import { Plus, AlertCircle, ArrowLeft, Scale } from "lucide-react";
import { useDefensiaExpedientes } from "../hooks/useDefensiaExpedientes";
import { useSEO } from "../hooks/useSEO";
import { DisclaimerBanner } from "../components/defensia/DisclaimerBanner";
import { ExpedienteTimelineCard } from "../components/defensia/ExpedienteTimelineCard";
import "./DefensiaListPage.css";

export function DefensiaListPage() {
  const navigate = useNavigate();
  const { expedientes, loading, error, refetch } = useDefensiaExpedientes();

  useSEO({
    title: "DefensIA — Mis expedientes",
    description: "Expedientes abiertos en DefensIA.",
    noindex: true,
  });

  const handleCrear = () => navigate("/defensia/nuevo");

  return (
    <div className="defensia-list-page">
      <Link to="/" className="defensia-back-link">
        <ArrowLeft size={16} aria-hidden="true" /> Volver a inicio
      </Link>
      <header className="defensia-list-header">
        <div className="defensia-list-title-block">
          <Scale size={28} aria-hidden="true" />
          <div>
            <h1>DefensIA</h1>
            <p>Tus expedientes frente a Hacienda</p>
          </div>
        </div>
        <button
          type="button"
          className="defensia-list-crear-btn"
          onClick={handleCrear}
        >
          <Plus size={18} aria-hidden="true" />
          Crear expediente
        </button>
      </header>

      <DisclaimerBanner />

      {loading && (
        <div className="defensia-list-skeleton" aria-busy="true">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      )}

      {!loading && error && (
        <div className="defensia-list-error">
          <AlertCircle size={24} aria-hidden="true" />
          <p>Error al cargar los expedientes: {error}</p>
          <button type="button" onClick={() => void refetch()}>
            Reintentar
          </button>
        </div>
      )}

      {!loading && !error && expedientes.length === 0 && (
        <div className="defensia-list-empty">
          <Scale size={48} aria-hidden="true" />
          <h2>Todavía no tienes expedientes</h2>
          <p>
            Abre uno cuando recibas una comprobación, un requerimiento o una
            sanción de Hacienda y quieras estudiar la respuesta.
          </p>
          <button
            type="button"
            className="defensia-list-crear-btn"
            onClick={handleCrear}
          >
            <Plus size={18} aria-hidden="true" />
            Crear expediente
          </button>
        </div>
      )}

      {!loading && !error && expedientes.length > 0 && (
        <div className="defensia-list-grid">
          {expedientes.map((exp) => (
            <ExpedienteTimelineCard
              key={exp.id}
              expediente={exp}
              onClick={(id) => navigate(`/defensia/${id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default DefensiaListPage;
