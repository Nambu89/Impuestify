import { useReducer, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, ChevronLeft, ChevronRight, CheckCircle,
  Info, AlertCircle, Loader2, ArrowLeft, Download, FileText
} from 'lucide-react'
import Header from '../components/Header'
import ISResultCard from '../components/ISResultCard'
import { useIsEstimator } from '../hooks/useIsEstimator'
import { useIsPrefill } from '../hooks/useIsPrefill'
import { useWorkspaces } from '../hooks/useWorkspaces'
import { useAuth } from '../hooks/useAuth'
import { useSEO } from '../hooks/useSEO'
import { CCAA_OPTIONS } from '../constants/ccaa'
import type { TipoEntidad, ISEstimateInput } from '../types/is'
import './Modelo200Page.css'

/* ============================================================
   State management
   ============================================================ */

interface WizardState {
  step: number
  // Paso 1
  tipo_entidad: TipoEntidad
  territorio: string
  facturacion_anual: number
  ejercicio: number
  workspace_id: string
  es_zec: boolean
  // Paso 2
  ingresos_explotacion: number
  gastos_explotacion: number
  resultado_contable: number
  amortizacion_contable: number
  amortizacion_fiscal: number
  // Paso 3
  gastos_no_deducibles: number
  bins_pendientes: number
  gasto_id: number
  gasto_it: number
  incremento_ffpp: number
  donativos: number
  empleados_discapacidad_33: number
  empleados_discapacidad_65: number
  dotacion_ric: number
  rentas_ceuta_melilla: number
  retenciones_ingresos_cuenta: number
  pagos_fraccionados_realizados: number
}

type Action =
  | { type: 'SET_FIELD'; field: keyof WizardState; value: any }
  | { type: 'SET_STEP'; step: number }
  | { type: 'PREFILL'; data: Partial<WizardState> }
  | { type: 'RESET' }

const initialState: WizardState = {
  step: 0,
  tipo_entidad: 'sl',
  territorio: '',
  facturacion_anual: 0,
  ejercicio: 2025,
  workspace_id: '',
  es_zec: false,
  ingresos_explotacion: 0,
  gastos_explotacion: 0,
  resultado_contable: 0,
  amortizacion_contable: 0,
  amortizacion_fiscal: 0,
  gastos_no_deducibles: 0,
  bins_pendientes: 0,
  gasto_id: 0,
  gasto_it: 0,
  incremento_ffpp: 0,
  donativos: 0,
  empleados_discapacidad_33: 0,
  empleados_discapacidad_65: 0,
  dotacion_ric: 0,
  rentas_ceuta_melilla: 0,
  retenciones_ingresos_cuenta: 0,
  pagos_fraccionados_realizados: 0,
}

function reducer(state: WizardState, action: Action): WizardState {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value }
    case 'SET_STEP':
      return { ...state, step: action.step }
    case 'PREFILL':
      return { ...state, ...action.data }
    case 'RESET':
      return { ...initialState }
    default:
      return state
  }
}

/* ============================================================
   Helpers
   ============================================================ */

const STEP_LABELS = ['Entidad', 'Resultado contable', 'Ajustes', 'Resultado']

const TIPO_ENTIDAD_OPTIONS: { value: TipoEntidad; label: string }[] = [
  { value: 'sl', label: 'Sociedad Limitada (SL)' },
  { value: 'slp', label: 'Sociedad Limitada Profesional (SLP)' },
  { value: 'sa', label: 'Sociedad An\u00f3nima (SA)' },
  { value: 'nueva_creacion', label: 'Nueva creaci\u00f3n (2 primeros ejercicios)' },
]

const fmtEur = (n: number): string =>
  n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' EUR'

/* ============================================================
   Component
   ============================================================ */

