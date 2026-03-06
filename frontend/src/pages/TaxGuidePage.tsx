import { useEffect, useMemo, useState, useCallback } from 'react'
import { ChevronLeft, ChevronRight, RotateCcw, MapPin, Briefcase, PiggyBank, Home as HomeIcon, Users, Gift, BarChart3, CheckCircle } from 'lucide-react'
import Header from '../components/Header'
import LiveEstimatorBar from '../components/LiveEstimatorBar'
import { useTaxGuideProgress, STEP_LABELS, type TaxGuideData } from '../hooks/useTaxGuideProgress'
import { useIrpfEstimator } from '../hooks/useIrpfEstimator'
import { useFiscalProfile } from '../hooks/useFiscalProfile'
import './TaxGuidePage.css'

const CCAA_OPTIONS = [
    'Andalucia', 'Aragon', 'Asturias', 'Baleares', 'Canarias',
    'Cantabria', 'Castilla-La Mancha', 'Castilla y Leon', 'Cataluna',
    'Ceuta', 'Comunidad Valenciana', 'Extremadura', 'Galicia',
    'La Rioja', 'Madrid', 'Melilla', 'Murcia', 'Navarra',
    'Pais Vasco - Araba', 'Pais Vasco - Bizkaia', 'Pais Vasco - Gipuzkoa',
]

const STEP_ICONS = [MapPin, Briefcase, PiggyBank, HomeIcon, Users, Gift, BarChart3]

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

// Step 1: Datos personales
function StepPersonal({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Datos personales</h2>
            <p className="tg-step__desc">Necesitamos saber donde resides para aplicar las escalas correctas.</p>

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

            <NumberInput
                label="Edad"
                value={data.edad_contribuyente}
                onChange={v => update({ edad_contribuyente: v })}
                min={16} step={1}
            />

            <CheckboxInput
                label="Tributacion conjunta"
                checked={data.tributacion_conjunta}
                onChange={v => update({ tributacion_conjunta: v })}
                help="Permite declarar con tu unidad familiar. Aplica una reduccion fija sobre la base imponible."
            />

            {data.tributacion_conjunta && (
                <div className="tg-field">
                    <label className="tg-field__label">Tipo de unidad familiar</label>
                    <select
                        className="tg-field__select"
                        value={data.tipo_unidad_familiar}
                        onChange={e => update({ tipo_unidad_familiar: e.target.value })}
                    >
                        <option value="matrimonio">Matrimonio (reduccion 3.400 EUR)</option>
                        <option value="monoparental">Monoparental (reduccion 2.150 EUR)</option>
                    </select>
                </div>
            )}
        </div>
    )
}

// Step 2: Trabajo
function StepTrabajo({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Rendimientos del trabajo</h2>
            <p className="tg-step__desc">Incluye tu salario bruto anual, cotizaciones y retenciones.</p>

            <NumberInput
                label="Salario bruto anual"
                value={data.ingresos_trabajo}
                onChange={v => update({ ingresos_trabajo: v })}
                suffix="EUR"
                help="Suma de todas tus nominas brutas del ano"
            />
            <NumberInput
                label="Cotizaciones a la Seguridad Social"
                value={data.ss_empleado}
                onChange={v => update({ ss_empleado: v })}
                suffix="EUR"
                help="Aparece en tu nomina como 'SS empleado'"
            />
            <NumberInput
                label="Retenciones de IRPF practicadas"
                value={data.retenciones_trabajo}
                onChange={v => update({ retenciones_trabajo: v })}
                suffix="EUR"
                help="Total retenido por tu empresa durante el ano"
            />
        </div>
    )
}

// Step 3: Ahorro
function StepAhorro({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Ahorro e inversiones</h2>
            <p className="tg-step__desc">Intereses, dividendos y ganancias patrimoniales tributan en la base del ahorro.</p>

            <NumberInput
                label="Intereses de cuentas/depositos"
                value={data.intereses}
                onChange={v => update({ intereses: v })}
                suffix="EUR"
            />
            <NumberInput
                label="Dividendos"
                value={data.dividendos}
                onChange={v => update({ dividendos: v })}
                suffix="EUR"
            />
            <NumberInput
                label="Ganancias de fondos/acciones"
                value={data.ganancias_fondos}
                onChange={v => update({ ganancias_fondos: v })}
                suffix="EUR"
                help="Ganancias netas realizadas (ventas - compras)"
            />
            <NumberInput
                label="Retenciones sobre capital mobiliario"
                value={data.retenciones_ahorro}
                onChange={v => update({ retenciones_ahorro: v })}
                suffix="EUR"
                help="19% retenido por bancos sobre intereses y dividendos"
            />
        </div>
    )
}

