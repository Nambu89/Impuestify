import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { ChevronLeft, ChevronRight, RotateCcw, MapPin, Briefcase, PiggyBank, Home as HomeIcon, Users, Gift, BarChart3, CheckCircle, Info, AlertTriangle, Zap, Shield, TrendingUp } from 'lucide-react'
import Header from '../components/Header'
import LiveEstimatorBar from '../components/LiveEstimatorBar'
import DynamicFiscalForm from '../components/DynamicFiscalForm'
import { useTaxGuideProgress, STEP_LABELS, QUICK_STEP_LABELS, type TaxGuideData } from '../hooks/useTaxGuideProgress'
import { useIrpfEstimator } from '../hooks/useIrpfEstimator'
import { useFiscalProfile } from '../hooks/useFiscalProfile'
import { useDeductionDiscovery, type MissingQuestion } from '../hooks/useDeductionDiscovery'
import './TaxGuidePage.css'

const CCAA_OPTIONS = [
    'Andalucia', 'Aragon', 'Asturias', 'Baleares', 'Canarias',
    'Cantabria', 'Castilla-La Mancha', 'Castilla y Leon', 'Cataluna',
    'Ceuta', 'Valencia', 'Extremadura', 'Galicia',
    'La Rioja', 'Madrid', 'Melilla', 'Murcia', 'Navarra',
    'Araba', 'Bizkaia', 'Gipuzkoa',
]

const STEP_ICONS = [MapPin, Briefcase, PiggyBank, HomeIcon, TrendingUp, Users, Gift, BarChart3]
const QUICK_STEP_ICONS = [MapPin, BarChart3]

// === Reusable inputs ===

function NumberInput({ label, value, onChange, suffix, min = 0, step = 100, help }: {
    label: string; value: number; onChange: (v: number) => void;
    suffix?: string; min?: number; step?: number; help?: string
}) {
    return (
        <div className="tg-field">
            <label className="tg-field__label">{label}</label>
            <div className="tg-field__input-wrap">
                <input
                    type="number"
                    className="tg-field__input"
                    value={value || ''}
                    onChange={e => onChange(parseFloat(e.target.value) || 0)}
                    min={min}
                    step={step}
                    inputMode="decimal"
                    placeholder="0"
                />
                {suffix && <span className="tg-field__suffix">{suffix}</span>}
            </div>
            {help && <span className="tg-field__help">{help}</span>}
        </div>
    )
}

function CheckboxInput({ label, checked, onChange, help }: {
    label: string; checked: boolean; onChange: (v: boolean) => void; help?: string
}) {
    return (
        <div className="tg-field">
            <label className="tg-field__label tg-field__checkbox-label">
                <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
                {label}
            </label>
            {help && <span className="tg-field__help">{help}</span>}
        </div>
    )
}

// === Phase C: CCAA contextual tips ===

function CcaaTip({ ccaa }: { ccaa: string }) {
    if (!ccaa) return null

    const isCeutaMelilla = ccaa === 'Ceuta' || ccaa === 'Melilla'
    const isCanarias = ccaa === 'Canarias'
    const isForal = ['Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra'].includes(ccaa)

    if (isCeutaMelilla) {
        return (
            <div className="tg-tip tg-tip--success">
                <Shield size={18} />
                <div>
                    <strong>Ventaja fiscal Ceuta/Melilla</strong>
                    <p>Deduccion del 60% sobre la cuota integra del IRPF (Art. 68.4 LIRPF). Ademas, aplica IPSI en lugar de IVA con tipos inferiores. Bonificacion del 50% en cuotas de autonomos.</p>
                </div>
            </div>
        )
    }

    if (isForal) {
        return (
            <div className="tg-tip tg-tip--warning">
                <AlertTriangle size={18} />
                <div>
                    <strong>Territorio foral</strong>
                    <p>Los territorios forales tienen su propio sistema IRPF con escalas y deducciones específicas. No se aplican las deducciones estatales del régimen común.</p>
                </div>
            </div>
        )
    }

    if (isCanarias) {
        return (
            <div className="tg-tip tg-tip--info">
                <Info size={18} />
                <div>
                    <strong>Canarias</strong>
                    <p>En Canarias se aplica el IGIC en lugar del IVA. El IRPF sigue el régimen común estatal con deducciones autonómicas propias.</p>
                </div>
            </div>
        )
    }

    return null
}

// === Phase D: Wizard mode selector ===

function WizardModeSelector({ mode, onChange }: { mode: 'quick' | 'full'; onChange: (m: 'quick' | 'full') => void }) {
    return (
        <div className="tg-mode-selector">
            <button
                className={`tg-mode-selector__btn ${mode === 'quick' ? 'tg-mode-selector__btn--active' : ''}`}
                onClick={() => onChange('quick')}
            >
                <Zap size={16} />
                <div>
                    <strong>Rapido</strong>
                    <span>Solo salario y CCAA</span>
                </div>
            </button>
            <button
                className={`tg-mode-selector__btn ${mode === 'full' ? 'tg-mode-selector__btn--active' : ''}`}
                onClick={() => onChange('full')}
            >
                <BarChart3 size={16} />
                <div>
                    <strong>Completo</strong>
                    <span>Todas las deducciones</span>
                </div>
            </button>
        </div>
    )
}

// === Step 1: Datos personales ===

