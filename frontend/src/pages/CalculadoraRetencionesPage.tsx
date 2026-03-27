import { useState } from 'react';
import { Calculator, ChevronDown, ChevronUp, Plus, Trash2, AlertCircle } from 'lucide-react';
import '../styles/CalculadoraRetenciones.css';

interface Descendiente {
  ano_nacimiento: number;
  por_entero: boolean;
  discapacidad: string;
}

interface WithholdingResult {
  success: boolean;
  tipo_retencion: number;
  cuota_anual: number;
  retencion_mensual: number;
  salario_neto_mensual: number;
  retribucion_bruta: number;
  cotizaciones_ss: number;
  gastos_deducibles: number;
  rendimiento_neto_reducido: number;
  minimo_personal_familiar: number;
  base_retencion: number;
  exento: boolean;
  motivo_exencion?: string;
  disclaimer: string;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function CalculadoraRetencionesPage() {
  const [salarioBruto, setSalarioBruto] = useState('');
  const [numPagas, setNumPagas] = useState('14');
  const [situacionFamiliar, setSituacionFamiliar] = useState('3');
  const [situacionLaboral, setSituacionLaboral] = useState('activo');
  const [tipoContrato, setTipoContrato] = useState('indefinido');
  const [anoNacimiento, setAnoNacimiento] = useState('1990');
  const [discapacidad, setDiscapacidad] = useState('sin');
  const [ceutaMelilla, setCeutaMelilla] = useState(false);
  const [hipoteca, setHipoteca] = useState(false);
  const [descendientes, setDescendientes] = useState<Descendiente[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [result, setResult] = useState<WithholdingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const calcular = async () => {
    if (!salarioBruto || parseFloat(salarioBruto) <= 0) {
      setError('Introduce tu salario bruto anual');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const resp = await fetch(`${API_BASE}/api/irpf/withholding`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          retribucion_bruta_anual: parseFloat(salarioBruto),
          situacion_familiar: situacionFamiliar,
          situacion_laboral: situacionLaboral,
          tipo_contrato: tipoContrato,
          ano_nacimiento: parseInt(anoNacimiento),
          discapacidad,
          ceuta_melilla: ceutaMelilla,
          hipoteca_pre2013: hipoteca,
          num_pagas: parseInt(numPagas),
          descendientes: descendientes.map(d => ({
            ano_nacimiento: d.ano_nacimiento,
            por_entero: d.por_entero,
            discapacidad: d.discapacidad,
          })),
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

  const addHijo = () => {
    setDescendientes([...descendientes, { ano_nacimiento: 2020, por_entero: true, discapacidad: 'sin' }]);
  };

  const removeHijo = (idx: number) => {
    setDescendientes(descendientes.filter((_, i) => i !== idx));
  };

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <div className="calc-ret-page">
      <div className="calc-ret-container">
        <div className="calc-ret-header">
          <Calculator size={32} />
          <div>
            <h1>Calculadora de Retenciones IRPF 2026</h1>
            <p>Calcula tu tipo de retención según el algoritmo oficial de la AEAT</p>
          </div>
        </div>

        <div className="calc-ret-grid">
          {/* FORMULARIO */}
          <div className="calc-ret-form">
            <div className="calc-ret-section">
              <h3>Datos básicos</h3>

              <label>Salario bruto anual (EUR)</label>
              <input
                type="number"
                value={salarioBruto}
                onChange={e => setSalarioBruto(e.target.value)}
                placeholder="Ej: 25000"
                className="calc-ret-input"
              />

              <div className="calc-ret-row">
                <div>
                  <label>Pagas</label>
                  <select value={numPagas} onChange={e => setNumPagas(e.target.value)} className="calc-ret-select">
                    <option value="12">12 pagas</option>
                    <option value="14">14 pagas</option>
                  </select>
                </div>
                <div>
                  <label>Contrato</label>
                  <select value={tipoContrato} onChange={e => setTipoContrato(e.target.value)} className="calc-ret-select">
                    <option value="indefinido">Indefinido</option>
                    <option value="temporal">Temporal</option>
                  </select>
                </div>
              </div>

              <label>Situación familiar</label>
              <select value={situacionFamiliar} onChange={e => setSituacionFamiliar(e.target.value)} className="calc-ret-select">
                <option value="3">Soltero/a sin hijos a cargo, o casado/a (cónyuge con rentas {'>'} 1.500 EUR)</option>
                <option value="1">Soltero/a, viudo/a o divorciado/a con hijos a cargo</option>
                <option value="2">Casado/a (cónyuge sin rentas o {'<'} 1.500 EUR)</option>
              </select>

              <div className="calc-ret-row">
                <div>
                  <label>Año de nacimiento</label>
                  <input type="number" value={anoNacimiento} onChange={e => setAnoNacimiento(e.target.value)} className="calc-ret-input" />
                </div>
                <div>
                  <label>Situación laboral</label>
                  <select value={situacionLaboral} onChange={e => setSituacionLaboral(e.target.value)} className="calc-ret-select">
                    <option value="activo">Trabajador activo</option>
                    <option value="pensionista">Pensionista</option>
                    <option value="desempleado">Desempleado</option>
                  </select>
                </div>
              </div>
            </div>

            {/* HIJOS */}
            <div className="calc-ret-section">
              <div className="calc-ret-section-header">
                <h3>Hijos a cargo</h3>
                <button onClick={addHijo} className="calc-ret-add-btn"><Plus size={16} /> Añadir hijo</button>
              </div>
              {descendientes.map((d, i) => (
                <div key={i} className="calc-ret-hijo-row">
                  <span>Hijo {i + 1}</span>
                  <input
                    type="number"
                    value={d.ano_nacimiento}
                    onChange={e => {
                      const updated = [...descendientes];
                      updated[i].ano_nacimiento = parseInt(e.target.value);
                      setDescendientes(updated);
                    }}
                    placeholder="Año nacimiento"
                    className="calc-ret-input-sm"
                  />
                  <label className="calc-ret-checkbox">
                    <input
                      type="checkbox"
                      checked={d.por_entero}
                      onChange={e => {
                        const updated = [...descendientes];
                        updated[i].por_entero = e.target.checked;
                        setDescendientes(updated);
                      }}
                    />
                    100%
                  </label>
                  <button onClick={() => removeHijo(i)} className="calc-ret-del-btn"><Trash2 size={14} /></button>
                </div>
              ))}
              {descendientes.length === 0 && <p className="calc-ret-hint">Sin hijos a cargo</p>}
            </div>

            {/* AVANZADO */}
            <button onClick={() => setShowAdvanced(!showAdvanced)} className="calc-ret-toggle">
              {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              Opciones avanzadas
            </button>
            {showAdvanced && (
              <div className="calc-ret-section">
                <label>Discapacidad del trabajador</label>
                <select value={discapacidad} onChange={e => setDiscapacidad(e.target.value)} className="calc-ret-select">
                  <option value="sin">Sin discapacidad</option>
                  <option value="33-65">33% - 65%</option>
                  <option value="65+">65% o superior</option>
                </select>
                <div className="calc-ret-checks">
                  <label className="calc-ret-checkbox">
                    <input type="checkbox" checked={ceutaMelilla} onChange={e => setCeutaMelilla(e.target.checked)} />
                    Residente en Ceuta o Melilla
                  </label>
                  <label className="calc-ret-checkbox">
                    <input type="checkbox" checked={hipoteca} onChange={e => setHipoteca(e.target.checked)} />
                    Hipoteca vivienda habitual (anterior a 2013)
                  </label>
                </div>
              </div>
            )}

            {error && <div className="calc-ret-error"><AlertCircle size={16} /> {error}</div>}

            <button onClick={calcular} disabled={loading} className="calc-ret-submit">
              {loading ? 'Calculando...' : 'Calcular retención'}
            </button>
          </div>

          {/* RESULTADO */}
          <div className="calc-ret-result">
            {result ? (
              <>
                <div className={`calc-ret-big-number ${result.exento ? 'exento' : ''}`}>
                  <span className="calc-ret-percentage">{result.tipo_retencion.toFixed(2)}%</span>
                  <span className="calc-ret-label">Tipo de retención IRPF</span>
                </div>

                {result.exento && (
                  <div className="calc-ret-exento-badge">
                    Exento de retención: {result.motivo_exencion}
                  </div>
                )}

                <div className="calc-ret-summary">
                  <div className="calc-ret-summary-item">
                    <span>Retención mensual</span>
                    <strong>{fmt(result.retencion_mensual)} EUR</strong>
                  </div>
                  <div className="calc-ret-summary-item">
                    <span>Retención anual</span>
                    <strong>{fmt(result.cuota_anual)} EUR</strong>
                  </div>
                  <div className="calc-ret-summary-item highlight">
                    <span>Salario neto mensual</span>
                    <strong>{fmt(result.salario_neto_mensual)} EUR</strong>
                  </div>
                </div>

                <details className="calc-ret-details">
                  <summary>Ver desglose completo</summary>
                  <table className="calc-ret-table">
                    <tbody>
                      <tr><td>Salario bruto anual</td><td>{fmt(result.retribucion_bruta)} EUR</td></tr>
                      <tr><td>Cotizaciones Seguridad Social</td><td>-{fmt(result.cotizaciones_ss)} EUR</td></tr>
                      <tr><td>Gastos deducibles totales</td><td>-{fmt(result.gastos_deducibles)} EUR</td></tr>
                      <tr><td>Rendimiento neto reducido</td><td>{fmt(result.rendimiento_neto_reducido)} EUR</td></tr>
                      <tr><td>Mínimo personal y familiar</td><td>{fmt(result.minimo_personal_familiar)} EUR</td></tr>
                      <tr><td>Base para retención</td><td>{fmt(result.base_retencion)} EUR</td></tr>
                    </tbody>
                  </table>
                </details>

                <p className="calc-ret-disclaimer">{result.disclaimer}</p>

                <div className="calc-ret-cta">
                  <p>¿Quieres saber cuánto te devuelve Hacienda?</p>
                  <a href="/guia-fiscal" className="calc-ret-cta-btn">Usar la Guía Fiscal completa</a>
                </div>
              </>
            ) : (
              <div className="calc-ret-placeholder">
                <Calculator size={48} />
                <p>Introduce tus datos y pulsa "Calcular retención" para ver tu resultado</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
