import { useState, useEffect } from 'react';
import { Building2, AlertCircle, Info, CheckCircle, XCircle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../styles/CalculadoraUmbrales.css';

interface ThresholdDetail {
  valor: number;
  limite: number;
  supera: boolean;
  porcentaje: number;
}

interface CompanySizeResult {
  success: boolean;
  clasificacion: string;
  clasificacion_label: string;
  pgc_aplicable: string;
  pgc_detalle: string;
  balance_abreviado: boolean;
  memoria_abreviada: boolean;
  pyg_abreviada: boolean;
  auditoria_obligatoria: boolean;
  notas: string[];
  umbrales_clasificacion: Record<string, ThresholdDetail>;
  umbrales_auditoria: Record<string, ThresholdDetail>;
  umbrales_balance: Record<string, ThresholdDetail>;
  umbrales_pyg: Record<string, ThresholdDetail>;
  ejercicio_referencia: string;
  disclaimer: string;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

const fmt = (n: number) =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

const fmtEur = (n: number) =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' EUR';

function getBarClass(pct: number): string {
  if (pct <= 60) return 'safe';
  if (pct <= 90) return 'warning';
  return 'danger';
}

export default function CalculadoraUmbralesPage() {
  const [y1Activo, setY1Activo] = useState('');
  const [y1Negocios, setY1Negocios] = useState('');
  const [y1Empleados, setY1Empleados] = useState('');
  const [y2Activo, setY2Activo] = useState('');
  const [y2Negocios, setY2Negocios] = useState('');
  const [y2Empleados, setY2Empleados] = useState('');
  const [ejercicio, setEjercicio] = useState('2025');
  const [result, setResult] = useState<CompanySizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // SEO meta tags
  useEffect(() => {
    document.title = 'Calculadora de umbrales contables | Normal vs Abreviado | Impuestify';
    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute(
        'content',
        'Descubre si tu empresa puede usar el PGC PYMES, balance abreviado o si necesita auditoría. Basado en LSC Art. 257-258 y Directiva UE 2023/2775.'
      );
    }
  }, []);

  const calcular = async () => {
    if (!y1Activo || !y1Negocios || !y1Empleados || !y2Activo || !y2Negocios || !y2Empleados) {
      setError('Completa todos los campos de ambos ejercicios');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const resp = await fetch(`${API_BASE}/api/irpf/company-size`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year_1: {
            activo: parseFloat(y1Activo),
            negocios: parseFloat(y1Negocios),
            empleados: parseInt(y1Empleados),
          },
          year_2: {
            activo: parseFloat(y2Activo),
            negocios: parseFloat(y2Negocios),
            empleados: parseInt(y2Empleados),
          },
          ejercicio: parseInt(ejercicio),
        }),
      });
      const data = await resp.json();
      if (data.success) {
        setResult(data);
      } else {
        setError(data.detail || 'Error en el calculo');
      }
    } catch {
      setError('Error de conexion. Intentalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const renderBars = (
    title: string,
    thresholds: Record<string, ThresholdDetail> | undefined,
  ) => {
    if (!thresholds) return null;
    const labels: Record<string, string> = {
      activo: 'Activo total',
      negocios: 'Cifra de negocios',
      empleados: 'Empleados',
    };
    return (
      <div className="calc-umb-bars">
        <h4>{title}</h4>
        {Object.entries(thresholds).map(([key, detail]) => {
          const pct = Math.min(detail.porcentaje, 100);
          const isEmployees = key === 'empleados';
          return (
            <div key={key} className="calc-umb-bar-item">
              <div className="calc-umb-bar-label">
                <span>{labels[key] || key}</span>
                <strong>
                  {isEmployees ? fmt(detail.valor) : fmtEur(detail.valor)} / {isEmployees ? fmt(detail.limite) : fmtEur(detail.limite)}
                </strong>
              </div>
              <div className="calc-umb-bar-track">
                <div
                  className={`calc-umb-bar-fill ${getBarClass(detail.porcentaje)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="calc-umb-page">
      <div className="calc-umb-container">
        <Link to="/" className="calc-back-link">
          <ArrowLeft size={16} /> Volver a inicio
        </Link>
        <div className="calc-umb-header">
          <Building2 size={32} />
          <div>
            <h1>Calculadora de Umbrales Contables</h1>
            <p>Descubre si tu empresa puede usar PGC PYMES, balance abreviado o si necesita auditoría</p>
          </div>
        </div>

        <div className="calc-umb-grid">
          {/* FORMULARIO */}
          <div className="calc-umb-form">
            <div className="calc-umb-section">
              <h3>Ejercicio de referencia</h3>
              <label>Normativa aplicable</label>
              <select
                value={ejercicio}
                onChange={e => setEjercicio(e.target.value)}
                className="calc-umb-select"
              >
                <option value="2025">2025 (umbrales actuales LSC)</option>
                <option value="2026">2026+ (Directiva UE 2023/2775)</option>
              </select>
            </div>

            <div className="calc-umb-section">
              <h3>Datos financieros (2 ejercicios consecutivos)</h3>
              <div className="calc-umb-years">
                <div className="calc-umb-year-col">
                  <h4>Ejercicio N-1</h4>
                  <label>Activo total (EUR)</label>
                  <input
                    type="number"
                    value={y1Activo}
                    onChange={e => setY1Activo(e.target.value)}
                    placeholder="Ej: 2000000"
                    className="calc-umb-input"
                    min="0"
                  />
                  <label>Cifra de negocios (EUR)</label>
                  <input
                    type="number"
                    value={y1Negocios}
                    onChange={e => setY1Negocios(e.target.value)}
                    placeholder="Ej: 5000000"
                    className="calc-umb-input"
                    min="0"
                  />
                  <label>Empleados (media anual)</label>
                  <input
                    type="number"
                    value={y1Empleados}
                    onChange={e => setY1Empleados(e.target.value)}
                    placeholder="Ej: 30"
                    className="calc-umb-input"
                    min="0"
                  />
                </div>

                <div className="calc-umb-year-col">
                  <h4>Ejercicio N</h4>
                  <label>Activo total (EUR)</label>
                  <input
                    type="number"
                    value={y2Activo}
                    onChange={e => setY2Activo(e.target.value)}
                    placeholder="Ej: 2500000"
                    className="calc-umb-input"
                    min="0"
                  />
                  <label>Cifra de negocios (EUR)</label>
                  <input
                    type="number"
                    value={y2Negocios}
                    onChange={e => setY2Negocios(e.target.value)}
                    placeholder="Ej: 6000000"
                    className="calc-umb-input"
                    min="0"
                  />
                  <label>Empleados (media anual)</label>
                  <input
                    type="number"
                    value={y2Empleados}
                    onChange={e => setY2Empleados(e.target.value)}
                    placeholder="Ej: 35"
                    className="calc-umb-input"
                    min="0"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="calc-umb-error">
                <AlertCircle size={16} /> {error}
              </div>
            )}

            <button onClick={calcular} disabled={loading} className="calc-umb-submit">
              {loading ? 'Calculando...' : 'Clasificar empresa'}
            </button>
          </div>

          {/* RESULTADO */}
          <div className="calc-umb-result">
            {result ? (
              <>
                <div className="calc-umb-badge-wrap">
                  <span className={`calc-umb-badge ${result.clasificacion}`}>
                    {result.clasificacion_label}
                  </span>
                  <span className="calc-umb-badge-label">{result.pgc_aplicable}</span>
                </div>

                <div className="calc-umb-summary">
                  <div className="calc-umb-summary-item">
                    <span>PGC aplicable</span>
                    <strong>{result.pgc_aplicable.split(' (')[0]}</strong>
                  </div>
                  <div className="calc-umb-summary-item">
                    <span>Balance abreviado</span>
                    <strong className={result.balance_abreviado ? 'si' : 'no'}>
                      {result.balance_abreviado ? 'Si' : 'No'}
                    </strong>
                  </div>
                  <div className="calc-umb-summary-item">
                    <span>Memoria abreviada</span>
                    <strong className={result.memoria_abreviada ? 'si' : 'no'}>
                      {result.memoria_abreviada ? 'Si' : 'No'}
                    </strong>
                  </div>
                  <div className="calc-umb-summary-item">
                    <span>PyG abreviada</span>
                    <strong className={result.pyg_abreviada ? 'si' : 'no'}>
                      {result.pyg_abreviada ? 'Si' : 'No'}
                    </strong>
                  </div>
                  <div className="calc-umb-summary-item">
                    <span>Auditoría obligatoria</span>
                    <strong className={result.auditoria_obligatoria ? 'audit-si' : 'si'}>
                      {result.auditoria_obligatoria ? 'Sí' : 'No'}
                    </strong>
                  </div>
                </div>

                {renderBars('Umbrales de clasificación', result.umbrales_clasificacion)}
                {renderBars('Umbrales de auditoría (Art. 263 LSC)', result.umbrales_auditoria)}

                {result.notas && result.notas.length > 0 && (
                  <div className="calc-umb-notes">
                    <h4>Observaciones</h4>
                    {result.notas.map((nota, i) => (
                      <div key={i} className="calc-umb-note">
                        <Info size={14} />
                        <span>{nota}</span>
                      </div>
                    ))}
                  </div>
                )}

                <p className="calc-umb-disclaimer">{result.disclaimer}</p>

                <div className="calc-umb-cta">
                  <p>¿Necesitas ayuda con la contabilidad de tu empresa?</p>
                  <a href="/contact" className="calc-umb-cta-btn">Contactar con un asesor</a>
                </div>
              </>
            ) : (
              <div className="calc-umb-placeholder">
                <Building2 size={48} />
                <p>Introduce los datos financieros de los 2 últimos ejercicios y pulsa "Clasificar empresa"</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
