import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FileText, ArrowLeft, Calculator } from 'lucide-react'
import Header from '../components/Header'
import { useSEO } from '../hooks/useSEO'
import { CCAA_OPTIONS } from '../constants/ccaa'
import './Modelo202Page.css'

/* ============================================================
   Local calculation — no backend needed for 202
   ============================================================ */

type Modalidad = 'art40_2' | 'art40_3'

const fmtEur = (n: number): string =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' EUR'

function calcArt40_2(cuotaIntegra: number, deducciones: number, retenciones: number): number {
  // 18% x (cuota integra - deducciones - bonificaciones - retenciones)
  const base = cuotaIntegra - deducciones - retenciones
  return Math.max(base * 0.18, 0)
}

function calcArt40_3(
  baseImponible3m: number,
  baseImponible9m: number,
  baseImponible11m: number,
  pagoPrevio1: number,
  pagoPrevio2: number,
  tipoGravamen: number
): { p1: number; p2: number; p3: number } {
  // Porcentaje: 5/7 del tipo gravamen
  const pct = (5 / 7) * tipoGravamen
  const p1 = Math.max(baseImponible3m * pct - 0, 0)
  const p2 = Math.max(baseImponible9m * pct - pagoPrevio1, 0)
  const p3 = Math.max(baseImponible11m * pct - pagoPrevio1 - pagoPrevio2, 0)
  return { p1, p2, p3 }
}

