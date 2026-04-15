import { useReducer } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Loader2, Scale } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useDefensiaUpload } from "../hooks/useDefensiaUpload";
import { useSEO } from "../hooks/useSEO";
import { DisclaimerBanner } from "../components/defensia/DisclaimerBanner";
import { TributoSelect } from "../components/defensia/TributoSelect";
import { DocumentoUploadCard, type UploadDocumento } from "../components/defensia/DocumentoUploadCard";
import { FaseBadge } from "../components/defensia/FaseBadge";
import type { Tributo, Fase } from "../types/defensia";
import "./DefensiaWizardPage.css";

type Paso = 1 | 2 | 3 | 4 | 5;

interface WizardState {
  paso: Paso;
  tributo: Tributo | null;
  ccaa: string;
  expedienteId: string | null;
  documentos: UploadDocumento[];
  faseDetectada: Fase | null;
  brief: string;
  creandoExpediente: boolean;
  error: string | null;
}

type Action =
  | { type: "SET_TRIBUTO"; tributo: Tributo }
  | { type: "SET_CCAA"; ccaa: string }
  | { type: "CREAR_START" }
  | { type: "CREAR_OK"; id: string }
  | { type: "CREAR_ERROR"; error: string }
  | { type: "ADD_DOC"; doc: UploadDocumento }
  | { type: "REMOVE_DOC"; id: string }
  | { type: "SET_FASE"; fase: Fase }
  | { type: "SET_BRIEF"; brief: string }
  | { type: "NEXT" }
  | { type: "PREV" };

const initialState: WizardState = {
  paso: 1,
  tributo: null,
  ccaa: "Madrid",
  expedienteId: null,
  documentos: [],
  faseDetectada: null,
  brief: "",
  creandoExpediente: false,
  error: null,
};

function reducer(state: WizardState, action: Action): WizardState {
  switch (action.type) {
    case "SET_TRIBUTO":
      return { ...state, tributo: action.tributo };
    case "SET_CCAA":
      return { ...state, ccaa: action.ccaa };
    case "CREAR_START":
      return { ...state, creandoExpediente: true, error: null };
    case "CREAR_OK":
      return {
        ...state,
        creandoExpediente: false,
        expedienteId: action.id,
        paso: 2,
      };
    case "CREAR_ERROR":
      return { ...state, creandoExpediente: false, error: action.error };
    case "ADD_DOC":
      return { ...state, documentos: [...state.documentos, action.doc] };
    case "REMOVE_DOC":
      return {
        ...state,
        documentos: state.documentos.filter((d) => d.id !== action.id),
      };
    case "SET_FASE":
      return { ...state, faseDetectada: action.fase };
    case "SET_BRIEF":
      return { ...state, brief: action.brief };
    case "NEXT":
      return { ...state, paso: Math.min(5, state.paso + 1) as Paso };
    case "PREV":
      return { ...state, paso: Math.max(1, state.paso - 1) as Paso };
    default:
      return state;
  }
}

