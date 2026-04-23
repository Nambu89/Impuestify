import { useReducer, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Loader2, Scale } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useDefensiaUpload } from "../hooks/useDefensiaUpload";
import { useDefensiaAnalyze } from "../hooks/useDefensiaAnalyze";
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
  const { analyze, analyzing, error: analyzeError } = useDefensiaAnalyze();
  const [analyzeStatus, setAnalyzeStatus] = useState<string | null>(null);

  useSEO({
    title: "Nuevo expediente — DefensIA",
    description: "Asistente paso a paso para abrir un expediente de defensa frente a Hacienda.",
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
              nombre: `${state.tributo} — ${new Date().toLocaleDateString("es-ES")}`,
              tributo: state.tributo,
              ccaa: state.ccaa,
              tipo_procedimiento_declarado: "comprobacion_limitada",
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

    // Paso 4 -> 5: persistir el brief antes de avanzar a la confirmacion.
    // Sin este POST, el analyze del paso 5 fallaria con 400 (brief vacio).
    if (state.paso === 4 && state.expedienteId) {
      try {
        await apiRequest(
          `/api/defensia/expedientes/${state.expedienteId}/brief`,
          {
            method: "POST",
            body: JSON.stringify({ texto: state.brief }),
          },
        );
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Error al guardar el brief";
        dispatch({ type: "CREAR_ERROR", error: msg });
        return;
      }
      dispatch({ type: "NEXT" });
      return;
    }

    // Paso 5 -> dispara el analyze SSE. Mientras corre mostramos progreso
    // textual. onDone navega al expediente, donde ExpedientePage muestra
    // el dictamen + escrito ya persistidos por el backend.
    if (state.paso === 5 && state.expedienteId) {
      setAnalyzeStatus("Preparando el análisis…");
      let doneFired = false;
      try {
        await analyze(state.expedienteId, {
          onPhase: () => setAnalyzeStatus("Detectando la fase procesal…"),
          onCandidatos: (d) =>
            setAnalyzeStatus(
              `Aplicando reglas (${d.count} candidatos)…`,
            ),
          onVerificando: () =>
            setAnalyzeStatus("Verificando argumentos contra el corpus normativo…"),
          onDictamen: () => setAnalyzeStatus("Redactando el dictamen…"),
          onEscrito: () => setAnalyzeStatus("Redactando el escrito de alegaciones…"),
          onDone: () => {
            doneFired = true;
            setAnalyzeStatus(null);
            navigate(`/defensia/${state.expedienteId}`);
          },
        });
      } finally {
        // Si analyze() termino sin disparar onDone (error HTTP, abort, stream
        // cortado), limpiamos el status para que la UI no quede mostrando
        // el bloque de "Analizando..." con analyzing=false. El error visible
        // sigue viniendo de analyzeError.
        if (!doneFired) {
          setAnalyzeStatus(null);
        }
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
      // response. Siempre propagamos el valor (incluido INDETERMINADA)
      // para no bloquear el paso 3 del wizard cuando la extraccion
      // best-effort falla o los documentos subidos no permiten decidir
      // la fase con confianza — la UI mostrara el badge gris y el usuario
      // podra seguir a paso 4.
      if (res.fase_detectada) {
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
      <Link to="/" className="defensia-back-link">
        <ArrowLeft size={16} aria-hidden="true" /> Volver a inicio
      </Link>
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
              <>
                <FaseBadge fase={state.faseDetectada} />
                {state.faseDetectada === "INDETERMINADA" && (
                  <p className="defensia-wizard-hint">
                    Con los documentos subidos no podemos fijar la fase. Puedes
                    continuar y describir el caso en el paso siguiente; el
                    motor intentará deducirla del brief.
                  </p>
                )}
              </>
            ) : (
              <p className="defensia-wizard-hint">
                Leyendo los documentos para detectar la fase procesal…
              </p>
            )}
          </section>
        )}

        {state.paso === 4 && (
          <section aria-labelledby="paso4-title">
            <h2 id="paso4-title">Describe tu caso (brief)</h2>
            <p className="defensia-wizard-hint">
              Cuéntanos con tus palabras qué ha pasado y qué quieres conseguir.
              DefensIA no empieza el análisis jurídico hasta leer este brief.
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
            {!analyzing && !analyzeStatus && (
              <>
                <p>
                  Al pulsar "Analizar expediente" DefensIA hará lo siguiente:
                </p>
                <ol>
                  <li>Aplicar las reglas deterministas al caso.</li>
                  <li>Verificar cada argumento contra el corpus normativo.</li>
                  <li>Redactar un dictamen con las citas ya comprobadas.</li>
                </ol>
              </>
            )}
            {(analyzing || analyzeStatus) && (
              <div className="defensia-wizard-analyzing" role="status">
                <Loader2 size={20} className="spin" aria-hidden="true" />
                <span>{analyzeStatus || "Analizando el expediente…"}</span>
              </div>
            )}
            {analyzeError && !analyzing && (
              <div className="defensia-wizard-error">{analyzeError}</div>
            )}
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
          disabled={state.paso === 1 || analyzing}
        >
          <ArrowLeft size={18} aria-hidden="true" />
          Atrás
        </button>
        <button
          type="button"
          className="defensia-wizard-next"
          onClick={() => void handleSiguiente()}
          disabled={!puedeAvanzar() || analyzing}
        >
          {(state.creandoExpediente || analyzing) && (
            <Loader2 size={18} className="spin" />
          )}
          {state.paso === 5 ? "Analizar expediente" : "Siguiente"}
          {!state.creandoExpediente && !analyzing && (
            <ArrowRight size={18} aria-hidden="true" />
          )}
        </button>
      </footer>
    </div>
  );
}

export default DefensiaWizardPage;