export default function Modelo200Page() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const { isAuthenticated } = useAuth()
  const { result, loading: estimating, error: estError, estimate, reset: resetEstimate } = useIsEstimator()
  const { data: prefillData, loading: prefilling, prefill, reset: resetPrefill } = useIsPrefill()
  const { workspaces, fetchWorkspaces } = useWorkspaces()

  useSEO({
    title: 'Modelo 200 \u2014 Simulador Impuesto sobre Sociedades | Impuestify',
    description: 'Calcula el Impuesto sobre Sociedades (IS) de tu empresa. Simulador Modelo 200 con tipo reducido para pymes, nueva creaci\u00f3n, deducciones I+D+i, BINs y pagos fraccionados Modelo 202.',
    canonical: '/modelo-200',
    keywords: 'modelo 200, impuesto sociedades, IS, pyme, SL, simulador, deducciones I+D, BINs, modelo 202',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: 'Simulador Modelo 200 \u2014 Impuesto sobre Sociedades',
      applicationCategory: 'FinanceApplication',
      operatingSystem: 'Web',
      description: 'Calcula la cuota del Impuesto sobre Sociedades aplicando ajustes extracontables, compensaci\u00f3n de BINs, deducciones por I+D+i y bonificaciones por territorio.',
    },
  })

  // Fetch workspaces if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchWorkspaces().catch(() => { /* ignore */ })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  // Prefill when workspace selected
  useEffect(() => {
    if (state.workspace_id && state.workspace_id !== '_manual') {
      prefill(state.workspace_id, state.ejercicio)
    } else {
      resetPrefill()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.workspace_id, state.ejercicio])

  // Apply prefill data
  useEffect(() => {
    if (prefillData) {
      dispatch({
        type: 'PREFILL',
        data: {
          ingresos_explotacion: prefillData.ingresos_explotacion,
          gastos_explotacion: prefillData.gastos_explotacion,
          resultado_contable: prefillData.resultado_contable,
          amortizacion_contable: prefillData.amortizacion_contable,
        },
      })
    }
  }, [prefillData])

  // Trigger estimate on step 3 (resultado) or any field change when on result step
  const triggerEstimate = useCallback(() => {
    const isManual = !state.workspace_id || state.workspace_id === '_manual'
    const rc = isManual
      ? (state.ingresos_explotacion - state.gastos_explotacion)
      : state.resultado_contable

    const input: ISEstimateInput = {
      workspace_id: state.workspace_id && state.workspace_id !== '_manual' ? state.workspace_id : undefined,
      ejercicio: state.ejercicio,
      tipo_entidad: state.tipo_entidad,
      territorio: state.territorio,
      facturacion_anual: state.facturacion_anual,
      ejercicios_con_bi_positiva: state.tipo_entidad === 'nueva_creacion' ? 0 : 3,
      ingresos_explotacion: state.ingresos_explotacion || undefined,
      gastos_explotacion: state.gastos_explotacion || undefined,
      resultado_contable: rc,
      amortizacion_contable: state.amortizacion_contable,
      amortizacion_fiscal: state.amortizacion_fiscal || undefined,
      gastos_no_deducibles: state.gastos_no_deducibles,
      ajustes_negativos: 0,
      bins_pendientes: state.bins_pendientes,
      gasto_id: state.gasto_id,
      gasto_it: state.gasto_it,
      incremento_ffpp: state.incremento_ffpp,
      donativos: state.donativos,
      empleados_discapacidad_33: state.empleados_discapacidad_33,
      empleados_discapacidad_65: state.empleados_discapacidad_65,
      dotacion_ric: state.dotacion_ric,
      es_zec: state.es_zec,
      rentas_ceuta_melilla: state.rentas_ceuta_melilla,
      retenciones_ingresos_cuenta: state.retenciones_ingresos_cuenta,
      pagos_fraccionados_realizados: state.pagos_fraccionados_realizados,
    }
    estimate(input)
  }, [state, estimate])

  useEffect(() => {
    if (state.step === 3) {
      triggerEstimate()
    }
  }, [state.step, triggerEstimate])

  const setField = (field: keyof WizardState, value: any) =>
    dispatch({ type: 'SET_FIELD', field, value })

  const goNext = () => dispatch({ type: 'SET_STEP', step: Math.min(state.step + 1, 3) })
  const goBack = () => dispatch({ type: 'SET_STEP', step: Math.max(state.step - 1, 0) })

  const canGoNext = (): boolean => {
    if (state.step === 0) return !!state.territorio && state.facturacion_anual > 0
    if (state.step === 1) {
      const isManual = !state.workspace_id || state.workspace_id === '_manual'
      if (isManual) return state.ingresos_explotacion > 0
      return !!prefillData
    }
    return true
  }

  const isCanarias = state.territorio === 'Canarias'
  const isCeutaMelilla = state.territorio === 'Ceuta' || state.territorio === 'Melilla'
  const isManual = !state.workspace_id || state.workspace_id === '_manual'
  const calculatedRC = isManual
    ? state.ingresos_explotacion - state.gastos_explotacion
    : state.resultado_contable

  return (
    <div className="m200-page">
      <Header />
      <div className="m200-container">
        <div className="m200-header">
          <Building2 size={40} />
          <h1>Modelo 200 &mdash; Impuesto sobre Sociedades</h1>
          <p>Estima la cuota del IS a partir de tu resultado contable y los ajustes fiscales del ejercicio.</p>
        </div>

        {/* Stepper */}
        <div className="m200-stepper">
          {STEP_LABELS.map((label, i) => (
            <div
              key={i}
              className={`m200-step-dot${state.step === i ? ' m200-step-dot--active' : ''}${state.step > i ? ' m200-step-dot--done' : ''}`}
            >
              {state.step > i ? <CheckCircle size={14} /> : <span>{i + 1}</span>}
              {label}
            </div>
          ))}
        </div>

        {/* ---- STEP 0: Datos de la entidad ---- */}
        {state.step === 0 && (
          <div className="m200-card">
            <h2><Building2 size={20} /> Datos de la entidad</h2>

            <div className="m200-field">
              <label className="m200-field__label">Tipo de entidad</label>
              <select
                className="m200-field__select"
                value={state.tipo_entidad}
                onChange={e => setField('tipo_entidad', e.target.value)}
              >
                {TIPO_ENTIDAD_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Territorio fiscal</label>
              <select
                className="m200-field__select"
                value={state.territorio}
                onChange={e => {
                  setField('territorio', e.target.value)
                  if (e.target.value !== 'Canarias') setField('es_zec', false)
                  if (e.target.value !== 'Ceuta' && e.target.value !== 'Melilla') setField('rentas_ceuta_melilla', 0)
                }}
              >
                <option value="">Selecciona territorio</option>
                {CCAA_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {isCanarias && (
              <div className="m200-field">
                <label className="m200-field__checkbox">
                  <input
                    type="checkbox"
                    checked={state.es_zec}
                    onChange={e => setField('es_zec', e.target.checked)}
                  />
                  Entidad inscrita en la ZEC (Zona Especial Canarias)
                </label>
                <span className="m200-field__help">Tipo reducido del 4% para entidades ZEC (Art. 44 Ley 19/1994)</span>
              </div>
            )}

            <div className="m200-field">
              <label className="m200-field__label">Facturaci&oacute;n anual aproximada</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.facturacion_anual || ''}
                  onChange={e => setField('facturacion_anual', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={1000}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Determina si aplican tipos reducidos para micropymes (&lt; 1M) o pymes (&lt; 10M)</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Ejercicio</label>
              <select
                className="m200-field__select"
                value={state.ejercicio}
                onChange={e => setField('ejercicio', parseInt(e.target.value))}
              >
                <option value={2025}>2025</option>
                <option value={2024}>2024</option>
              </select>
            </div>

            {isAuthenticated && workspaces.length > 0 && (
              <div className="m200-field">
                <label className="m200-field__label">Cargar datos desde workspace</label>
                <select
                  className="m200-field__select"
                  value={state.workspace_id}
                  onChange={e => setField('workspace_id', e.target.value)}
                >
                  <option value="_manual">Introducir manualmente</option>
                  {workspaces.map(w => (
                    <option key={w.id} value={w.id}>{w.name} ({w.file_count} archivos)</option>
                  ))}
                </select>
              </div>
            )}

            <div className="m200-nav">
              <span />
              <button
                className="m200-btn m200-btn--primary"
                onClick={goNext}
                disabled={!canGoNext()}
              >
                Siguiente <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* ---- STEP 1: Resultado contable ---- */}
        {state.step === 1 && (
          <div className="m200-card">
            <h2><FileText size={20} /> Resultado contable</h2>

            {prefilling && (
              <div className="m200-loading">
                <Loader2 size={20} className="spin" /> Cargando datos del workspace...
              </div>
            )}

            {!isManual && prefillData && !prefilling && (
              <>
                <div className="m200-prefill-info">
                  <Info size={16} />
                  Datos precargados de <strong>{prefillData.workspace_name}</strong> &mdash; {prefillData.num_facturas} facturas, per&iacute;odo {prefillData.periodo_cubierto}. Puedes editarlos.
                </div>

                {prefillData.cuentas_desglose.length > 0 && (
                  <table className="m200-prefill-table">
                    <thead>
                      <tr>
                        <th>Cuenta PGC</th>
                        <th>Nombre</th>
                        <th>Importe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prefillData.cuentas_desglose.map((c, i) => (
                        <tr key={i}>
                          <td>{c.cuenta}</td>
                          <td>{c.nombre}</td>
                          <td>{fmtEur(c.importe)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                <div className="m200-field">
                  <label className="m200-field__label">Ingresos de explotaci&oacute;n</label>
                  <div className="m200-field__input-wrap">
                    <input
                      type="number"
                      className="m200-field__input"
                      value={state.ingresos_explotacion || ''}
                      onChange={e => setField('ingresos_explotacion', parseFloat(e.target.value) || 0)}
                      min={0}
                      step={100}
                      inputMode="decimal"
                      placeholder="0"
                    />
                    <span className="m200-field__suffix">EUR</span>
                  </div>
                </div>

                <div className="m200-field">
                  <label className="m200-field__label">Gastos de explotaci&oacute;n</label>
                  <div className="m200-field__input-wrap">
                    <input
                      type="number"
                      className="m200-field__input"
                      value={state.gastos_explotacion || ''}
                      onChange={e => setField('gastos_explotacion', parseFloat(e.target.value) || 0)}
                      min={0}
                      step={100}
                      inputMode="decimal"
                      placeholder="0"
                    />
                    <span className="m200-field__suffix">EUR</span>
                  </div>
                </div>

                <div className="m200-field">
                  <label className="m200-field__label">Resultado contable (editable)</label>
                  <div className="m200-field__input-wrap">
                    <input
                      type="number"
                      className="m200-field__input"
                      value={state.resultado_contable || ''}
                      onChange={e => setField('resultado_contable', parseFloat(e.target.value) || 0)}
                      step={100}
                      inputMode="decimal"
                      placeholder="0"
                    />
                    <span className="m200-field__suffix">EUR</span>
                  </div>
                </div>
              </>
            )}

            {isManual && !prefilling && (
              <>
                <div className="m200-field">
                  <label className="m200-field__label">Ingresos de explotaci&oacute;n</label>
                  <div className="m200-field__input-wrap">
                    <input
                      type="number"
                      className="m200-field__input"
                      value={state.ingresos_explotacion || ''}
                      onChange={e => setField('ingresos_explotacion', parseFloat(e.target.value) || 0)}
                      min={0}
                      step={100}
                      inputMode="decimal"
                      placeholder="0"
                    />
                    <span className="m200-field__suffix">EUR</span>
                  </div>
                </div>

                <div className="m200-field">
                  <label className="m200-field__label">Gastos de explotaci&oacute;n</label>
                  <div className="m200-field__input-wrap">
                    <input
                      type="number"
                      className="m200-field__input"
                      value={state.gastos_explotacion || ''}
                      onChange={e => setField('gastos_explotacion', parseFloat(e.target.value) || 0)}
                      min={0}
                      step={100}
                      inputMode="decimal"
                      placeholder="0"
                    />
                    <span className="m200-field__suffix">EUR</span>
                  </div>
                </div>

                <div className="m200-calculated">
                  <span className="m200-calculated__label">Resultado contable</span>
                  <span className="m200-calculated__value">{fmtEur(calculatedRC)}</span>
                </div>
              </>
            )}

            <div className="m200-field">
              <label className="m200-field__label">Amortizaci&oacute;n contable</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.amortizacion_contable || ''}
                  onChange={e => setField('amortizacion_contable', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Amortizaci&oacute;n fiscal (si difiere de contable)</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.amortizacion_fiscal || ''}
                  onChange={e => setField('amortizacion_fiscal', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Si es mayor que la contable, genera un ajuste negativo (diferencia temporaria deducible)</span>
            </div>

            <div className="m200-nav">
              <button className="m200-btn m200-btn--secondary" onClick={goBack}>
                <ChevronLeft size={18} /> Anterior
              </button>
              <button
                className="m200-btn m200-btn--primary"
                onClick={goNext}
                disabled={!canGoNext()}
              >
                Siguiente <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* ---- STEP 2: Ajustes y deducciones ---- */}
        {state.step === 2 && (
          <div className="m200-card">
            <h2><FileText size={20} /> Ajustes y deducciones</h2>

            <div className="m200-field">
              <label className="m200-field__label">
                Gastos no deducibles
                <span className="m200-tooltip">
                  <Info size={14} />
                  <span className="m200-tooltip__content">
                    Art. 15 LIS: multas/sanciones, donativos no acogidos a Ley 49/2002, liberalidades, gastos con operaciones vinculadas no valorados a mercado, p&eacute;rdidas de juego, gastos financieros no deducibles (Art. 16 LIS).
                  </span>
                </span>
              </label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.gastos_no_deducibles || ''}
                  onChange={e => setField('gastos_no_deducibles', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Bases imponibles negativas (BINs) pendientes</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.bins_pendientes || ''}
                  onChange={e => setField('bins_pendientes', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">BINs de ejercicios anteriores pendientes de compensar (l&iacute;mite 70% de BI previa, 100% hasta 1M)</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Gasto en I+D</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.gasto_id || ''}
                  onChange={e => setField('gasto_id', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Deducci&oacute;n del 25% (42% si supera media de los 2 a&ntilde;os anteriores)</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Gasto en innovaci&oacute;n tecnol&oacute;gica</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.gasto_it || ''}
                  onChange={e => setField('gasto_it', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Deducci&oacute;n del 12%</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Reserva de capitalizaci&oacute;n (incremento fondos propios)</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.incremento_ffpp || ''}
                  onChange={e => setField('incremento_ffpp', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Reducci&oacute;n del 10% del incremento de fondos propios (Art. 25 LIS)</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Donativos (Ley 49/2002)</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.donativos || ''}
                  onChange={e => setField('donativos', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
              <span className="m200-field__help">Deducci&oacute;n del 40% (l&iacute;mite 15% de BI)</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Empleados con discapacidad &ge;33%</label>
              <input
                type="number"
                className="m200-field__input"
                value={state.empleados_discapacidad_33 || ''}
                onChange={e => setField('empleados_discapacidad_33', parseInt(e.target.value) || 0)}
                min={0}
                step={1}
                inputMode="numeric"
                placeholder="0"
              />
              <span className="m200-field__help">Deducci&oacute;n de 9.000 EUR por contrato</span>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Empleados con discapacidad &ge;65%</label>
              <input
                type="number"
                className="m200-field__input"
                value={state.empleados_discapacidad_65 || ''}
                onChange={e => setField('empleados_discapacidad_65', parseInt(e.target.value) || 0)}
                min={0}
                step={1}
                inputMode="numeric"
                placeholder="0"
              />
              <span className="m200-field__help">Deducci&oacute;n de 12.000 EUR por contrato</span>
            </div>

            {isCanarias && (
              <div className="m200-field">
                <label className="m200-field__label">Dotaci&oacute;n RIC (Reserva para Inversiones en Canarias)</label>
                <div className="m200-field__input-wrap">
                  <input
                    type="number"
                    className="m200-field__input"
                    value={state.dotacion_ric || ''}
                    onChange={e => setField('dotacion_ric', parseFloat(e.target.value) || 0)}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m200-field__suffix">EUR</span>
                </div>
                <span className="m200-field__help">Reducci&oacute;n de hasta el 90% del beneficio no distribuido (Art. 27 Ley 19/1994)</span>
              </div>
            )}

            {isCeutaMelilla && (
              <div className="m200-field">
                <label className="m200-field__label">Rentas obtenidas en Ceuta/Melilla</label>
                <div className="m200-field__input-wrap">
                  <input
                    type="number"
                    className="m200-field__input"
                    value={state.rentas_ceuta_melilla || ''}
                    onChange={e => setField('rentas_ceuta_melilla', parseFloat(e.target.value) || 0)}
                    min={0}
                    step={100}
                    inputMode="decimal"
                    placeholder="0"
                  />
                  <span className="m200-field__suffix">EUR</span>
                </div>
                <span className="m200-field__help">Bonificaci&oacute;n del 50% sobre la parte de cuota correspondiente</span>
              </div>
            )}

            <div className="m200-field">
              <label className="m200-field__label">Retenciones e ingresos a cuenta</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.retenciones_ingresos_cuenta || ''}
                  onChange={e => setField('retenciones_ingresos_cuenta', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
            </div>

            <div className="m200-field">
              <label className="m200-field__label">Pagos fraccionados ya realizados (Modelo 202)</label>
              <div className="m200-field__input-wrap">
                <input
                  type="number"
                  className="m200-field__input"
                  value={state.pagos_fraccionados_realizados || ''}
                  onChange={e => setField('pagos_fraccionados_realizados', parseFloat(e.target.value) || 0)}
                  min={0}
                  step={100}
                  inputMode="decimal"
                  placeholder="0"
                />
                <span className="m200-field__suffix">EUR</span>
              </div>
            </div>

            <div className="m200-nav">
              <button className="m200-btn m200-btn--secondary" onClick={goBack}>
                <ChevronLeft size={18} /> Anterior
              </button>
              <button className="m200-btn m200-btn--primary" onClick={goNext}>
                Calcular <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* ---- STEP 3: Resultado ---- */}
        {state.step === 3 && (
          <div className="m200-result-grid">
            {/* Estimator bar */}
            {result && (
              <div className="m200-estimator-sticky">
                <div className={`estimator-bar ${result.tipo === 'a_devolver' ? 'estimator-bar--refund' : 'estimator-bar--payment'} ${estimating ? 'estimator-bar--loading' : ''}`}>
                  {estimating ? (
                    <div className="estimator-bar__loader">
                      <Loader2 size={20} className="spin" />
                      <span>Calculando...</span>
                    </div>
                  ) : (
                    <>
                      <div className="estimator-bar__icon">
                        {result.tipo === 'a_devolver'
                          ? <Building2 size={22} style={{ color: '#34d399' }} />
                          : <Building2 size={22} style={{ color: '#f87171' }} />}
                      </div>
                      <div className="estimator-bar__content">
                        <span className="estimator-bar__label">
                          {result.tipo === 'a_devolver' ? 'A devolver' : 'A ingresar'}
                        </span>
                        <span className="estimator-bar__amount">
                          {Math.abs(result.resultado_liquidacion).toLocaleString('es-ES', { minimumFractionDigits: 2 })}
                          <span className="estimator-bar__currency"> EUR</span>
                        </span>
                      </div>
                      <div className="estimator-bar__meta">
                        <span className="estimator-bar__rate">
                          Tipo efectivo: {result.tipo_efectivo.toFixed(1)}%
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            {estimating && !result && (
              <div className="m200-loading">
                <Loader2 size={20} className="spin" /> Calculando Impuesto sobre Sociedades...
              </div>
            )}

            {estError && (
              <div className="m200-error">
                <AlertCircle size={16} /> {estError}
              </div>
            )}

            {result && <ISResultCard result={result} />}

            {/* Actions */}
            <div className="m200-actions">
              <button
                className="m200-btn m200-btn--outline"
                onClick={() => {
                  console.log('Descargar PDF borrador', result)
                }}
              >
                <Download size={16} /> Descargar PDF borrador
              </button>
              <Link to="/modelo-202" className="m200-btn m200-btn--secondary" style={{ textDecoration: 'none' }}>
                <FileText size={16} /> Calcular Modelo 202
              </Link>
            </div>

            <div className="m200-nav">
              <button className="m200-btn m200-btn--secondary" onClick={goBack}>
                <ChevronLeft size={18} /> Modificar datos
              </button>
              <button
                className="m200-btn m200-btn--secondary"
                onClick={() => {
                  resetEstimate()
                  resetPrefill()
                  dispatch({ type: 'RESET' })
                }}
              >
                Nueva simulaci&oacute;n
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