function StepPersonal({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Datos personales</h2>
            <p className="tg-step__desc">Necesitamos saber donde resides para aplicar las escalas correctas.</p>

            <WizardModeSelector
                mode={data.wizard_mode}
                onChange={m => update({ wizard_mode: m })}
            />

            <div className="tg-field">
                <label className="tg-field__label">Comunidad Autonoma</label>
                <select
                    className="tg-field__select"
                    value={data.comunidad_autonoma}
                    onChange={e => {
                        const ccaa = e.target.value
                        update({
                            comunidad_autonoma: ccaa,
                            ceuta_melilla: ccaa === 'Ceuta' || ccaa === 'Melilla',
                        })
                    }}
                >
                    <option value="">Selecciona tu CCAA</option>
                    {CCAA_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
            </div>

            <CcaaTip ccaa={data.comunidad_autonoma} />

            <NumberInput
                label="Edad"
                value={data.edad_contribuyente}
                onChange={v => update({ edad_contribuyente: v })}
                min={16} step={1}
            />

            {data.wizard_mode === 'full' && (
                <>
                    <CheckboxInput
                        label="Tributacion conjunta"
                        checked={data.tributacion_conjunta}
                        onChange={v => update({ tributacion_conjunta: v })}
                        help="Permite declarar con tu unidad familiar. Aplica una reducción fija sobre la base imponible."
                    />

                    {data.tributacion_conjunta && (
                        <div className="tg-field">
                            <label className="tg-field__label">Tipo de unidad familiar</label>
                            <select
                                className="tg-field__select"
                                value={data.tipo_unidad_familiar}
                                onChange={e => update({ tipo_unidad_familiar: e.target.value })}
                            >
                                <option value="matrimonio">Matrimonio (reducción 3.400 EUR)</option>
                                <option value="monoparental">Monoparental (reducción 2.150 EUR)</option>
                            </select>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

// === Step 2: Trabajo (Phase A: salary input mode + activity income) ===

function StepTrabajo({ data, update, zeroIncomeAcknowledged, onAcknowledgeZeroIncome }: StepProps & {
    zeroIncomeAcknowledged: boolean
    onAcknowledgeZeroIncome: (v: boolean) => void
}) {
    const isMonthly = data.salary_input_mode === 'monthly'
    const computedAnnual = isMonthly
        ? (data.salario_base_mensual + data.complementos_salariales) * data.num_pagas_anuales
        : data.ingresos_trabajo

    const [showActivity, setShowActivity] = useState(data.ingresos_actividad > 0)

    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Rendimientos del trabajo</h2>
            <p className="tg-step__desc">Incluye tu salario, cotizaciones y retenciones.</p>

            {/* Salary input mode toggle */}
            <div className="tg-toggle-group">
                <button
                    className={`tg-toggle-group__btn ${!isMonthly ? 'tg-toggle-group__btn--active' : ''}`}
                    onClick={() => update({ salary_input_mode: 'annual' })}
                >
                    Salario anual
                </button>
                <button
                    className={`tg-toggle-group__btn ${isMonthly ? 'tg-toggle-group__btn--active' : ''}`}
                    onClick={() => update({ salary_input_mode: 'monthly' })}
                >
                    Salario mensual
                </button>
            </div>

            {isMonthly ? (
                <>
                    <NumberInput
                        label="Salario base mensual"
                        value={data.salario_base_mensual}
                        onChange={v => update({ salario_base_mensual: v })}
                        suffix="EUR"
                        help="Aparece en tu nómina como 'Salario base'"
                    />
                    <NumberInput
                        label="Complementos salariales"
                        value={data.complementos_salariales}
                        onChange={v => update({ complementos_salariales: v })}
                        suffix="EUR"
                        help="Plus transporte, antiguedad, productividad..."
                    />
                    <div className="tg-field">
                        <label className="tg-field__label">Numero de pagas</label>
                        <div className="tg-toggle-group">
                            <button
                                className={`tg-toggle-group__btn ${data.num_pagas_anuales === 12 ? 'tg-toggle-group__btn--active' : ''}`}
                                onClick={() => update({ num_pagas_anuales: 12 })}
                            >
                                12 pagas
                            </button>
                            <button
                                className={`tg-toggle-group__btn ${data.num_pagas_anuales === 14 ? 'tg-toggle-group__btn--active' : ''}`}
                                onClick={() => update({ num_pagas_anuales: 14 })}
                            >
                                14 pagas
                            </button>
                        </div>
                        <span className="tg-field__help">
                            {data.num_pagas_anuales === 14
                                ? '12 mensualidades + 2 pagas extras (junio y diciembre)'
                                : '12 mensualidades con pagas extras prorrateadas'}
                        </span>
                    </div>
                    {computedAnnual > 0 && (
                        <div className="tg-computed-value">
                            Bruto anual estimado: <strong>{computedAnnual.toLocaleString('es-ES')} EUR</strong>
                        </div>
                    )}
                </>
            ) : (
                <NumberInput
                    label="Salario bruto anual"
                    value={data.ingresos_trabajo}
                    onChange={v => update({ ingresos_trabajo: v })}
                    suffix="EUR"
                    help="Suma de todas tus nóminas brutas del año"
                />
            )}

            <NumberInput
                label="Cotizaciones a la Seguridad Social"
                value={data.ss_empleado}
                onChange={v => update({ ss_empleado: v })}
                suffix="EUR"
                help="Total anual. Si no lo sabes, dejalo en 0 y se estimara (~6,35%)"
            />

            <h3 className="tg-step__subtitle">Retenciones IRPF</h3>

            <NumberInput
                label="Porcentaje IRPF en nómina"
                value={data.irpf_retenido_porcentaje}
                onChange={v => update({ irpf_retenido_porcentaje: v })}
                suffix="%"
                step={0.1}
                help="Aparece en tu nómina como '% IRPF' o 'retención IRPF'"
            />

            {data.irpf_retenido_porcentaje > 0 && computedAnnual > 0 && (
                <div className="tg-computed-value">
                    Retenciones anuales estimadas: <strong>{(computedAnnual * data.irpf_retenido_porcentaje / 100).toLocaleString('es-ES', { maximumFractionDigits: 0 })} EUR</strong>
                </div>
            )}

            <NumberInput
                label="Retenciones IRPF totales (anual)"
                value={data.retenciones_trabajo}
                onChange={v => update({ retenciones_trabajo: v })}
                suffix="EUR"
                help="Si pusiste el %, se calcula automáticamente. Si lo sabes exacto, ponlo aquí."
            />

            {/* Activity income section for autonomos */}
            <div style={{ marginTop: 'var(--spacing-6)' }}>
                <CheckboxInput
                    label="Tengo ingresos por actividad economica (autonomo)"
                    checked={showActivity}
                    onChange={v => {
                        setShowActivity(v)
                        if (!v) update({
                            ingresos_actividad: 0, gastos_actividad: 0, cuota_autonomo_anual: 0,
                            amortizaciones_actividad: 0, provisiones_actividad: 0, otros_gastos_actividad: 0,
                            retenciones_actividad: 0, pagos_fraccionados_130: 0,
                            inicio_actividad: false, un_solo_cliente: false,
                        })
                    }}
                />
            </div>

            {showActivity && (
                <>
                    <h3 className="tg-step__subtitle">Actividad economica</h3>

                    <div className="tg-field">
                        <label className="tg-field__label">Método de estimación</label>
                        <select
                            className="tg-field__select"
                            value={data.estimacion_actividad}
                            onChange={e => update({ estimacion_actividad: e.target.value })}
                        >
                            <option value="directa_simplificada">Estimacion directa simplificada</option>
                            <option value="directa_normal">Estimacion directa normal</option>
                            <option value="objetiva">Estimacion objetiva (modulos)</option>
                        </select>
                        <span className="tg-field__help">
                            {data.estimacion_actividad === 'directa_simplificada'
                                ? 'La mas comun. Incluye 5% de gastos de dificil justificacion (max 2.000 EUR)'
                                : data.estimacion_actividad === 'directa_normal'
                                ? 'Requiere contabilidad ajustada al Codigo de Comercio. Permite provisiones'
                                : 'Solo si tu actividad esta incluida en la Orden de Modulos'}
                        </span>
                    </div>

                    <NumberInput
                        label="Ingresos de actividad (anual)"
                        value={data.ingresos_actividad}
                        onChange={v => update({ ingresos_actividad: v })}
                        suffix="EUR"
                        help="Total facturado (base imponible, sin IVA/IGIC)"
                    />

                    <NumberInput
                        label="Gastos deducibles de actividad"
                        value={data.gastos_actividad}
                        onChange={v => update({ gastos_actividad: v })}
                        suffix="EUR"
                        help="Suministros, alquiler local, seguros, material, marketing..."
                    />

                    <NumberInput
                        label="Cuota de autonomo anual"
                        value={data.cuota_autonomo_anual}
                        onChange={v => update({ cuota_autonomo_anual: v })}
                        suffix="EUR"
                        help="Cuota mensual x 12. Ej: 293 EUR/mes = 3.516 EUR/ano"
                    />

                    <NumberInput
                        label="Amortizaciones"
                        value={data.amortizaciones_actividad}
                        onChange={v => update({ amortizaciones_actividad: v })}
                        suffix="EUR"
                        help="Amortizacion de activos fijos (ordenador, vehiculo, mobiliario...)"
                    />

                    {data.estimacion_actividad === 'directa_normal' && (
                        <NumberInput
                            label="Provisiones"
                            value={data.provisiones_actividad}
                            onChange={v => update({ provisiones_actividad: v })}
                            suffix="EUR"
                            help="Solo en estimación directa normal"
                        />
                    )}

                    <NumberInput
                        label="Otros gastos deducibles"
                        value={data.otros_gastos_actividad}
                        onChange={v => update({ otros_gastos_actividad: v })}
                        suffix="EUR"
                    />

                    <h3 className="tg-step__subtitle">Retenciones y pagos a cuenta</h3>

                    <NumberInput
                        label="Retenciones en facturas (anual)"
                        value={data.retenciones_actividad}
                        onChange={v => update({ retenciones_actividad: v })}
                        suffix="EUR"
                        help="15% (o 7% nuevos autonomos) retenido por tus clientes profesionales"
                    />

                    <NumberInput
                        label="Pagos fraccionados Modelo 130"
                        value={data.pagos_fraccionados_130}
                        onChange={v => update({ pagos_fraccionados_130: v })}
                        suffix="EUR"
                        help="Suma de los 4 trimestres del Modelo 130 pagados"
                    />

                    <h3 className="tg-step__subtitle">Reducciones</h3>

                    <CheckboxInput
                        label="Inicio de actividad (primeros 2 anos con beneficio)"
                        checked={data.inicio_actividad}
                        onChange={v => update({ inicio_actividad: v })}
                        help="Reduccion del 20% sobre el rendimiento neto positivo (Art. 32.3 LIRPF)"
                    />

                    <CheckboxInput
                        label="Mas del 75% de ingresos de un solo cliente"
                        checked={data.un_solo_cliente}
                        onChange={v => update({ un_solo_cliente: v })}
                        help="Autónomo económicamente dependiente (TRADE). Aplica reducción similar a trabajo (Art. 32.2 LIRPF)"
                    />
                </>
            )}

            {/* B-GF-06: Zero-income acknowledgment */}
            {!zeroIncomeAcknowledged && data.ingresos_trabajo === 0 && data.ingresos_actividad === 0 && data.salary_input_mode === 'annual' && (
                <div className="tg-tip tg-tip--warning" style={{ marginTop: 'var(--spacing-4)' }}>
                    <AlertTriangle size={18} />
                    <div>
                        <strong>Sin ingresos introducidos</strong>
                        <p>Has dejado los ingresos en 0. Si no has tenido rentas del trabajo este ano, confirma para continuar.</p>
                        <button
                            type="button"
                            className="tg-nav__btn tg-nav__btn--secondary"
                            style={{ marginTop: 'var(--spacing-3)', fontSize: 'var(--font-size-xs)' }}
                            onClick={() => onAcknowledgeZeroIncome(true)}
                        >
                            Confirmar: no tuve ingresos del trabajo
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

// === Step 3: Ahorro ===

function StepAhorro({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Ahorro e inversiones</h2>
            <p className="tg-step__desc">Intereses, dividendos y ganancias patrimoniales tributan en la base del ahorro.</p>

            <NumberInput label="Intereses de cuentas/depositos" value={data.intereses} onChange={v => update({ intereses: v })} suffix="EUR" />
            <NumberInput label="Dividendos" value={data.dividendos} onChange={v => update({ dividendos: v })} suffix="EUR" />
            <NumberInput label="Ganancias de fondos/acciones" value={data.ganancias_fondos} onChange={v => update({ ganancias_fondos: v })} suffix="EUR" help="Ganancias netas realizadas (ventas - compras)" />
            <NumberInput label="Retenciones sobre capital mobiliario" value={data.retenciones_ahorro} onChange={v => update({ retenciones_ahorro: v })} suffix="EUR" help="19% retenido por bancos sobre intereses y dividendos" />
        </div>
    )
}

// === Step 4: Inmuebles ===

function StepInmuebles({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Inmuebles y alquileres</h2>
            <p className="tg-step__desc">Si alquilas un inmueble, indica los ingresos y gastos asociados.</p>

            <NumberInput label="Ingresos por alquiler (anual)" value={data.ingresos_alquiler} onChange={v => update({ ingresos_alquiler: v })} suffix="EUR" />
            <NumberInput label="Gastos deducibles del alquiler" value={data.gastos_alquiler_total} onChange={v => update({ gastos_alquiler_total: v })} suffix="EUR" help="IBI, comunidad, seguros, reparaciones, intereses hipoteca..." />
            <NumberInput label="Valor de adquisicion del inmueble" value={data.valor_adquisicion_inmueble} onChange={v => update({ valor_adquisicion_inmueble: v })} suffix="EUR" help="Para calcular la amortizacion (3% anual)" />
            <NumberInput label="Retenciones sobre alquileres" value={data.retenciones_alquiler} onChange={v => update({ retenciones_alquiler: v })} suffix="EUR" help="19% retenido por inquilinos empresas/profesionales" />

            <h3 className="tg-step__subtitle">Alquiler como inquilino</h3>
            <CheckboxInput label="Tengo contrato de alquiler anterior al 1/1/2015" checked={data.alquiler_habitual_pre2015} onChange={v => update({ alquiler_habitual_pre2015: v })} help="Régimen transitorio: deducción del 10,05% sobre el alquiler pagado (máx. 9.040 EUR/año)" />
            {data.alquiler_habitual_pre2015 && (
                <NumberInput label="Alquiler anual pagado" value={data.alquiler_pagado_anual} onChange={v => update({ alquiler_pagado_anual: v })} suffix="EUR" />
            )}

            <h3 className="tg-step__subtitle">Segundas viviendas</h3>
            <NumberInput label="Valor catastral de segundas viviendas" value={data.valor_catastral_segundas_viviendas} onChange={v => update({ valor_catastral_segundas_viviendas: v })} suffix="EUR" help="Viviendas no alquiladas ni vivienda habitual. Imputa 1,1%-2% como renta" />
            <CheckboxInput label="Valor catastral revisado despues de 1994" checked={data.valor_catastral_revisado_post1994} onChange={v => update({ valor_catastral_revisado_post1994: v })} help="Si fue revisado antes de 1994 se aplica el 2% en lugar del 1,1%" />
        </div>
    )
}

// === Step 4: Inversiones y cripto ===

function StepInversiones({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Inversiones y cripto</h2>
            <p className="tg-step__desc">Ganancias y perdidas patrimoniales de acciones, fondos, criptomonedas, derivados y apuestas.</p>

            <CheckboxInput label="Tengo criptomonedas" checked={data.tiene_criptomonedas} onChange={v => {
                update({ tiene_criptomonedas: v })
                if (!v) update({ cripto_ganancia_neta: 0, cripto_perdida_neta: 0 })
            }} />
            {data.tiene_criptomonedas && (
                <>
                    <NumberInput label="Ganancias netas cripto" value={data.cripto_ganancia_neta} onChange={v => update({ cripto_ganancia_neta: v })} suffix="EUR" help="Ganancias realizadas (ventas - compras, método FIFO)" />
                    <NumberInput label="Perdidas netas cripto" value={data.cripto_perdida_neta} onChange={v => update({ cripto_perdida_neta: v })} suffix="EUR" help="Pérdidas realizadas (no compensadas). Atención: regla antiaplicación 61 días" />
                </>
            )}

            <CheckboxInput label="Tengo acciones o fondos de inversion" checked={data.tiene_acciones_fondos} onChange={v => {
                update({ tiene_acciones_fondos: v })
                if (!v) update({ ganancias_acciones: 0, perdidas_acciones: 0, ganancias_reembolso_fondos: 0, perdidas_reembolso_fondos: 0 })
            }} />
            {data.tiene_acciones_fondos && (
                <>
                    <NumberInput label="Ganancias por venta de acciones" value={data.ganancias_acciones} onChange={v => update({ ganancias_acciones: v })} suffix="EUR" />
                    <NumberInput label="Perdidas por venta de acciones" value={data.perdidas_acciones} onChange={v => update({ perdidas_acciones: v })} suffix="EUR" />
                    <NumberInput label="Ganancias por reembolso de fondos" value={data.ganancias_reembolso_fondos} onChange={v => update({ ganancias_reembolso_fondos: v })} suffix="EUR" />
                    <NumberInput label="Perdidas por reembolso de fondos" value={data.perdidas_reembolso_fondos} onChange={v => update({ perdidas_reembolso_fondos: v })} suffix="EUR" />
                </>
            )}

            <CheckboxInput label="Tengo derivados (opciones, futuros, CFDs)" checked={data.tiene_derivados} onChange={v => {
                update({ tiene_derivados: v })
                if (!v) update({ ganancias_derivados: 0, perdidas_derivados: 0 })
            }} />
            {data.tiene_derivados && (
                <>
                    <NumberInput label="Ganancias de derivados" value={data.ganancias_derivados} onChange={v => update({ ganancias_derivados: v })} suffix="EUR" />
                    <NumberInput label="Perdidas de derivados" value={data.perdidas_derivados} onChange={v => update({ perdidas_derivados: v })} suffix="EUR" />
                </>
            )}

            <CheckboxInput label="Tengo premios de apuestas privadas" checked={data.tiene_ganancias_juegos_privados} onChange={v => {
                update({ tiene_ganancias_juegos_privados: v })
                if (!v) update({ premios_metalico_privados: 0, perdidas_juegos_privados: 0 })
            }} help="Casinos, poker, apuestas deportivas privadas (tributan en base general)" />
            {data.tiene_ganancias_juegos_privados && (
                <>
                    <NumberInput label="Premios de juegos privados" value={data.premios_metalico_privados} onChange={v => update({ premios_metalico_privados: v })} suffix="EUR" />
                    <NumberInput label="Perdidas de juegos privados" value={data.perdidas_juegos_privados} onChange={v => update({ perdidas_juegos_privados: v })} suffix="EUR" help="Compensables solo con ganancias de juegos" />
                </>
            )}

            <CheckboxInput label="Tengo premios de loterias publicas" checked={data.tiene_premios_loterias} onChange={v => {
                update({ tiene_premios_loterias: v })
                if (!v) update({ premios_metalico_publicos: 0 })
            }} help="Loteria Nacional, Euromillones, ONCE, Cruz Roja. Gravamen especial 20% (exentos primeros 40.000 EUR)" />
            {data.tiene_premios_loterias && (
                <NumberInput label="Premios de loterias publicas" value={data.premios_metalico_publicos} onChange={v => update({ premios_metalico_publicos: v })} suffix="EUR" help="Importe bruto total. Los primeros 40.000 EUR estan exentos" />
            )}
        </div>
    )
}

// === Step 5: Familia ===

function StepFamilia({ data, update }: StepProps) {
    const handleDescendientes = (n: number) => {
        const current = data.anios_nacimiento_desc || []
        const currentYear = new Date().getFullYear()
        if (n > current.length) {
            update({
                num_descendientes: n,
                anios_nacimiento_desc: [...current, ...Array(n - current.length).fill(currentYear - 5)],
            })
        } else {
            update({
                num_descendientes: n,
                anios_nacimiento_desc: current.slice(0, n),
            })
        }
    }

    const updateBirthYear = (idx: number, year: number) => {
        const arr = [...(data.anios_nacimiento_desc || [])]
        arr[idx] = year
        update({ anios_nacimiento_desc: arr })
    }

    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Situacion familiar</h2>
            <p className="tg-step__desc">Los minimos personales y familiares reducen la base imponible.</p>

            <NumberInput label="Numero de hijos" value={data.num_descendientes} onChange={handleDescendientes} min={0} step={1} />

            {(data.anios_nacimiento_desc || []).map((y, i) => (
                <NumberInput key={i} label={`Ano de nacimiento - Hijo ${i + 1}`} value={y} onChange={v => updateBirthYear(i, v)} min={1950} step={1} />
            ))}

            {data.num_descendientes > 0 && (
                <CheckboxInput label="Custodia compartida" checked={data.custodia_compartida} onChange={v => update({ custodia_compartida: v })} />
            )}

            <NumberInput label="Ascendientes mayores de 65 anos" value={data.num_ascendientes_65} onChange={v => update({ num_ascendientes_65: v })} min={0} step={1} />
            <NumberInput label="Ascendientes mayores de 75 anos" value={data.num_ascendientes_75} onChange={v => update({ num_ascendientes_75: v })} min={0} step={1} />

            <div className="tg-field">
                <label className="tg-field__label">Grado de discapacidad</label>
                <select className="tg-field__select" value={data.discapacidad_contribuyente} onChange={e => update({ discapacidad_contribuyente: parseInt(e.target.value) })}>
                    <option value={0}>Sin discapacidad</option>
                    <option value={33}>33% - 64%</option>
                    <option value={65}>65% o mas</option>
                </select>
            </div>

            <CheckboxInput label="Madre trabajadora dada de alta en la SS" checked={data.madre_trabajadora_ss} onChange={v => update({ madre_trabajadora_ss: v })} help="Deduccion por maternidad: 1.200 EUR/hijo menor de 3 anos" />

            {data.madre_trabajadora_ss && (
                <NumberInput label="Gastos de guarderia (anual)" value={data.gastos_guarderia_anual} onChange={v => update({ gastos_guarderia_anual: v })} suffix="EUR" help="Hasta 1.000 EUR adicionales por hijo en guarderia autorizada" />
            )}

            <CheckboxInput label="Familia numerosa" checked={data.familia_numerosa} onChange={v => update({ familia_numerosa: v })} />

            {data.familia_numerosa && (
                <div className="tg-field">
                    <label className="tg-field__label">Tipo de familia numerosa</label>
                    <select className="tg-field__select" value={data.tipo_familia_numerosa} onChange={e => update({ tipo_familia_numerosa: e.target.value })}>
                        <option value="general">General (3-4 hijos) - 1.200 EUR</option>
                        <option value="especial">Especial (5+ hijos) - 2.400 EUR</option>
                    </select>
                </div>
            )}
        </div>
    )
}

// === Step 6: Deducciones (Phase B: proactive discovery + DynamicFiscalForm) ===

function StepDeducciones({ data, update, discoveryResult, discoveryLoading, discoveryError, discoveryAnswers, onAnswerQuestion, dynamicFormValues, onDynamicFormChange }: StepProps & {
    discoveryResult: any
    discoveryLoading: boolean
    discoveryError: string | null
    discoveryAnswers: Record<string, boolean>
    onAnswerQuestion: (key: string, value: boolean) => void
    dynamicFormValues: Record<string, any>
    onDynamicFormChange: (key: string, value: any) => void
}) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Deducciones y reducciones</h2>
            <p className="tg-step__desc">Estas deducciones reducen directamente tu cuota o tu base imponible.</p>

            <h3 className="tg-step__subtitle">Planes de pensiones</h3>
            <NumberInput label="Aportaciones propias a planes de pensiones" value={data.aportaciones_plan_pensiones} onChange={v => update({ aportaciones_plan_pensiones: v })} suffix="EUR" help="Maximo 1.500 EUR/año (reducen la base imponible general)" />
            <NumberInput label="Aportaciones de la empresa" value={data.aportaciones_plan_pensiones_empresa} onChange={v => update({ aportaciones_plan_pensiones_empresa: v })} suffix="EUR" help="Limite conjunto con propias: 8.500 EUR" />

            <h3 className="tg-step__subtitle">Vivienda habitual (hipoteca anterior al 1/1/2013)</h3>
            <CheckboxInput label="Tengo hipoteca firmada antes del 1 de enero de 2013" checked={data.hipoteca_pre2013} onChange={v => update({ hipoteca_pre2013: v })} help="Regimen transitorio: deduccion del 15% sobre max. 9.040 EUR/ano" />

            {data.hipoteca_pre2013 && (
                <>
                    <NumberInput label="Capital amortizado en el ano" value={data.capital_amortizado_hipoteca} onChange={v => update({ capital_amortizado_hipoteca: v })} suffix="EUR" help="Principal pagado durante el ejercicio" />
                    <NumberInput label="Intereses de hipoteca pagados" value={data.intereses_hipoteca} onChange={v => update({ intereses_hipoteca: v })} suffix="EUR" />
                </>
            )}

            <h3 className="tg-step__subtitle">Donativos</h3>
            <NumberInput label="Donativos a entidades Ley 49/2002" value={data.donativos_ley_49_2002} onChange={v => update({ donativos_ley_49_2002: v })} suffix="EUR" help="ONGs, fundaciones... 80% primeros 250 EUR, 40% resto" />
            {data.donativos_ley_49_2002 > 0 && (
                <CheckboxInput label="Donante recurrente (3+ anos misma entidad)" checked={data.donativo_recurrente} onChange={v => update({ donativo_recurrente: v })} help="Sube al 45% el exceso sobre 250 EUR" />
            )}

            {/* Task 1: DynamicFiscalForm — CCAA-specific deduction fields */}
            {data.comunidad_autonoma && (
                <>
                    <h3 className="tg-step__subtitle">Deducciones especificas de {data.comunidad_autonoma}</h3>
                    <DynamicFiscalForm
                        ccaa={data.comunidad_autonoma}
                        values={dynamicFormValues}
                        onChange={onDynamicFormChange}
                        compact
                    />
                </>
            )}

            {/* Phase B: Proactive deduction discovery */}
            {data.comunidad_autonoma && (
                <div className="tg-discovery">
                    <h3 className="tg-step__subtitle">Deducciones descubiertas para {data.comunidad_autonoma}</h3>

                    {discoveryLoading && <p className="tg-discovery__loading">Buscando deducciones...</p>}

                    {/* B-GF-07: Show error state if discovery API fails */}
                    {discoveryError && !discoveryLoading && (
                        <div className="tg-tip tg-tip--warning">
                            <AlertTriangle size={18} />
                            <div>
                                <strong>No se pudieron cargar las deducciones</strong>
                                <p>{discoveryError}</p>
                            </div>
                        </div>
                    )}

                    {!discoveryError && discoveryResult && discoveryResult.eligible.length > 0 && (
                        <div className="tg-discovery__section">
                            <p className="tg-discovery__section-label tg-discovery__section-label--eligible">Deducciones a las que tienes derecho</p>
                            {discoveryResult.eligible.map((d: any) => (
                                <div key={d.code} className="tg-deduction-card tg-deduction-card--eligible">
                                    <div className="tg-deduction-card__header">
                                        <CheckCircle size={16} />
                                        <strong>{d.name}</strong>
                                    </div>
                                    {d.description && <p className="tg-deduction-card__desc">{d.description}</p>}
                                    {d.max_amount && <span className="tg-deduction-card__badge">Hasta {d.max_amount.toLocaleString('es-ES')} EUR</span>}
                                    {d.fixed_amount && <span className="tg-deduction-card__badge">{d.fixed_amount.toLocaleString('es-ES')} EUR</span>}
                                    {d.legal_reference && <span className="tg-deduction-card__ref">{d.legal_reference}</span>}
                                </div>
                            ))}
                            {discoveryResult.estimated_savings > 0 && (
                                <div className="tg-discovery__savings">
                                    Ahorro estimado: <strong>{discoveryResult.estimated_savings.toLocaleString('es-ES')} EUR</strong>
                                </div>
                            )}
                        </div>
                    )}

                    {!discoveryError && discoveryResult && discoveryResult.missing_questions.length > 0 && (
                        <div className="tg-discovery__section">
                            <p className="tg-discovery__section-label tg-discovery__section-label--maybe">Responde para descubrir mas deducciones</p>
                            {discoveryResult.missing_questions.slice(0, 5).map((q: MissingQuestion) => (
                                <div key={q.key} className="tg-deduction-question">
                                    <span className="tg-deduction-question__text">{q.text}</span>
                                    <div className="tg-deduction-question__actions">
                                        <button
                                            className={`tg-deduction-question__btn ${discoveryAnswers[q.key] === true ? 'tg-deduction-question__btn--active-yes' : ''}`}
                                            onClick={() => onAnswerQuestion(q.key, true)}
                                        >Si</button>
                                        <button
                                            className={`tg-deduction-question__btn ${discoveryAnswers[q.key] === false ? 'tg-deduction-question__btn--active-no' : ''}`}
                                            onClick={() => onAnswerQuestion(q.key, false)}
                                        >No</button>
                                    </div>
                                    <span className="tg-deduction-question__for">{q.deduction_name}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {!discoveryError && discoveryResult && discoveryResult.eligible.length === 0 && discoveryResult.missing_questions.length === 0 && !discoveryLoading && (
                        <p className="tg-discovery__empty">No se encontraron deducciones adicionales para tu situación.</p>
                    )}
                </div>
            )}
        </div>
    )
}

// === Step 7: Resultado ===

function StepResultado({ result, loading, onSaveProfile, savingProfile, saveProfileDone, discoveryResult }: {
    result: any; loading: boolean; onSaveProfile: () => void; savingProfile: boolean; saveProfileDone: boolean
    discoveryResult: any
}) {
    if (!result || !result.success) {
        return (
            <div className="tg-step">
                <h2 className="tg-step__title">Resultado de la estimación</h2>
                <p className="tg-step__desc">{loading ? 'Calculando tu estimación...' : 'Completa los pasos anteriores para ver tu resultado.'}</p>
            </div>
        )
    }

    const isRefund = result.resultado_estimado < 0
    const abs = Math.abs(result.resultado_estimado)

    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Resultado de la estimación</h2>

            <div className={`tg-result-card ${isRefund ? 'tg-result-card--refund' : 'tg-result-card--payment'}`}>
                <span className="tg-result-card__label">{isRefund ? 'Hacienda te devuelve' : 'A pagar a Hacienda'}</span>
                <span className="tg-result-card__amount">{abs.toLocaleString('es-ES', { minimumFractionDigits: 2 })} EUR</span>
            </div>

            <div className="tg-breakdown">
                <h3 className="tg-breakdown__title">Desglose</h3>
                <div className="tg-breakdown__grid">
                    <BreakdownRow label="Base imponible general" value={result.base_imponible_general} />
                    <BreakdownRow label="Base imponible ahorro" value={result.base_imponible_ahorro} />
                    {result.renta_imputada_inmuebles > 0 && <BreakdownRow label="Renta imputada inmuebles" value={result.renta_imputada_inmuebles} />}
                    <BreakdownRow label="Cuota integra general" value={result.cuota_integra_general} />
                    <BreakdownRow label="Cuota integra ahorro" value={result.cuota_integra_ahorro} />
                    <BreakdownRow label="Cuota liquida total" value={result.cuota_liquida_total} />
                    <BreakdownRow label="Retenciones pagadas" value={result.retenciones_pagadas} prefix="-" />
                    {result.deduccion_ceuta_melilla > 0 && <BreakdownRow label="Deduccion Ceuta/Melilla (60%)" value={result.deduccion_ceuta_melilla} prefix="-" />}
                    <BreakdownRow label="Tipo medio efectivo" value={result.tipo_medio_efectivo} suffix="%" />
                </div>

                {(result.reduccion_planes_pensiones > 0 || result.reduccion_tributacion_conjunta > 0) && (
                    <>
                        <h3 className="tg-breakdown__title">Reducciones aplicadas</h3>
                        <div className="tg-breakdown__grid">
                            {result.reduccion_planes_pensiones > 0 && <BreakdownRow label="Planes de pensiones" value={result.reduccion_planes_pensiones} prefix="-" />}
                            {result.reduccion_tributacion_conjunta > 0 && <BreakdownRow label="Tributacion conjunta" value={result.reduccion_tributacion_conjunta} prefix="-" />}
                        </div>
                    </>
                )}

                {(result.total_deducciones_cuota > 0 || result.deduccion_alquiler_pre2015 > 0) && (
                    <>
                        <h3 className="tg-breakdown__title">Deducciones en cuota</h3>
                        <div className="tg-breakdown__grid">
                            {result.deduccion_vivienda_pre2013 > 0 && <BreakdownRow label="Vivienda habitual (pre-2013)" value={result.deduccion_vivienda_pre2013} prefix="-" />}
                            {result.deduccion_alquiler_pre2015 > 0 && <BreakdownRow label="Alquiler vivienda (pre-2015)" value={result.deduccion_alquiler_pre2015} prefix="-" />}
                            {result.deduccion_maternidad > 0 && <BreakdownRow label="Maternidad" value={result.deduccion_maternidad} prefix="-" />}
                            {result.deduccion_familia_numerosa > 0 && <BreakdownRow label="Familia numerosa" value={result.deduccion_familia_numerosa} prefix="-" />}
                            {result.deduccion_donativos > 0 && <BreakdownRow label="Donativos" value={result.deduccion_donativos} prefix="-" />}
                        </div>
                    </>
                )}

                {result.trabajo && (
                    <>
                        <h3 className="tg-breakdown__title">Rendimientos del trabajo</h3>
                        <div className="tg-breakdown__grid">
                            <BreakdownRow label="Ingresos brutos" value={result.trabajo.ingresos_brutos} />
                            <BreakdownRow label="Gastos deducibles (SS)" value={result.trabajo.gastos_deducibles} prefix="-" />
                            <BreakdownRow label="Reduccion por trabajo" value={result.trabajo.reduccion_trabajo} prefix="-" />
                            <BreakdownRow label="Rendimiento neto reducido" value={result.trabajo.rendimiento_neto} />
                        </div>
                    </>
                )}

                {result.actividad && result.actividad.ingresos_actividad > 0 && (
                    <>
                        <h3 className="tg-breakdown__title">Rendimientos de actividad economica</h3>
                        <div className="tg-breakdown__grid">
                            <BreakdownRow label="Ingresos de actividad" value={result.actividad.ingresos_actividad} />
                            <BreakdownRow label="Gastos deducibles" value={result.actividad.total_gastos_deducibles} prefix="-" />
                            {result.actividad.gastos_dificil_justificacion > 0 && <BreakdownRow label="Gastos dificil justificacion (5%)" value={result.actividad.gastos_dificil_justificacion} prefix="-" />}
                            <BreakdownRow label="Rendimiento neto" value={result.actividad.rendimiento_neto} />
                            {result.actividad.reduccion_aplicada > 0 && <BreakdownRow label={`Reducción (${result.actividad.tipo_reduccion === 'inicio_actividad_art32_3' ? 'inicio actividad 20%' : 'TRADE Art. 32.2'})`} value={result.actividad.reduccion_aplicada} prefix="-" />}
                            <BreakdownRow label="Rendimiento neto reducido" value={result.actividad.rendimiento_neto_reducido} />
                        </div>
                    </>
                )}
            </div>

            {/* Phase B: Show discovered deductions in result */}
            {discoveryResult && discoveryResult.maybe_eligible && discoveryResult.maybe_eligible.length > 0 && (
                <div className="tg-result-deductions">
                    <h3 className="tg-breakdown__title">Deducciones que podrias reclamar</h3>
                    <div className="tg-result-deductions__list">
                        {discoveryResult.maybe_eligible.slice(0, 4).map((d: any) => (
                            <div key={d.code} className="tg-deduction-card tg-deduction-card--maybe">
                                <div className="tg-deduction-card__header">
                                    <Info size={14} />
                                    <strong>{d.name}</strong>
                                </div>
                                {d.max_amount && <span className="tg-deduction-card__badge">Hasta {d.max_amount.toLocaleString('es-ES')} EUR</span>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <p className="tg-disclaimer">
                Esta estimación es orientativa y no constituye asesoramiento fiscal.
                Los cálculos se basan en las escalas y deducciones vigentes.
                Para una declaración precisa, consulta con un asesor fiscal.
            </p>

            {saveProfileDone ? (
                <div className="tg-save-done">
                    <CheckCircle size={18} />
                    <span>Datos guardados en tu perfil fiscal</span>
                </div>
            ) : (
                <button
                    className="tg-nav__btn tg-nav__btn--primary"
                    onClick={onSaveProfile}
                    disabled={savingProfile}
                    style={{ marginTop: 'var(--spacing-4)', width: '100%' }}
                >
                    {savingProfile ? 'Guardando...' : 'Guardar en mi perfil'}
                </button>
            )}
        </div>
    )
}

function BreakdownRow({ label, value, prefix, suffix = 'EUR' }: {
    label: string; value: number; prefix?: string; suffix?: string
}) {
    return (
        <div className="tg-breakdown__row">
            <span className="tg-breakdown__label">{label}</span>
            <span className="tg-breakdown__value">
                {prefix}{value.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {suffix}
            </span>
        </div>
    )
}

interface StepProps {
    data: TaxGuideData
    update: (partial: Partial<TaxGuideData>) => void
}

// === Helper: build deduction discovery answers from wizard data ===

function buildAnswersFromData(data: TaxGuideData, extra: Record<string, boolean>): Record<string, any> {
    const answers: Record<string, any> = { ...extra }
    const currentYear = new Date().getFullYear()

    if (data.hipoteca_pre2013) {
        answers.adquisicion_antes_2013 = true
        answers.deducia_antes_2013 = true
    }
    if (data.madre_trabajadora_ss) answers.madre_trabajadora = true
    if (data.num_descendientes > 0) answers.tiene_hijos = true
    if (data.anios_nacimiento_desc?.some(y => (currentYear - y) < 3)) answers.hijo_menor_3 = true
    if (data.familia_numerosa) answers.familia_numerosa = true
    if (data.ceuta_melilla) answers.residente_ceuta_melilla = true
    if (data.donativos_ley_49_2002 > 0) answers.donativo_a_entidad_acogida = true
    if (data.discapacidad_contribuyente >= 33) answers.discapacidad_reconocida = true
    if (data.num_ascendientes_65 > 0 || data.num_ascendientes_75 > 0) answers.ascendiente_a_cargo = true
    if (data.alquiler_habitual_pre2015) answers.contrato_antes_2015 = true

    return answers
}

// === Main component ===

export default function TaxGuidePage() {
    const { step, data, updateData, nextStep, prevStep, goToStep, resetAll, stepLabels } = useTaxGuideProgress()
    const { result, loading, estimate } = useIrpfEstimator()
    const { profile, loading: profileLoading, save } = useFiscalProfile()
    const { result: discoveryResult, loading: discoveryLoading, error: discoveryError, discover } = useDeductionDiscovery()
    const profileAppliedRef = useRef(false)
    const [savingProfile, setSavingProfile] = useState(false)
    const [saveProfileDone, setSaveProfileDone] = useState(false)
    const [discoveryAnswers, setDiscoveryAnswers] = useState<Record<string, boolean>>({})
    const [zeroIncomeAcknowledged, setZeroIncomeAcknowledged] = useState(false)
    const [dynamicFormValues, setDynamicFormValues] = useState<Record<string, any>>({})

    // Phase D: step animation
    const [slideDir, setSlideDir] = useState<'left' | 'right' | ''>('')

    const isQuick = data.wizard_mode === 'quick'
    const icons = isQuick ? QUICK_STEP_ICONS : STEP_ICONS

    // Pre-fill from fiscal profile once the API has loaded
    useEffect(() => {
        if (profileLoading || profileAppliedRef.current) return
        if (!profile.ccaa_residencia) return // No profile saved yet
        profileAppliedRef.current = true

        // Compute edad from fecha_nacimiento if available
        let edad = data.edad_contribuyente
        if (profile.fecha_nacimiento) {
            const birth = new Date(profile.fecha_nacimiento)
            const today = new Date()
            edad = today.getFullYear() - birth.getFullYear()
            if (today.getMonth() < birth.getMonth() ||
                (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) {
                edad--
            }
        }

        updateData({
            comunidad_autonoma: profile.ccaa_residencia,
            edad_contribuyente: edad,
            ceuta_melilla: profile.ceuta_melilla || false,
            ingresos_trabajo: profile.ingresos_trabajo || 0,
            ss_empleado: profile.ss_empleado || 0,
            intereses: profile.intereses || 0,
            dividendos: profile.dividendos || 0,
            ganancias_fondos: profile.ganancias_fondos || 0,
            ingresos_alquiler: profile.ingresos_alquiler || 0,
            valor_adquisicion_inmueble: profile.valor_adquisicion_inmueble || 0,
            num_descendientes: profile.num_descendientes || 0,
            anios_nacimiento_desc: profile.anios_nacimiento_desc || [],
            custodia_compartida: profile.custodia_compartida || false,
            num_ascendientes_65: profile.num_ascendientes_65 || 0,
            num_ascendientes_75: profile.num_ascendientes_75 || 0,
            discapacidad_contribuyente: profile.discapacidad_contribuyente || 0,
            aportaciones_plan_pensiones: profile.aportaciones_plan_pensiones || 0,
            aportaciones_plan_pensiones_empresa: profile.aportaciones_plan_pensiones_empresa || 0,
            hipoteca_pre2013: profile.hipoteca_pre2013 || false,
            capital_amortizado_hipoteca: profile.capital_amortizado_hipoteca || 0,
            intereses_hipoteca: profile.intereses_hipoteca || 0,
            madre_trabajadora_ss: profile.madre_trabajadora_ss || false,
            gastos_guarderia_anual: profile.gastos_guarderia_anual || 0,
            familia_numerosa: profile.familia_numerosa || false,
            tipo_familia_numerosa: profile.tipo_familia_numerosa || 'general',
            donativos_ley_49_2002: profile.donativos_ley_49_2002 || 0,
            donativo_recurrente: profile.donativo_recurrente || false,
            retenciones_trabajo: profile.retenciones_trabajo || 0,
            retenciones_alquiler: profile.retenciones_alquiler || 0,
            retenciones_ahorro: profile.retenciones_ahorro || 0,
            // Phase 2 fields
            tributacion_conjunta: profile.tributacion_conjunta || false,
            tipo_unidad_familiar: profile.tipo_unidad_familiar || 'matrimonio',
            alquiler_habitual_pre2015: profile.alquiler_habitual_pre2015 || false,
            alquiler_pagado_anual: profile.alquiler_pagado_anual || 0,
            valor_catastral_segundas_viviendas: profile.valor_catastral_segundas_viviendas || 0,
            valor_catastral_revisado_post1994: profile.valor_catastral_revisado_post1994 ?? true,
            // Activity income
            ingresos_actividad: profile.ingresos_actividad || 0,
            gastos_actividad: profile.gastos_actividad || 0,
            cuota_autonomo_anual: profile.cuota_autonomo_anual || 0,
            amortizaciones_actividad: profile.amortizaciones_actividad || 0,
            provisiones_actividad: profile.provisiones_actividad || 0,
            otros_gastos_actividad: profile.otros_gastos_actividad || 0,
            estimacion_actividad: profile.estimacion_actividad || 'directa_simplificada',
            inicio_actividad: profile.inicio_actividad || false,
            un_solo_cliente: profile.un_solo_cliente || false,
            retenciones_actividad: profile.retenciones_actividad || 0,
            pagos_fraccionados_130: profile.pagos_fraccionados_130 || 0,
            // Phase 3 fields
            num_pagas_anuales: (profile.num_pagas_anuales as 12 | 14) || 14,
            salario_base_mensual: profile.salario_base_mensual || 0,
            complementos_salariales: profile.complementos_salariales || 0,
            irpf_retenido_porcentaje: profile.irpf_retenido_porcentaje || 0,
        })
    }, [profileLoading, profile]) // eslint-disable-line react-hooks/exhaustive-deps

    // Save wizard data to fiscal profile
    const handleSaveProfile = useCallback(async () => {
        setSavingProfile(true)
        const ok = await save({
            ccaa_residencia: data.comunidad_autonoma || null,
            ingresos_trabajo: data.ingresos_trabajo || null,
            ss_empleado: data.ss_empleado || null,
            intereses: data.intereses || null,
            dividendos: data.dividendos || null,
            ganancias_fondos: data.ganancias_fondos || null,
            ingresos_alquiler: data.ingresos_alquiler || null,
            valor_adquisicion_inmueble: data.valor_adquisicion_inmueble || null,
            num_descendientes: data.num_descendientes || null,
            anios_nacimiento_desc: data.anios_nacimiento_desc.length > 0 ? data.anios_nacimiento_desc : null,
            custodia_compartida: data.custodia_compartida,
            num_ascendientes_65: data.num_ascendientes_65 || null,
            num_ascendientes_75: data.num_ascendientes_75 || null,
            discapacidad_contribuyente: data.discapacidad_contribuyente || null,
            aportaciones_plan_pensiones: data.aportaciones_plan_pensiones || null,
            aportaciones_plan_pensiones_empresa: data.aportaciones_plan_pensiones_empresa || null,
            hipoteca_pre2013: data.hipoteca_pre2013,
            capital_amortizado_hipoteca: data.capital_amortizado_hipoteca || null,
            intereses_hipoteca: data.intereses_hipoteca || null,
            madre_trabajadora_ss: data.madre_trabajadora_ss,
            gastos_guarderia_anual: data.gastos_guarderia_anual || null,
            familia_numerosa: data.familia_numerosa,
            tipo_familia_numerosa: data.tipo_familia_numerosa || null,
            donativos_ley_49_2002: data.donativos_ley_49_2002 || null,
            donativo_recurrente: data.donativo_recurrente,
            retenciones_trabajo: data.retenciones_trabajo || null,
            retenciones_alquiler: data.retenciones_alquiler || null,
            retenciones_ahorro: data.retenciones_ahorro || null,
            // Activity income
            ingresos_actividad: data.ingresos_actividad || null,
            gastos_actividad: data.gastos_actividad || null,
            cuota_autonomo_anual: data.cuota_autonomo_anual || null,
            amortizaciones_actividad: data.amortizaciones_actividad || null,
            provisiones_actividad: data.provisiones_actividad || null,
            otros_gastos_actividad: data.otros_gastos_actividad || null,
            estimacion_actividad: data.estimacion_actividad || null,
            inicio_actividad: data.inicio_actividad,
            un_solo_cliente: data.un_solo_cliente,
            retenciones_actividad: data.retenciones_actividad || null,
            pagos_fraccionados_130: data.pagos_fraccionados_130 || null,
            // Phase 3
            num_pagas_anuales: data.num_pagas_anuales,
            salario_base_mensual: data.salario_base_mensual || null,
            complementos_salariales: data.complementos_salariales || null,
            irpf_retenido_porcentaje: data.irpf_retenido_porcentaje || null,
        })
        setSavingProfile(false)
        if (ok) setSaveProfileDone(true)
    }, [data, save])

    // Trigger estimate whenever data changes
    useEffect(() => {
        estimate({
            comunidad_autonoma: data.comunidad_autonoma,
            year: 2025,
            ingresos_trabajo: data.ingresos_trabajo,
            ss_empleado: data.ss_empleado,
            retenciones_trabajo: data.retenciones_trabajo,
            intereses: data.intereses,
            dividendos: data.dividendos,
            ganancias_fondos: data.ganancias_fondos,
            ingresos_alquiler: data.ingresos_alquiler,
            gastos_alquiler_total: data.gastos_alquiler_total,
            valor_adquisicion_inmueble: data.valor_adquisicion_inmueble,
            edad_contribuyente: data.edad_contribuyente,
            num_descendientes: data.num_descendientes,
            anios_nacimiento_desc: data.anios_nacimiento_desc,
            custodia_compartida: data.custodia_compartida,
            num_ascendientes_65: data.num_ascendientes_65,
            num_ascendientes_75: data.num_ascendientes_75,
            discapacidad_contribuyente: data.discapacidad_contribuyente,
            ceuta_melilla: data.ceuta_melilla,
            aportaciones_plan_pensiones: data.aportaciones_plan_pensiones,
            aportaciones_plan_pensiones_empresa: data.aportaciones_plan_pensiones_empresa,
            hipoteca_pre2013: data.hipoteca_pre2013,
            capital_amortizado_hipoteca: data.capital_amortizado_hipoteca,
            intereses_hipoteca: data.intereses_hipoteca,
            madre_trabajadora_ss: data.madre_trabajadora_ss,
            gastos_guarderia_anual: data.gastos_guarderia_anual,
            familia_numerosa: data.familia_numerosa,
            tipo_familia_numerosa: data.tipo_familia_numerosa,
            donativos_ley_49_2002: data.donativos_ley_49_2002,
            donativo_recurrente: data.donativo_recurrente,
            retenciones_alquiler: data.retenciones_alquiler,
            retenciones_ahorro: data.retenciones_ahorro,
            tributacion_conjunta: data.tributacion_conjunta,
            tipo_unidad_familiar: data.tipo_unidad_familiar,
            alquiler_habitual_pre2015: data.alquiler_habitual_pre2015,
            alquiler_pagado_anual: data.alquiler_pagado_anual,
            valor_catastral_segundas_viviendas: data.valor_catastral_segundas_viviendas,
            valor_catastral_revisado_post1994: data.valor_catastral_revisado_post1994,
            // Activity income
            ingresos_actividad: data.ingresos_actividad,
            gastos_actividad: data.gastos_actividad,
            cuota_autonomo_anual: data.cuota_autonomo_anual,
            amortizaciones_actividad: data.amortizaciones_actividad,
            provisiones_actividad: data.provisiones_actividad,
            otros_gastos_actividad: data.otros_gastos_actividad,
            estimacion_actividad: data.estimacion_actividad,
            inicio_actividad: data.inicio_actividad,
            un_solo_cliente: data.un_solo_cliente,
            retenciones_actividad: data.retenciones_actividad,
            pagos_fraccionados_130: data.pagos_fraccionados_130,
            // Phase 3
            num_pagas_anuales: data.num_pagas_anuales,
            salario_base_mensual: data.salario_base_mensual,
            complementos_salariales: data.complementos_salariales,
            irpf_retenido_porcentaje: data.irpf_retenido_porcentaje,
            // Inversiones y cripto
            cripto_ganancia_neta: data.cripto_ganancia_neta,
            cripto_perdida_neta: data.cripto_perdida_neta,
            ganancias_acciones: data.ganancias_acciones,
            perdidas_acciones: data.perdidas_acciones,
            ganancias_reembolso_fondos: data.ganancias_reembolso_fondos,
            perdidas_reembolso_fondos: data.perdidas_reembolso_fondos,
            ganancias_derivados: data.ganancias_derivados,
            perdidas_derivados: data.perdidas_derivados,
            premios_metalico_privados: data.premios_metalico_privados,
            perdidas_juegos_privados: data.perdidas_juegos_privados,
            premios_metalico_publicos: data.premios_metalico_publicos,
        })
    }, [data, estimate])

    // Phase B: Trigger deduction discovery when on step 6 (Deducciones) or result step
    const isDeductionStep = isQuick ? step === 1 : step >= 6
    useEffect(() => {
        if (isDeductionStep && data.comunidad_autonoma) {
            const answers = buildAnswersFromData(data, discoveryAnswers)
            discover(data.comunidad_autonoma, answers)
        }
    }, [isDeductionStep, data.comunidad_autonoma, data.num_descendientes, data.madre_trabajadora_ss, data.familia_numerosa, data.ceuta_melilla, data.hipoteca_pre2013, data.discapacidad_contribuyente, discoveryAnswers, discover]) // eslint-disable-line react-hooks/exhaustive-deps

    const handleAnswerQuestion = useCallback((key: string, value: boolean) => {
        setDiscoveryAnswers(prev => ({ ...prev, [key]: value }))
    }, [])

    // Phase D: animated step navigation
    const animatedGoTo = useCallback((target: number) => {
        setSlideDir(target > step ? 'right' : 'left')
        setTimeout(() => {
            goToStep(target)
            setSlideDir('')
        }, 150)
    }, [step, goToStep])

    const animatedNext = useCallback(() => {
        setSlideDir('right')
        setTimeout(() => { nextStep(); setSlideDir('') }, 150)
    }, [nextStep])

    const animatedPrev = useCallback(() => {
        setSlideDir('left')
        setTimeout(() => { prevStep(); setSlideDir('') }, 150)
    }, [prevStep])

    const handleDynamicFormChange = useCallback((key: string, value: any) => {
        setDynamicFormValues(prev => ({ ...prev, [key]: value }))
    }, [])

    // Render step content (8 steps: 0-7)
    const renderFullStep = () => {
        switch (step) {
            case 0: return <StepPersonal data={data} update={updateData} />
            case 1: return (
                <StepTrabajo
                    data={data}
                    update={updateData}
                    zeroIncomeAcknowledged={zeroIncomeAcknowledged}
                    onAcknowledgeZeroIncome={setZeroIncomeAcknowledged}
                />
            )
            case 2: return <StepAhorro data={data} update={updateData} />
            case 3: return <StepInmuebles data={data} update={updateData} />
            case 4: return <StepInversiones data={data} update={updateData} />
            case 5: return <StepFamilia data={data} update={updateData} />
            case 6: return (
                <StepDeducciones
                    data={data}
                    update={updateData}
                    discoveryResult={discoveryResult}
                    discoveryLoading={discoveryLoading}
                    discoveryError={discoveryError}
                    discoveryAnswers={discoveryAnswers}
                    onAnswerQuestion={handleAnswerQuestion}
                    dynamicFormValues={dynamicFormValues}
                    onDynamicFormChange={handleDynamicFormChange}
                />
            )
            case 7: return <StepResultado result={result} loading={loading} onSaveProfile={handleSaveProfile} savingProfile={savingProfile} saveProfileDone={saveProfileDone} discoveryResult={discoveryResult} />
            default: return null
        }
    }

    const renderQuickStep = () => {
        switch (step) {
            case 0:
                return (
                    <div className="tg-step">
                        <StepPersonal data={data} update={updateData} />
                        <div style={{ marginTop: 'var(--spacing-6)' }}>
                            <StepTrabajo
                                data={data}
                                update={updateData}
                                zeroIncomeAcknowledged={zeroIncomeAcknowledged}
                                onAcknowledgeZeroIncome={setZeroIncomeAcknowledged}
                            />
                        </div>
                    </div>
                )
            case 1:
                return <StepResultado result={result} loading={loading} onSaveProfile={handleSaveProfile} savingProfile={savingProfile} saveProfileDone={saveProfileDone} discoveryResult={discoveryResult} />
            default: return null
        }
    }

    const stepContent = useMemo(() => {
        return isQuick ? renderQuickStep() : renderFullStep()
    }, [step, data, updateData, result, loading, handleSaveProfile, savingProfile, saveProfileDone, discoveryResult, discoveryLoading, discoveryAnswers, handleAnswerQuestion, isQuick]) // eslint-disable-line react-hooks/exhaustive-deps

    const isFirstStep = step === 0
    const isLastStep = step === stepLabels.length - 1

    // B-GF-06: step-specific validation
    const getEffectiveIngresos = () => {
        if (data.salary_input_mode === 'monthly') {
            return (data.salario_base_mensual + data.complementos_salariales) * data.num_pagas_anuales
        }
        return data.ingresos_trabajo
    }
    const step1HasIncome = !isQuick
        ? (getEffectiveIngresos() > 0 || data.ingresos_actividad > 0 || zeroIncomeAcknowledged)
        : true // quick mode combines steps 0+1, validation handled by CCAA check
    const canProceed = (() => {
        if (isQuick) return !!data.comunidad_autonoma
        if (step === 0) return !!data.comunidad_autonoma
        if (step === 1) return step1HasIncome
        return true
    })()

    // Block clicking directly on the result step in progress bar without required data
    const canGoToStep = (targetStep: number) => {
        if (isQuick) return !!data.comunidad_autonoma || targetStep === 0
        // For result step (7), require CCAA + income
        if (targetStep >= stepLabels.length - 1) {
            return !!data.comunidad_autonoma && step1HasIncome
        }
        // For step 1+, require CCAA
        if (targetStep >= 1) return !!data.comunidad_autonoma
        return true
    }

    return (
        <div className="tax-guide">
            <Header />

            <div className="tax-guide__header">
                <h1 className="tax-guide__header-title">
                    Simulador <span>IRPF</span>
                </h1>
                <p className="tax-guide__header-desc">
                    Calcula tu declaración de la renta con todas las deducciones de tu comunidad autónoma
                </p>
            </div>

            <div className="tax-guide__layout">
                <aside className="tax-guide__sidebar">
                    <LiveEstimatorBar result={result} loading={loading} />
                </aside>

                <main className="tax-guide__main">
                    {/* Progress bar */}
                    <div className="tg-progress">
                        {stepLabels.map((label, i) => {
                            const Icon = icons[i] || BarChart3
                            return (
                                <button
                                    key={i}
                                    className={`tg-progress__step ${i === step ? 'tg-progress__step--active' : ''} ${i < step ? 'tg-progress__step--done' : ''}`}
                                    onClick={() => canGoToStep(i) && animatedGoTo(i)}
                                    disabled={!canGoToStep(i)}
                                    title={label}
                                >
                                    <Icon size={16} />
                                    <span className="tg-progress__label">{label}</span>
                                </button>
                            )
                        })}
                    </div>

                    {/* Step content with animation */}
                    <div className={`tg-step-container ${slideDir ? `tg-step-container--slide-${slideDir}` : ''}`}>
                        {stepContent}
                    </div>

                    {/* Navigation */}
                    <div className="tg-nav">
                        <button className="tg-nav__btn tg-nav__btn--secondary" onClick={animatedPrev} disabled={isFirstStep}>
                            <ChevronLeft size={18} /> Anterior
                        </button>

                        <button className="tg-nav__btn tg-nav__btn--ghost" onClick={() => { profileAppliedRef.current = false; resetAll() }} title="Empezar de nuevo">
                            <RotateCcw size={16} />
                        </button>

                        {!isLastStep && (
                            <button className="tg-nav__btn tg-nav__btn--primary" onClick={animatedNext} disabled={!canProceed}>
                                Siguiente <ChevronRight size={18} />
                            </button>
                        )}
                    </div>
                </main>
            </div>

            <div className="tax-guide__mobile-bar">
                <LiveEstimatorBar result={result} loading={loading} />
            </div>
        </div>
    )
}