export function DefensiaWizardPage() {
  const navigate = useNavigate();
  const { apiRequest } = useApi();
  const [state, dispatch] = useReducer(reducer, initialState);

  useSEO({
    title: "DefensIA — Nuevo expediente",
    description: "Creación guiada de expediente fiscal defensivo.",
    noindex: true,
  });

  const upload = useDefensiaUpload(state.expedienteId ?? "pending");

  const puedeAvanzar = (): boolean => {
    switch (state.paso) {
      case 1:
        return state.tributo !== null && !state.creandoExpediente;
      case 2:
        return state.documentos.length > 0;
      case 3:
        return state.faseDetectada !== null;
      case 4:
        return state.brief.trim().length >= 30;
      case 5:
        return true;
      default:
        return false;
    }
  };

  const handleSiguiente = async () => {
    if (state.paso === 1 && state.tributo !== null) {
      dispatch({ type: "CREAR_START" });
      try {
        const res = await apiRequest<{ id: string }>(
          "/api/defensia/expedientes",
          {
            method: "POST",
            body: JSON.stringify({
              tributo: state.tributo,
              ccaa: state.ccaa,
              titulo: `${state.tributo} — ${new Date().toLocaleDateString("es-ES")}`,
            }),
          },
        );
        dispatch({ type: "CREAR_OK", id: res.id });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Error al crear expediente";
        dispatch({ type: "CREAR_ERROR", error: msg });
      }
      return;
    }

    if (state.paso === 5) {
      dispatch({ type: "NEXT" });
      if (state.expedienteId) {
        navigate(`/defensia/${state.expedienteId}`);
      }
      return;
    }

    dispatch({ type: "NEXT" });
  };

  const handleFileSelected = async (file: File) => {
    if (!state.expedienteId) return;
    const tempId = `tmp-${Date.now()}`;
    dispatch({
      type: "ADD_DOC",
      doc: {
        id: tempId,
        nombre: file.name,
        progreso: 0,
        estado: "subiendo",
      },
    });
    try {
      const res = await upload.upload(file, "OTROS");
      dispatch({ type: "REMOVE_DOC", id: tempId });
      dispatch({
        type: "ADD_DOC",
        doc: {
          id: res.id || tempId,
          nombre: file.name,
          progreso: 1,
          estado: "completado",
        },
      });
      // El backend ejecuta Fase 1 auto (classifier + extractor + phase
      // detector) durante el upload y devuelve fase_detectada en la
      // response. Si viene y es una fase real (no null ni INDETERMINADA),
      // la propagamos al reducer para que el paso 3 del wizard la muestre
      // sin necesidad de un nuevo round-trip.
      if (res.fase_detectada && res.fase_detectada !== "INDETERMINADA") {
        dispatch({ type: "SET_FASE", fase: res.fase_detectada });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al subir";
      dispatch({ type: "REMOVE_DOC", id: tempId });
      dispatch({
        type: "ADD_DOC",
        doc: {
          id: tempId,
          nombre: file.name,
          progreso: 0,
          estado: "error",
          error: msg,
        },
      });
    }
  };

  return (
    <div className="defensia-wizard-page">
      <header className="defensia-wizard-header">
        <Scale size={24} aria-hidden="true" />
        <h1>Nuevo expediente DefensIA</h1>
      </header>

      <DisclaimerBanner />

      <div className="defensia-wizard-steps" role="status">
        Paso {state.paso} de 5
      </div>

      <div className="defensia-wizard-body">
        {state.paso === 1 && (
          <section aria-labelledby="paso1-title">
            <h2 id="paso1-title">Selecciona el tributo</h2>
            <TributoSelect
              value={state.tributo}
              onChange={(t) => dispatch({ type: "SET_TRIBUTO", tributo: t })}
            />
          </section>
        )}

        {state.paso === 2 && (
          <section aria-labelledby="paso2-title">
            <h2 id="paso2-title">Sube los documentos del expediente</h2>
            <p className="defensia-wizard-hint">
              Liquidaciones, requerimientos, propuestas, resoluciones, escrituras…
            </p>
            <div className="defensia-wizard-uploads">
              {state.documentos.map((doc) => (
                <DocumentoUploadCard
                  key={doc.id}
                  documento={doc}
                  onRemove={(id) => dispatch({ type: "REMOVE_DOC", id })}
                />
              ))}
              <DocumentoUploadCard
                documento={null}
                onRemove={() => {}}
                onFileSelected={handleFileSelected}
              />
            </div>
          </section>
        )}

        {state.paso === 3 && (
          <section aria-labelledby="paso3-title">
            <h2 id="paso3-title">Fase procesal detectada</h2>
            {state.faseDetectada ? (
              <FaseBadge fase={state.faseDetectada} />
            ) : (
              <p className="defensia-wizard-hint">
                Analizando los documentos para detectar la fase procesal…
              </p>
            )}
          </section>
        )}

        {state.paso === 4 && (
          <section aria-labelledby="paso4-title">
            <h2 id="paso4-title">Describe tu caso (brief)</h2>
            <p className="defensia-wizard-hint">
              Explica con tus palabras qué ha pasado y qué buscas conseguir.
              DefensIA no arranca el análisis jurídico hasta leer este brief.
            </p>
            <textarea
              className="defensia-wizard-textarea"
              rows={8}
              placeholder="Ej: Hacienda me ha enviado una propuesta de liquidación de 3.200 EUR por…"
              value={state.brief}
              onChange={(e) => dispatch({ type: "SET_BRIEF", brief: e.target.value })}
            />
            <small className="defensia-wizard-count">
              {state.brief.trim().length} / mínimo 30 caracteres
            </small>
          </section>
        )}

        {state.paso === 5 && (
          <section aria-labelledby="paso5-title">
            <h2 id="paso5-title">Confirmación</h2>
            <p>Todo listo. Al pulsar "Analizar expediente" DefensIA comenzará:</p>
            <ol>
              <li>Aplicar las 30 reglas deterministas</li>
              <li>Verificar cada argumento contra el corpus RAG</li>
              <li>Redactar un dictamen con citas verificadas</li>
            </ol>
          </section>
        )}
      </div>

      {state.error && (
        <div className="defensia-wizard-error">{state.error}</div>
      )}

      <footer className="defensia-wizard-footer">
        <button
          type="button"
          className="defensia-wizard-prev"
          onClick={() => dispatch({ type: "PREV" })}
          disabled={state.paso === 1}
        >
          <ArrowLeft size={18} aria-hidden="true" />
          Atrás
        </button>
        <button
          type="button"
          className="defensia-wizard-next"
          onClick={() => void handleSiguiente()}
          disabled={!puedeAvanzar()}
        >
          {state.creandoExpediente && <Loader2 size={18} className="spin" />}
          {state.paso === 5 ? "Analizar expediente" : "Siguiente"}
          {!state.creandoExpediente && <ArrowRight size={18} aria-hidden="true" />}
        </button>
      </footer>
    </div>
  );
}

export default DefensiaWizardPage;