export default function Modelo202Page() {
  const [modalidad, setModalidad] = useState<Modalidad>('art40_2')
  const [territorio, setTerritorio] = useState('')

  // Art 40.2 inputs
  const [cuotaIntegra, setCuotaIntegra] = useState(0)
  const [deducciones, setDeducciones] = useState(0)
  const [retenciones, setRetenciones] = useState(0)

  // Art 40.3 inputs
  const [bi3m, setBi3m] = useState(0)
  const [bi9m, setBi9m] = useState(0)
  const [bi11m, setBi11m] = useState(0)
  const [tipoGravamen, setTipoGravamen] = useState(25)

  const [calculated, setCalculated] = useState(false)

  useSEO({
    title: 'Pagos fraccionados del IS (Modelo 202) — Impuestify',
    description: 'Calcula los pagos fraccionados del Impuesto sobre Sociedades por el Art. 40.2 (sobre cuota del ejercicio anterior) o por el Art. 40.3 (sobre base imponible del ejercicio).',
    canonical: '/modelo-202',
    keywords: 'modelo 202, pagos fraccionados, IS, impuesto sociedades, Art 40.2, Art 40.3',
  })

  const result40_2 = useMemo(() => {
    if (modalidad !== 'art40_2') return null
    const pago = calcArt40_2(cuotaIntegra, deducciones, retenciones)
    return { pago, total: pago * 3 }
  }, [modalidad, cuotaIntegra, deducciones, retenciones])

  const result40_3 = useMemo(() => {
    if (modalidad !== 'art40_3') return null
    const { p1, p2, p3 } = calcArt40_3(bi3m, bi9m, bi11m, 0, 0, tipoGravamen / 100)
    return { p1, p2, p3, total: p1 + p2 + p3 }
  }, [modalidad, bi3m, bi9m, bi11m, tipoGravamen])

  const handleCalc = () => setCalculated(true)

  const canCalc = territorio && (
    modalidad === 'art40_2'
      ? cuotaIntegra > 0
      : (bi3m > 0 || bi9m > 0 || bi11m > 0)
  )

  return (
    <div className="m202-page">
      <Header />
      <div className="m202-container">
        <Link to="/modelo-200" className="m202-back">
          <ArrowLeft size={16} /> Volver al Modelo 200
        </Link>

        <div className="m202-header">
          <FileText size={36} />
          <h1>Modelo 202 &mdash; Pagos fraccionados IS</h1>
          <p>Estima los tres pagos a cuenta (abril, octubre y diciembre) bajo las modalidades del Art. 40.2 y Art. 40.3 LIS.</p>
        </div>

        <div className="m202-card">
          <h2><Calculator size={18} /> Configuraci&oacute;n</h2>

          <div className="m202-field">
            <label className="m202-field__label">Territorio fiscal</label>
            <select
              className="m202-field__select"
              value={territorio}
              onChange={e => { setTerritorio(e.target.value); setCalculated(false) }}
            >
              <option value="">Selecciona territorio</option>
              {CCAA_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="m202-field">
            <label className="m202-field__label">Modalidad de c&aacute;lculo</label>
            <div className="m202-tabs">
              <button
                className={`m202-tab${modalidad === 'art40_2' ? ' m202-tab--active' : ''}`}
                onClick={() => { setModalidad('art40_2'); setCalculated(false) }}
              >
                Art. 40.2 (sobre cuota)
              </button>
              <button
                className={`m202-tab${modalidad === 'art40_3' ? ' m202-tab--active' : ''}`}
                onClick={() => { setModalidad('art40_3'); setCalculated(false) }}
              >
                Art. 40.3 (sobre base)
              </button>
            </div>
            <span className="m202-field__help">
              {modalidad === 'art40_2'
                ? 'Modalidad por defecto: 18% sobre (cuota \u00edntegra \u2212 deducciones \u2212 retenciones) del \u00faltimo ejercicio.'
                : 'Obligatorio si facturaci\u00f3n > 6M EUR: porcentaje sobre base imponible del per\u00edodo.'}
            </span>
          </div>

          {modalidad === 'art40_2' && (
            <>
              <div className="m202-field">
                <label className="m202-field__label">Cuota &iacute;ntegra del &uacute;ltimo ejercicio</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={cuotaIntegra || ''}
                    onChange={e => { setCuotaIntegra(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
              </div>

              <div className="m202-field">
                <label className="m202-field__label">Deducciones y bonificaciones aplicadas</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={deducciones || ''}
                    onChange={e => { setDeducciones(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
              </div>

              <div className="m202-field">
                <label className="m202-field__label">Retenciones e ingresos a cuenta</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={retenciones || ''}
                    onChange={e => { setRetenciones(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
              </div>
            </>
          )}

          {modalidad === 'art40_3' && (
            <>
              <div className="m202-field">
                <label className="m202-field__label">Tipo gravamen aplicable (%)</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={tipoGravamen || ''}
                    onChange={e => { setTipoGravamen(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    max={100}
                    step={0.5}
                    inputMode="decimal"
                    placeholder="25"
                  />
                  <span className="m202-field__suffix">%</span>
                </div>
                <span className="m202-field__help">General: 25%. Pymes reducido: 23%. Nueva creaci&oacute;n: 15%.</span>
              </div>

              <div className="m202-field">
                <label className="m202-field__label">Base imponible acumulada 3 primeros meses</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={bi3m || ''}
                    onChange={e => { setBi3m(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
                <span className="m202-field__help">Pago de abril (1P): base ene-mar</span>
              </div>

              <div className="m202-field">
                <label className="m202-field__label">Base imponible acumulada 9 primeros meses</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={bi9m || ''}
                    onChange={e => { setBi9m(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
                <span className="m202-field__help">Pago de octubre (2P): base ene-sep</span>
              </div>

              <div className="m202-field">
                <label className="m202-field__label">Base imponible acumulada 11 primeros meses</label>
                <div className="m202-field__input-wrap">
                  <input
                    type="number"
                    className="m202-field__input"
                    value={bi11m || ''}
                    onChange={e => { setBi11m(parseFloat(e.target.value) || 0); setCalculated(false) }}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m202-field__suffix">EUR</span>
                </div>
                <span className="m202-field__help">Pago de diciembre (3P): base ene-nov</span>
              </div>
            </>
          )}

          <button
            className="m202-submit"
            onClick={handleCalc}
            disabled={!canCalc}
          >
            Calcular pagos fraccionados
          </button>
        </div>

        {/* Results */}
        {calculated && modalidad === 'art40_2' && result40_2 && (
          <div className="m202-result">
            <h3>Pagos fraccionados Modelo 202 (Art. 40.2)</h3>
            <div className="m202-result-row">
              <span className="m202-result-label">1P &mdash; Abril (1-20)</span>
              <span className="m202-result-amount">{fmtEur(result40_2.pago)}</span>
            </div>
            <div className="m202-result-row">
              <span className="m202-result-label">2P &mdash; Octubre (1-20)</span>
              <span className="m202-result-amount">{fmtEur(result40_2.pago)}</span>
            </div>
            <div className="m202-result-row">
              <span className="m202-result-label">3P &mdash; Diciembre (1-20)</span>
              <span className="m202-result-amount">{fmtEur(result40_2.pago)}</span>
            </div>
            <div className="m202-result-row m202-result-total">
              <span className="m202-result-label">Total anual pagos a cuenta</span>
              <span className="m202-result-amount">{fmtEur(result40_2.total)}</span>
            </div>
            <p className="m202-disclaimer">
              Estimaci&oacute;n orientativa. Bajo el Art. 40.2 LIS los tres pagos son iguales (18% sobre la base de c&aacute;lculo del &uacute;ltimo ejercicio cerrado). Revisa los importes con tu asesor antes de presentar cada modelo.
            </p>
          </div>
        )}

        {calculated && modalidad === 'art40_3' && result40_3 && (
          <div className="m202-result">
            <h3>Pagos fraccionados Modelo 202 (Art. 40.3)</h3>
            <div className="m202-result-row">
              <span className="m202-result-label">1P &mdash; Abril (ene-mar)</span>
              <span className="m202-result-amount">{fmtEur(result40_3.p1)}</span>
            </div>
            <div className="m202-result-row">
              <span className="m202-result-label">2P &mdash; Octubre (ene-sep)</span>
              <span className="m202-result-amount">{fmtEur(result40_3.p2)}</span>
            </div>
            <div className="m202-result-row">
              <span className="m202-result-label">3P &mdash; Diciembre (ene-nov)</span>
              <span className="m202-result-amount">{fmtEur(result40_3.p3)}</span>
            </div>
            <div className="m202-result-row m202-result-total">
              <span className="m202-result-label">Total anual pagos a cuenta</span>
              <span className="m202-result-amount">{fmtEur(result40_3.total)}</span>
            </div>
            <p className="m202-disclaimer">
              Estimaci&oacute;n orientativa. Art. 40.3 LIS: porcentaje = 5/7 del tipo de gravamen. Obligatorio para entidades con INCN &gt; 6M EUR en el ejercicio anterior. Contrasta las bases acumuladas con tu asesor antes de presentar cada pago.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