// Step 4: Inmuebles
function StepInmuebles({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Inmuebles y alquileres</h2>
            <p className="tg-step__desc">Si alquilas un inmueble, indica los ingresos y gastos asociados.</p>

            <NumberInput
                label="Ingresos por alquiler (anual)"
                value={data.ingresos_alquiler}
                onChange={v => update({ ingresos_alquiler: v })}
                suffix="EUR"
            />
            <NumberInput
                label="Gastos deducibles del alquiler"
                value={data.gastos_alquiler_total}
                onChange={v => update({ gastos_alquiler_total: v })}
                suffix="EUR"
                help="IBI, comunidad, seguros, reparaciones, intereses hipoteca..."
            />
            <NumberInput
                label="Valor de adquisicion del inmueble"
                value={data.valor_adquisicion_inmueble}
                onChange={v => update({ valor_adquisicion_inmueble: v })}
                suffix="EUR"
                help="Para calcular la amortizacion (3% anual)"
            />
            <NumberInput
                label="Retenciones sobre alquileres"
                value={data.retenciones_alquiler}
                onChange={v => update({ retenciones_alquiler: v })}
                suffix="EUR"
                help="19% retenido por inquilinos empresas/profesionales"
            />

            <h3 className="tg-step__subtitle">Alquiler como inquilino</h3>
            <CheckboxInput
                label="Tengo contrato de alquiler anterior al 1/1/2015"
                checked={data.alquiler_habitual_pre2015}
                onChange={v => update({ alquiler_habitual_pre2015: v })}
                help="Regimen transitorio: deduccion del 10,05% sobre el alquiler pagado (max. 9.040 EUR/ano)"
            />
            {data.alquiler_habitual_pre2015 && (
                <NumberInput
                    label="Alquiler anual pagado"
                    value={data.alquiler_pagado_anual}
                    onChange={v => update({ alquiler_pagado_anual: v })}
                    suffix="EUR"
                    help="Deduccion del 10,05% sobre max 9.040 EUR"
                />
            )}

            <h3 className="tg-step__subtitle">Segundas viviendas</h3>
            <NumberInput
                label="Valor catastral de segundas viviendas"
                value={data.valor_catastral_segundas_viviendas}
                onChange={v => update({ valor_catastral_segundas_viviendas: v })}
                suffix="EUR"
                help="Viviendas no alquiladas ni vivienda habitual. Imputa 1,1%-2% como renta"
            />
            <CheckboxInput
                label="Valor catastral revisado despues de 1994"
                checked={data.valor_catastral_revisado_post1994}
                onChange={v => update({ valor_catastral_revisado_post1994: v })}
                help="Si fue revisado antes de 1994 se aplica el 2% en lugar del 1,1%"
            />
        </div>
    )
}

// Step 5: Familia
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

            <NumberInput
                label="Numero de hijos"
                value={data.num_descendientes}
                onChange={handleDescendientes}
                min={0} step={1}
            />

            {(data.anios_nacimiento_desc || []).map((y, i) => (
                <NumberInput
                    key={i}
                    label={`Ano de nacimiento - Hijo ${i + 1}`}
                    value={y}
                    onChange={v => updateBirthYear(i, v)}
                    min={1950} step={1}
                />
            ))}

            {data.num_descendientes > 0 && (
                <CheckboxInput
                    label="Custodia compartida"
                    checked={data.custodia_compartida}
                    onChange={v => update({ custodia_compartida: v })}
                />
            )}

            <NumberInput
                label="Ascendientes mayores de 65 anos"
                value={data.num_ascendientes_65}
                onChange={v => update({ num_ascendientes_65: v })}
                min={0} step={1}
            />
            <NumberInput
                label="Ascendientes mayores de 75 anos"
                value={data.num_ascendientes_75}
                onChange={v => update({ num_ascendientes_75: v })}
                min={0} step={1}
            />

            <div className="tg-field">
                <label className="tg-field__label">Grado de discapacidad</label>
                <select
                    className="tg-field__select"
                    value={data.discapacidad_contribuyente}
                    onChange={e => update({ discapacidad_contribuyente: parseInt(e.target.value) })}
                >
                    <option value={0}>Sin discapacidad</option>
                    <option value={33}>33% - 64%</option>
                    <option value={65}>65% o mas</option>
                </select>
            </div>

            <CheckboxInput
                label="Madre trabajadora dada de alta en la SS"
                checked={data.madre_trabajadora_ss}
                onChange={v => update({ madre_trabajadora_ss: v })}
                help="Deduccion por maternidad: 1.200 EUR/hijo menor de 3 anos"
            />

            {data.madre_trabajadora_ss && (
                <NumberInput
                    label="Gastos de guarderia (anual)"
                    value={data.gastos_guarderia_anual}
                    onChange={v => update({ gastos_guarderia_anual: v })}
                    suffix="EUR"
                    help="Hasta 1.000 EUR adicionales por hijo en guarderia autorizada"
                />
            )}

            <CheckboxInput
                label="Familia numerosa"
                checked={data.familia_numerosa}
                onChange={v => update({ familia_numerosa: v })}
            />

            {data.familia_numerosa && (
                <div className="tg-field">
                    <label className="tg-field__label">Tipo de familia numerosa</label>
                    <select
                        className="tg-field__select"
                        value={data.tipo_familia_numerosa}
                        onChange={e => update({ tipo_familia_numerosa: e.target.value })}
                    >
                        <option value="general">General (3-4 hijos) - 1.200 EUR</option>
                        <option value="especial">Especial (5+ hijos) - 2.400 EUR</option>
                    </select>
                </div>
            )}
        </div>
    )
}

// Step 6: Deducciones y reducciones
function StepDeducciones({ data, update }: StepProps) {
    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Deducciones y reducciones</h2>
            <p className="tg-step__desc">Estas deducciones reducen directamente tu cuota o tu base imponible.</p>

            <h3 className="tg-step__subtitle">Planes de pensiones</h3>
            <NumberInput
                label="Aportaciones propias a planes de pensiones"
                value={data.aportaciones_plan_pensiones}
                onChange={v => update({ aportaciones_plan_pensiones: v })}
                suffix="EUR"
                help="Maximo 1.500 EUR/ano (reducen la base imponible general)"
            />
            <NumberInput
                label="Aportaciones de la empresa"
                value={data.aportaciones_plan_pensiones_empresa}
                onChange={v => update({ aportaciones_plan_pensiones_empresa: v })}
                suffix="EUR"
                help="Limite conjunto con propias: 8.500 EUR"
            />

            <h3 className="tg-step__subtitle">Vivienda habitual (hipoteca anterior al 1/1/2013)</h3>
            <CheckboxInput
                label="Tengo hipoteca firmada antes del 1 de enero de 2013"
                checked={data.hipoteca_pre2013}
                onChange={v => update({ hipoteca_pre2013: v })}
                help="Regimen transitorio: deduccion del 15% sobre max 9.040 EUR/ano"
            />

            {data.hipoteca_pre2013 && (
                <>
                    <NumberInput
                        label="Capital amortizado en el ano"
                        value={data.capital_amortizado_hipoteca}
                        onChange={v => update({ capital_amortizado_hipoteca: v })}
                        suffix="EUR"
                        help="Principal pagado durante el ejercicio"
                    />
                    <NumberInput
                        label="Intereses de hipoteca pagados"
                        value={data.intereses_hipoteca}
                        onChange={v => update({ intereses_hipoteca: v })}
                        suffix="EUR"
                    />
                </>
            )}

            <h3 className="tg-step__subtitle">Donativos</h3>
            <NumberInput
                label="Donativos a entidades Ley 49/2002"
                value={data.donativos_ley_49_2002}
                onChange={v => update({ donativos_ley_49_2002: v })}
                suffix="EUR"
                help="ONGs, fundaciones... 80% primeros 250 EUR, 40% resto"
            />
            {data.donativos_ley_49_2002 > 0 && (
                <CheckboxInput
                    label="Donante recurrente (3+ anos misma entidad)"
                    checked={data.donativo_recurrente}
                    onChange={v => update({ donativo_recurrente: v })}
                    help="Sube al 45% el exceso sobre 250 EUR"
                />
            )}
        </div>
    )
}

// Step 7: Resultado
function StepResultado({ result, loading, onSaveProfile, savingProfile, saveProfileDone }: {
    result: any
    loading: boolean
    onSaveProfile: () => void
    savingProfile: boolean
    saveProfileDone: boolean
}) {
    if (!result || !result.success) {
        return (
            <div className="tg-step">
                <h2 className="tg-step__title">Resultado de la estimacion</h2>
                <p className="tg-step__desc">
                    {loading ? 'Calculando tu estimacion...' : 'Completa los pasos anteriores para ver tu resultado.'}
                </p>
            </div>
        )
    }

    const isRefund = result.resultado_estimado < 0
    const abs = Math.abs(result.resultado_estimado)

    return (
        <div className="tg-step">
            <h2 className="tg-step__title">Resultado de la estimacion</h2>

            <div className={`tg-result-card ${isRefund ? 'tg-result-card--refund' : 'tg-result-card--payment'}`}>
                <span className="tg-result-card__label">{isRefund ? 'Hacienda te devuelve' : 'A pagar a Hacienda'}</span>
                <span className="tg-result-card__amount">{abs.toLocaleString('es-ES', { minimumFractionDigits: 2 })} EUR</span>
            </div>

            <div className="tg-breakdown">
                <h3 className="tg-breakdown__title">Desglose</h3>
                <div className="tg-breakdown__grid">
                    <BreakdownRow label="Base imponible general" value={result.base_imponible_general} />
                    <BreakdownRow label="Base imponible ahorro" value={result.base_imponible_ahorro} />
                    {result.renta_imputada_inmuebles > 0 && (
                        <BreakdownRow label="Renta imputada inmuebles" value={result.renta_imputada_inmuebles} />
                    )}
                    <BreakdownRow label="Cuota integra general" value={result.cuota_integra_general} />
                    <BreakdownRow label="Cuota integra ahorro" value={result.cuota_integra_ahorro} />
                    <BreakdownRow label="Cuota liquida total" value={result.cuota_liquida_total} />
                    <BreakdownRow label="Retenciones pagadas" value={result.retenciones_pagadas} prefix="-" />
                    {result.deduccion_ceuta_melilla > 0 && (
                        <BreakdownRow label="Deduccion Ceuta/Melilla" value={result.deduccion_ceuta_melilla} prefix="-" />
                    )}
                    <BreakdownRow label="Tipo medio efectivo" value={result.tipo_medio_efectivo} suffix="%" />
                </div>

                {(result.reduccion_planes_pensiones > 0 || result.reduccion_tributacion_conjunta > 0) && (
                    <>
                        <h3 className="tg-breakdown__title">Reducciones aplicadas</h3>
                        <div className="tg-breakdown__grid">
                            {result.reduccion_planes_pensiones > 0 && (
                                <BreakdownRow label="Planes de pensiones" value={result.reduccion_planes_pensiones} prefix="-" />
                            )}
                            {result.reduccion_tributacion_conjunta > 0 && (
                                <BreakdownRow label="Tributacion conjunta" value={result.reduccion_tributacion_conjunta} prefix="-" />
                            )}
                        </div>
                    </>
                )}

                {(result.total_deducciones_cuota > 0 || result.deduccion_alquiler_pre2015 > 0) && (
                    <>
                        <h3 className="tg-breakdown__title">Deducciones en cuota</h3>
                        <div className="tg-breakdown__grid">
                            {result.deduccion_vivienda_pre2013 > 0 && (
                                <BreakdownRow label="Vivienda habitual (pre-2013)" value={result.deduccion_vivienda_pre2013} prefix="-" />
                            )}
                            {result.deduccion_alquiler_pre2015 > 0 && (
                                <BreakdownRow label="Alquiler vivienda habitual (pre-2015)" value={result.deduccion_alquiler_pre2015} prefix="-" />
                            )}
                            {result.deduccion_maternidad > 0 && (
                                <BreakdownRow label="Maternidad" value={result.deduccion_maternidad} prefix="-" />
                            )}
                            {result.deduccion_familia_numerosa > 0 && (
                                <BreakdownRow label="Familia numerosa" value={result.deduccion_familia_numerosa} prefix="-" />
                            )}
                            {result.deduccion_donativos > 0 && (
                                <BreakdownRow label="Donativos" value={result.deduccion_donativos} prefix="-" />
                            )}
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
            </div>

            <p className="tg-disclaimer">
                Esta estimacion es orientativa y no constituye asesoramiento fiscal.
                Los calculos se basan en las escalas y deducciones vigentes.
                Para una declaracion precisa, consulta con un asesor fiscal.
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

export default function TaxGuidePage() {
    const { step, data, updateData, nextStep, prevStep, goToStep, resetAll } = useTaxGuideProgress()
    const { result, loading, estimate } = useIrpfEstimator()
    const { profile, save } = useFiscalProfile()
    const [savingProfile, setSavingProfile] = useState(false)
    const [saveProfileDone, setSaveProfileDone] = useState(false)

    // Pre-fill from fiscal profile on first load (only if wizard is empty)
    useEffect(() => {
        if (!data.comunidad_autonoma && profile.ccaa_residencia) {
            updateData({
                comunidad_autonoma: profile.ccaa_residencia,
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
                // Phase 1 fields
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
            })
        }
    }, [profile.ccaa_residencia]) // eslint-disable-line react-hooks/exhaustive-deps

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
            // Phase 1 fields
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
        })
        setSavingProfile(false)
        if (ok) setSaveProfileDone(true)
    }, [data, save])

    // Trigger estimate whenever data changes (sends ALL fields including Phase 1)
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
            // Phase 1 fields
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
            // Phase 2 fields
            tributacion_conjunta: data.tributacion_conjunta,
            tipo_unidad_familiar: data.tipo_unidad_familiar,
            alquiler_habitual_pre2015: data.alquiler_habitual_pre2015,
            alquiler_pagado_anual: data.alquiler_pagado_anual,
            valor_catastral_segundas_viviendas: data.valor_catastral_segundas_viviendas,
            valor_catastral_revisado_post1994: data.valor_catastral_revisado_post1994,
        })
    }, [data, estimate])

    const stepContent = useMemo(() => {
        switch (step) {
            case 0: return <StepPersonal data={data} update={updateData} />
            case 1: return <StepTrabajo data={data} update={updateData} />
            case 2: return <StepAhorro data={data} update={updateData} />
            case 3: return <StepInmuebles data={data} update={updateData} />
            case 4: return <StepFamilia data={data} update={updateData} />
            case 5: return <StepDeducciones data={data} update={updateData} />
            case 6: return <StepResultado result={result} loading={loading} onSaveProfile={handleSaveProfile} savingProfile={savingProfile} saveProfileDone={saveProfileDone} />
            default: return null
        }
    }, [step, data, updateData, result, loading, handleSaveProfile, savingProfile, saveProfileDone])

    const isFirstStep = step === 0
    const isLastStep = step === STEP_LABELS.length - 1
    const canProceed = step === 0 ? !!data.comunidad_autonoma : true

    return (
        <div className="tax-guide">
            <Header />

            <div className="tax-guide__layout">
                {/* Desktop sidebar estimator */}
                <aside className="tax-guide__sidebar">
                    <LiveEstimatorBar result={result} loading={loading} />
                </aside>

                <main className="tax-guide__main">
                    {/* Progress bar */}
                    <div className="tg-progress">
                        {STEP_LABELS.map((label, i) => {
                            const Icon = STEP_ICONS[i]
                            return (
                                <button
                                    key={i}
                                    className={`tg-progress__step ${i === step ? 'tg-progress__step--active' : ''} ${i < step ? 'tg-progress__step--done' : ''}`}
                                    onClick={() => goToStep(i)}
                                    title={label}
                                >
                                    <Icon size={16} />
                                    <span className="tg-progress__label">{label}</span>
                                </button>
                            )
                        })}
                    </div>

                    {/* Step content */}
                    <div className="tg-step-container">
                        {stepContent}
                    </div>

                    {/* Navigation */}
                    <div className="tg-nav">
                        <button
                            className="tg-nav__btn tg-nav__btn--secondary"
                            onClick={prevStep}
                            disabled={isFirstStep}
                        >
                            <ChevronLeft size={18} /> Anterior
                        </button>

                        <button
                            className="tg-nav__btn tg-nav__btn--ghost"
                            onClick={resetAll}
                            title="Empezar de nuevo"
                        >
                            <RotateCcw size={16} />
                        </button>

                        {!isLastStep && (
                            <button
                                className="tg-nav__btn tg-nav__btn--primary"
                                onClick={nextStep}
                                disabled={!canProceed}
                            >
                                Siguiente <ChevronRight size={18} />
                            </button>
                        )}
                    </div>
                </main>
            </div>

            {/* Mobile sticky estimator bar */}
            <div className="tax-guide__mobile-bar">
                <LiveEstimatorBar result={result} loading={loading} />
            </div>
        </div>
    )
}
