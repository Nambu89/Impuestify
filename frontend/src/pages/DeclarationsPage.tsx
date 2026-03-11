import { useState, useEffect, useMemo } from 'react'
import { FileText, Calculator, TrendingUp, TrendingDown, Save, Loader2, ChevronDown, Trash2, BarChart3 } from 'lucide-react'
import Header from '../components/Header'
import { useDeclarations, type ModeloType, type Calculate303Input, type Calculate130Input, type Calculate420Input, type CalculateIpsiInput } from '../hooks/useDeclarations'
import { useFiscalProfile } from '../hooks/useFiscalProfile'
import CountUp from '../components/reactbits/CountUp'
import './DeclarationsPage.css'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const QUARTERS = [
    { value: 1, label: '1T (Ene-Mar)' },
    { value: 2, label: '2T (Abr-Jun)' },
    { value: 3, label: '3T (Jul-Sep)' },
    { value: 4, label: '4T (Oct-Dic)' },
]

const TERRITORIES_130 = [
    'Comun', 'Araba', 'Gipuzkoa', 'Bizkaia', 'Navarra',
]

function NumberInput({ label, value, onChange, suffix = '', help = '', step = 0.01 }: {
    label: string; value: number; onChange: (v: number) => void
    suffix?: string; help?: string; step?: number
}) {
    return (
        <div className="decl-field">
            <label className="decl-field__label">{label}</label>
            <div className="decl-field__input-wrap">
                <input
                    type="number"
                    className="decl-field__input"
                    value={value || ''}
                    onChange={e => onChange(parseFloat(e.target.value) || 0)}
                    step={step}
                    min={0}
                />
                {suffix && <span className="decl-field__suffix">{suffix}</span>}
            </div>
            {help && <span className="decl-field__help">{help}</span>}
        </div>
    )
}

function CheckboxInput({ label, checked, onChange }: {
    label: string; checked: boolean; onChange: (v: boolean) => void
}) {
    return (
        <label className="decl-checkbox">
            <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
            <span>{label}</span>
        </label>
    )
}

// ---------------------------------------------------------------------------
// Modelo 303 Form
// ---------------------------------------------------------------------------

function Form303({ data, onChange, quarter }: {
    data: Calculate303Input; onChange: (d: Calculate303Input) => void; quarter: number
}) {
    const u = (field: string, val: number) => onChange({ ...data, [field]: val, quarter })
    return (
        <div className="decl-form">
            <h3 className="decl-form__section">IVA Devengado (ventas)</h3>
            <div className="decl-form__grid">
                <NumberInput label="Base imponible 4%" value={data.base_4 || 0} onChange={v => u('base_4', v)} suffix="EUR" />
                <NumberInput label="Base imponible 10%" value={data.base_10 || 0} onChange={v => u('base_10', v)} suffix="EUR" />
                <NumberInput label="Base imponible 21%" value={data.base_21 || 0} onChange={v => u('base_21', v)} suffix="EUR" />
            </div>

            <details className="decl-form__details">
                <summary><ChevronDown size={16} /> Operaciones avanzadas</summary>
                <div className="decl-form__grid">
                    <NumberInput label="Base intracomunitarias" value={data.base_intracomunitarias || 0} onChange={v => u('base_intracomunitarias', v)} suffix="EUR" />
                    <NumberInput label="Base inversion sujeto pasivo" value={data.base_inversion_sp || 0} onChange={v => u('base_inversion_sp', v)} suffix="EUR" />
                    <NumberInput label="Modificacion cuotas" value={data.mod_cuotas || 0} onChange={v => u('mod_cuotas', v)} suffix="EUR" help="Rectificaciones +/-" />
                </div>
            </details>

            <h3 className="decl-form__section">IVA Deducible (compras)</h3>
            <div className="decl-form__grid">
                <NumberInput label="Cuota bienes/servicios corrientes" value={data.cuota_corrientes_interiores || 0} onChange={v => u('cuota_corrientes_interiores', v)} suffix="EUR" />
                <NumberInput label="Cuota bienes de inversion" value={data.cuota_inversion_interiores || 0} onChange={v => u('cuota_inversion_interiores', v)} suffix="EUR" />
            </div>

            <details className="decl-form__details">
                <summary><ChevronDown size={16} /> Mas deducciones</summary>
                <div className="decl-form__grid">
                    <NumberInput label="Cuota importaciones corrientes" value={data.cuota_importaciones_corrientes || 0} onChange={v => u('cuota_importaciones_corrientes', v)} suffix="EUR" />
                    <NumberInput label="Cuota intracomunitarias" value={data.cuota_intracom_corrientes || 0} onChange={v => u('cuota_intracom_corrientes', v)} suffix="EUR" />
                    <NumberInput label="Rectificacion deducciones" value={data.rectificacion_deducciones || 0} onChange={v => u('rectificacion_deducciones', v)} suffix="EUR" />
                    <NumberInput label="Regularizacion inversion" value={data.regularizacion_inversion || 0} onChange={v => u('regularizacion_inversion', v)} suffix="EUR" />
                </div>
            </details>

            <h3 className="decl-form__section">Ajustes</h3>
            <div className="decl-form__grid">
                <NumberInput label="Cuotas a compensar anteriores" value={data.cuotas_compensar_anteriores || 0} onChange={v => u('cuotas_compensar_anteriores', v)} suffix="EUR" />
                {quarter === 4 && (
                    <NumberInput label="Regularizacion anual" value={data.regularizacion_anual || 0} onChange={v => u('regularizacion_anual', v)} suffix="EUR" />
                )}
                <NumberInput label="% Atribucion Estado" value={data.pct_atribucion_estado ?? 100} onChange={v => u('pct_atribucion_estado', v)} suffix="%" step={1} help="100% salvo operaciones forales" />
            </div>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Modelo 130 Form
// ---------------------------------------------------------------------------

function Form130({ data, onChange, territory }: {
    data: Calculate130Input; onChange: (d: Calculate130Input) => void; territory: string
}) {
    const u = (field: string, val: any) => onChange({ ...data, [field]: val })
    const isComun = territory === 'Comun'
    const isAraba = territory === 'Araba'
    const isNavarra = territory === 'Navarra'
    const isForal = ['Gipuzkoa', 'Bizkaia'].includes(territory)

    return (
        <div className="decl-form">
            {isComun && (
                <>
                    <h3 className="decl-form__section">Seccion I: Estimacion directa (acumulado)</h3>
                    <div className="decl-form__grid">
                        <NumberInput label="Ingresos acumulados" value={data.ingresos_acumulados || 0} onChange={v => u('ingresos_acumulados', v)} suffix="EUR" help="Desde 1 de enero" />
                        <NumberInput label="Gastos acumulados" value={data.gastos_acumulados || 0} onChange={v => u('gastos_acumulados', v)} suffix="EUR" help="Desde 1 de enero" />
                        <NumberInput label="Retenciones acumuladas" value={data.retenciones_acumuladas || 0} onChange={v => u('retenciones_acumuladas', v)} suffix="EUR" />
                        <NumberInput label="Pagos fraccionados anteriores" value={data.pagos_anteriores || 0} onChange={v => u('pagos_anteriores', v)} suffix="EUR" />
                    </div>
                    <h3 className="decl-form__section">Deducciones</h3>
                    <div className="decl-form__grid">
                        <NumberInput label="Rend. neto ano anterior" value={data.rend_neto_anterior || 0} onChange={v => u('rend_neto_anterior', v)} suffix="EUR" help="Para Art. 80 bis" />
                        <CheckboxInput label="Vivienda habitual (hipoteca)" checked={data.tiene_vivienda_habitual || false} onChange={v => u('tiene_vivienda_habitual', v)} />
                        <CheckboxInput label="Residente Ceuta/Melilla" checked={data.ceuta_melilla || false} onChange={v => u('ceuta_melilla', v)} />
                    </div>
                </>
            )}

            {isAraba && (
                <>
                    <h3 className="decl-form__section">Datos del trimestre</h3>
                    <div className="decl-form__grid">
                        <NumberInput label="Ingresos trimestre" value={data.ingresos_trimestre || 0} onChange={v => u('ingresos_trimestre', v)} suffix="EUR" />
                        <NumberInput label="Gastos trimestre" value={data.gastos_trimestre || 0} onChange={v => u('gastos_trimestre', v)} suffix="EUR" />
                        <NumberInput label="Retenciones trimestre" value={data.retenciones_trimestre || 0} onChange={v => u('retenciones_trimestre', v)} suffix="EUR" />
                        <NumberInput label="Pagos anteriores" value={data.pagos_anteriores || 0} onChange={v => u('pagos_anteriores', v)} suffix="EUR" />
                    </div>
                </>
            )}

            {isForal && (
                <>
                    <h3 className="decl-form__section">
                        {territory} - Regimen {data.regimen === 'excepcional' ? 'excepcional' : 'general'}
                    </h3>
                    <div className="decl-form__grid">
                        <div className="decl-field">
                            <label className="decl-field__label">Regimen</label>
                            <select className="decl-field__input" value={data.regimen || 'general'} onChange={e => u('regimen', e.target.value)}>
                                <option value="general">General (5% rend. penultimo)</option>
                                <option value="excepcional">Excepcional (1% volumen)</option>
                            </select>
                        </div>
                        {data.regimen !== 'excepcional' ? (
                            <>
                                <NumberInput label="Rend. neto penultimo ano" value={data.rend_neto_penultimo || 0} onChange={v => u('rend_neto_penultimo', v)} suffix="EUR" />
                                <NumberInput label="Retenciones penultimo ano" value={data.retenciones_penultimo || 0} onChange={v => u('retenciones_penultimo', v)} suffix="EUR" />
                            </>
                        ) : (
                            <>
                                <NumberInput label="Volumen operaciones trimestre" value={data.volumen_operaciones_trimestre || 0} onChange={v => u('volumen_operaciones_trimestre', v)} suffix="EUR" />
                                <NumberInput label="Retenciones trimestre" value={data.retenciones_trimestre_gipuzkoa || 0} onChange={v => u('retenciones_trimestre_gipuzkoa', v)} suffix="EUR" />
                            </>
                        )}
                    </div>
                    {territory === 'Bizkaia' && (
                        <div className="decl-form__grid">
                            <NumberInput label="Años de actividad" value={data.anos_actividad || 3} onChange={v => u('anos_actividad', v)} step={1} help="Primeros 2 años: régimen especial" />
                        </div>
                    )}
                </>
            )}

            {isNavarra && (
                <>
                    <h3 className="decl-form__section">Navarra</h3>
                    <div className="decl-form__grid">
                        <div className="decl-field">
                            <label className="decl-field__label">Modalidad</label>
                            <select className="decl-field__input" value={data.modalidad || 'segunda'} onChange={e => u('modalidad', e.target.value)}>
                                <option value="primera">Primera (rend. penultimo)</option>
                                <option value="segunda">Segunda (acumulado anualizado)</option>
                            </select>
                        </div>
                    </div>
                    {data.modalidad === 'primera' ? (
                        <div className="decl-form__grid">
                            <NumberInput label="Rend. neto penultimo ano" value={data.rend_neto_penultimo || 0} onChange={v => u('rend_neto_penultimo', v)} suffix="EUR" />
                            <NumberInput label="Retenciones penultimo ano" value={data.retenciones_penultimo || 0} onChange={v => u('retenciones_penultimo', v)} suffix="EUR" />
                        </div>
                    ) : (
                        <div className="decl-form__grid">
                            <NumberInput label="Ingresos acumulados" value={data.ingresos_acumulados || 0} onChange={v => u('ingresos_acumulados', v)} suffix="EUR" />
                            <NumberInput label="Gastos acumulados" value={data.gastos_acumulados || 0} onChange={v => u('gastos_acumulados', v)} suffix="EUR" />
                            <NumberInput label="Retenciones acumuladas" value={data.retenciones_acumuladas_navarra || 0} onChange={v => u('retenciones_acumuladas_navarra', v)} suffix="EUR" />
                            <NumberInput label="Pagos anteriores" value={data.pagos_anteriores_navarra || 0} onChange={v => u('pagos_anteriores_navarra', v)} suffix="EUR" />
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

// ---------------------------------------------------------------------------
// IPSI Form (Ceuta/Melilla)
// ---------------------------------------------------------------------------

function FormIpsi({ data, onChange, quarter, territorio }: {
    data: CalculateIpsiInput; onChange: (d: CalculateIpsiInput) => void; quarter: number; territorio: string
}) {
    const u = (field: string, val: number) => onChange({ ...data, [field]: val, quarter, territorio })
    return (
        <div className="decl-form">
            <h3 className="decl-form__section">IPSI Devengado (ventas)</h3>
            <div className="decl-form__grid">
                <NumberInput label="Base tipo general (4%)" value={data.base_4 || 0} onChange={v => u('base_4', v)} suffix="EUR" />
                <NumberInput label="Base tipo bonificado (2%)" value={data.base_2 || 0} onChange={v => u('base_2', v)} suffix="EUR" />
                <NumberInput label="Base tipo incrementado (8%)" value={data.base_8 || 0} onChange={v => u('base_8', v)} suffix="EUR" />
            </div>

            <details className="decl-form__details">
                <summary><ChevronDown size={16} /> Otros tipos</summary>
                <div className="decl-form__grid">
                    <NumberInput label="Base tipo minimo (0.5%)" value={data.base_0_5 || 0} onChange={v => u('base_0_5', v)} suffix="EUR" />
                    <NumberInput label="Base tipo reducido (1%)" value={data.base_1 || 0} onChange={v => u('base_1', v)} suffix="EUR" />
                    <NumberInput label="Base tipo especial (10%)" value={data.base_10 || 0} onChange={v => u('base_10', v)} suffix="EUR" />
                </div>
            </details>

            <details className="decl-form__details">
                <summary><ChevronDown size={16} /> Importaciones e ISP</summary>
                <div className="decl-form__grid">
                    <NumberInput label="Base importaciones" value={data.base_importaciones || 0} onChange={v => u('base_importaciones', v)} suffix="EUR" />
                    <NumberInput label="Base inversion sujeto pasivo" value={data.base_inversion_sp || 0} onChange={v => u('base_inversion_sp', v)} suffix="EUR" />
                    <NumberInput label="Modificacion cuotas" value={data.mod_cuotas || 0} onChange={v => u('mod_cuotas', v)} suffix="EUR" help="Rectificaciones +/-" />
                </div>
            </details>

            <h3 className="decl-form__section">IPSI Deducible (compras)</h3>
            <div className="decl-form__grid">
                <NumberInput label="Cuota bienes/servicios corrientes" value={data.cuota_corrientes_interiores || 0} onChange={v => u('cuota_corrientes_interiores', v)} suffix="EUR" />
                <NumberInput label="Cuota bienes de inversion" value={data.cuota_inversion_interiores || 0} onChange={v => u('cuota_inversion_interiores', v)} suffix="EUR" />
            </div>

            <details className="decl-form__details">
                <summary><ChevronDown size={16} /> Mas deducciones</summary>
                <div className="decl-form__grid">
                    <NumberInput label="Cuota importaciones corrientes" value={data.cuota_importaciones_corrientes || 0} onChange={v => u('cuota_importaciones_corrientes', v)} suffix="EUR" />
                    <NumberInput label="Cuota importaciones inversion" value={data.cuota_importaciones_inversion || 0} onChange={v => u('cuota_importaciones_inversion', v)} suffix="EUR" />
                    <NumberInput label="Rectificacion deducciones" value={data.rectificacion_deducciones || 0} onChange={v => u('rectificacion_deducciones', v)} suffix="EUR" />
                </div>
            </details>

            <h3 className="decl-form__section">Ajustes</h3>
            <div className="decl-form__grid">
                <NumberInput label="Cuotas a compensar anteriores" value={data.cuotas_compensar_anteriores || 0} onChange={v => u('cuotas_compensar_anteriores', v)} suffix="EUR" />
                {quarter === 4 && (
                    <NumberInput label="Regularizacion anual" value={data.regularizacion_anual || 0} onChange={v => u('regularizacion_anual', v)} suffix="EUR" />
                )}
            </div>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Result card
// ---------------------------------------------------------------------------

function ResultCard({ result, modelo }: { result: Record<string, any>; modelo: ModeloType }) {
    if (!result) return null

    const resultado = result.resultado_liquidacion ?? result.resultado ?? 0
    const isNegative = resultado < 0
    const absResult = Math.abs(resultado)

    return (
        <div className={`decl-result ${isNegative ? 'decl-result--negative' : 'decl-result--positive'}`}>
            <div className="decl-result__header">
                <span className="decl-result__icon">
                    {isNegative ? <TrendingDown size={24} /> : <TrendingUp size={24} />}
                </span>
                <div>
                    <span className="decl-result__label">
                        {isNegative ? 'A compensar / devolver' : 'A ingresar'}
                    </span>
                    <span className="decl-result__amount">
                        {isNegative && '-'}
                        <CountUp to={absResult} from={0} duration={0.6} separator="." />
                        <span className="decl-result__currency"> EUR</span>
                    </span>
                </div>
            </div>

            {modelo === '303' && (
                <div className="decl-result__breakdown">
                    <div className="decl-result__row">
                        <span>IVA devengado</span>
                        <span>{(result.total_devengado || 0).toFixed(2)} EUR</span>
                    </div>
                    <div className="decl-result__row">
                        <span>IVA deducible</span>
                        <span>-{(result.total_deducible || 0).toFixed(2)} EUR</span>
                    </div>
                    {result.cuotas_compensar_anteriores > 0 && (
                        <div className="decl-result__row">
                            <span>Compensacion anterior</span>
                            <span>-{result.cuotas_compensar_anteriores.toFixed(2)} EUR</span>
                        </div>
                    )}
                </div>
            )}

            {modelo === '130' && result.casillas && (
                <div className="decl-result__breakdown">
                    <div className="decl-result__row">
                        <span>Rendimiento neto</span>
                        <span>{(result.casillas['03_rendimiento_neto'] || 0).toFixed(2)} EUR</span>
                    </div>
                    <div className="decl-result__row">
                        <span>Tipo aplicado</span>
                        <span>{result.tipo_aplicado || 20}%</span>
                    </div>
                    {result.casillas['13_deduccion_art80bis'] > 0 && (
                        <div className="decl-result__row">
                            <span>Deduccion Art. 80 bis</span>
                            <span>-{result.casillas['13_deduccion_art80bis'].toFixed(2)} EUR</span>
                        </div>
                    )}
                </div>
            )}

            {modelo === '420' && (
                <div className="decl-result__breakdown">
                    <div className="decl-result__row">
                        <span>IGIC devengado</span>
                        <span>{(result.total_devengado || 0).toFixed(2)} EUR</span>
                    </div>
                    <div className="decl-result__row">
                        <span>IGIC deducible</span>
                        <span>-{(result.total_deducible || 0).toFixed(2)} EUR</span>
                    </div>
                </div>
            )}

            {modelo === 'ipsi' && (
                <div className="decl-result__breakdown">
                    <div className="decl-result__row">
                        <span>IPSI devengado</span>
                        <span>{(result.total_devengado || 0).toFixed(2)} EUR</span>
                    </div>
                    <div className="decl-result__row">
                        <span>IPSI deducible</span>
                        <span>-{(result.total_deducible || 0).toFixed(2)} EUR</span>
                    </div>
                    {result.cuotas_compensar_anteriores > 0 && (
                        <div className="decl-result__row">
                            <span>Compensacion anterior</span>
                            <span>-{result.cuotas_compensar_anteriores.toFixed(2)} EUR</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function DeclarationsPage() {
    const { profile } = useFiscalProfile()
    const {
        calcResult, declarations, loading, saving, error,
        calculate, save, loadYear, reset,
    } = useDeclarations()

    const [modelo, setModelo] = useState<ModeloType>('303')
    const [quarter, setQuarter] = useState(1)
    const [year, setYear] = useState(new Date().getFullYear())
    const [territory130, setTerritory130] = useState('Comun')
    const [saved, setSaved] = useState(false)

    // Form state
    const [form303, setForm303] = useState<Calculate303Input>({})
    const [form130, setForm130] = useState<Calculate130Input>({})
    const [form420, setForm420] = useState<Calculate420Input>({})
    const [formIpsi, setFormIpsi] = useState<CalculateIpsiInput>({})

    // Territory detection for conditional tabs and labels
    const userCcaa = profile?.ccaa_residencia || ''
    const isCeutaMelilla = ['Ceuta', 'Melilla'].some(t => userCcaa.includes(t))
    const isCanarias = userCcaa.includes('Canarias')
    const isGipuzkoa = userCcaa.includes('Gipuzkoa') || userCcaa.includes('Guipuzcoa')
    const isNavarra = userCcaa.includes('Navarra')
    const isForal = isGipuzkoa || isNavarra || ['Araba', 'Alava', 'Bizkaia', 'Vizcaya'].some(t => userCcaa.includes(t))
    const ipsiTerritorio = userCcaa.includes('Melilla') ? 'Melilla' : 'Ceuta'

    // IVA model name varies by territory
    const ivaModeloNum = isGipuzkoa ? '300' : isNavarra ? 'F-69' : '303'
    const ivaModeloLabel = isGipuzkoa ? '300 IVA' : isNavarra ? 'F-69 IVA' : '303 IVA'

    // Auto-detect territory from profile
    useEffect(() => {
        if (profile?.ccaa_residencia) {
            const ccaa = profile.ccaa_residencia
            if (['Araba', 'Alava'].some(t => ccaa.includes(t))) setTerritory130('Araba')
            else if (ccaa.includes('Gipuzkoa') || ccaa.includes('Guipuzcoa')) setTerritory130('Gipuzkoa')
            else if (ccaa.includes('Bizkaia') || ccaa.includes('Vizcaya')) setTerritory130('Bizkaia')
            else if (ccaa.includes('Navarra')) setTerritory130('Navarra')
            else setTerritory130('Comun')

            // Default to IPSI for Ceuta/Melilla, IGIC for Canarias
            if (['Ceuta', 'Melilla'].some(t => ccaa.includes(t))) setModelo('ipsi')
            else if (ccaa.includes('Canarias')) setModelo('420')
        }
    }, [profile])

    // Auto-calculate on form change
    useEffect(() => {
        setSaved(false)
        if (modelo === '303') {
            const hasInput = (form303.base_4 || 0) + (form303.base_10 || 0) + (form303.base_21 || 0) +
                (form303.cuota_corrientes_interiores || 0) > 0
            if (hasInput) calculate('303', { ...form303, quarter, year })
        } else if (modelo === '130') {
            const hasInput = (form130.ingresos_acumulados || 0) + (form130.ingresos_trimestre || 0) +
                (form130.rend_neto_penultimo || 0) > 0
            if (hasInput) calculate('130', { ...form130, quarter, territory: territory130 })
        } else if (modelo === '420') {
            const hasInput = (form420.base_7 || 0) + (form420.base_3 || 0) + (form420.base_0 || 0) > 0
            if (hasInput) calculate('420', { ...form420, quarter })
        } else if (modelo === 'ipsi') {
            const hasInput = (formIpsi.base_4 || 0) + (formIpsi.base_2 || 0) + (formIpsi.base_8 || 0) +
                (formIpsi.cuota_corrientes_interiores || 0) > 0
            if (hasInput) calculate('ipsi', { ...formIpsi, quarter, year, territorio: ipsiTerritorio })
        }
    }, [form303, form130, form420, formIpsi, modelo, quarter, year, territory130, ipsiTerritorio, calculate])

    // Load saved declarations
    useEffect(() => {
        loadYear(year)
    }, [year, loadYear])

    const handleSave = async () => {
        if (!calcResult?.success || !calcResult.result) return
        const formData = modelo === '303' ? form303 : modelo === '130' ? form130 : modelo === '420' ? form420 : formIpsi
        const territory = modelo === '130' ? territory130 : modelo === '420' ? 'Canarias' : modelo === 'ipsi' ? ipsiTerritorio : 'comun'
        const result = await save(modelo, territory, year, quarter, formData, calcResult.result)
        if (result?.success) {
            setSaved(true)
            loadYear(year)
        }
    }

    const handleReset = () => {
        if (modelo === '303') setForm303({})
        else if (modelo === '130') setForm130({})
        else if (modelo === '420') setForm420({})
        else setFormIpsi({})
        reset()
        setSaved(false)
    }

    const modeloLabel = useMemo(() => {
        if (modelo === '303') return `Modelo ${ivaModeloNum} - IVA${isForal ? ` (${territory130})` : ''}`
        if (modelo === '130') return `Modelo 130 - Pago Fraccionado IRPF${isForal ? ` (${territory130})` : ''}`
        if (modelo === 'ipsi') return `IPSI - ${ipsiTerritorio}`
        return 'Modelo 420 - IGIC Canarias'
    }, [modelo, ipsiTerritorio, ivaModeloNum, isForal, territory130])

    return (
        <div className="declarations-page">
            <Header />

            <main className="declarations-page__main">
                <div className="declarations-page__header">
                    <FileText size={28} />
                    <div>
                        <h1>Modelos Trimestrales</h1>
                        <p>Calcula y guarda tus declaraciones trimestrales{isCeutaMelilla ? ' de IPSI e IRPF' : isCanarias ? ' de IGIC e IRPF' : ' de IVA e IRPF'}{isForal ? ` — Hacienda Foral de ${territory130}` : ''}</p>
                    </div>
                </div>

                {/* Selector tabs — show relevant models based on user territory */}
                <div className="decl-tabs">
                    {!isCeutaMelilla && !isCanarias && (
                        <button className={`decl-tab ${modelo === '303' ? 'decl-tab--active' : ''}`} onClick={() => { setModelo('303'); reset() }}>
                            <Calculator size={16} /> {ivaModeloLabel}
                        </button>
                    )}
                    <button className={`decl-tab ${modelo === '130' ? 'decl-tab--active' : ''}`} onClick={() => { setModelo('130'); reset() }}>
                        <Calculator size={16} /> 130 IRPF
                    </button>
                    {isCanarias && (
                        <button className={`decl-tab ${modelo === '420' ? 'decl-tab--active' : ''}`} onClick={() => { setModelo('420'); reset() }}>
                            <Calculator size={16} /> 420 IGIC
                        </button>
                    )}
                    {isCeutaMelilla && (
                        <button className={`decl-tab ${modelo === 'ipsi' ? 'decl-tab--active' : ''}`} onClick={() => { setModelo('ipsi'); reset() }}>
                            <Calculator size={16} /> IPSI
                        </button>
                    )}
                </div>

                <div className="declarations-page__content">
                    {/* Left: Form */}
                    <div className="decl-form-panel">
                        <div className="decl-form-panel__header">
                            <h2>{modeloLabel}</h2>
                            <div className="decl-selectors">
                                <select className="decl-select" value={quarter} onChange={e => setQuarter(Number(e.target.value))}>
                                    {QUARTERS.map(q => (
                                        <option key={q.value} value={q.value}>{q.label}</option>
                                    ))}
                                </select>
                                <select className="decl-select" value={year} onChange={e => setYear(Number(e.target.value))}>
                                    {[2024, 2025, 2026].map(y => (
                                        <option key={y} value={y}>{y}</option>
                                    ))}
                                </select>
                                {modelo === '130' && (
                                    <select className="decl-select" value={territory130} onChange={e => setTerritory130(e.target.value)}>
                                        {TERRITORIES_130.map(t => (
                                            <option key={t} value={t}>{t}</option>
                                        ))}
                                    </select>
                                )}
                            </div>
                        </div>

                        {modelo === '303' && <Form303 data={form303} onChange={setForm303} quarter={quarter} />}
                        {modelo === '130' && <Form130 data={form130} onChange={setForm130} territory={territory130} />}
                        {modelo === '420' && (
                            <div className="decl-form">
                                <h3 className="decl-form__section">IGIC Devengado</h3>
                                <div className="decl-form__grid">
                                    <NumberInput label="Base tipo cero (0%)" value={form420.base_0 || 0} onChange={v => setForm420(p => ({ ...p, base_0: v }))} suffix="EUR" />
                                    <NumberInput label="Base reducido (3%)" value={form420.base_3 || 0} onChange={v => setForm420(p => ({ ...p, base_3: v }))} suffix="EUR" />
                                    <NumberInput label="Base general (7%)" value={form420.base_7 || 0} onChange={v => setForm420(p => ({ ...p, base_7: v }))} suffix="EUR" />
                                    <NumberInput label="Base incrementado 1 (9.5%)" value={form420.base_9_5 || 0} onChange={v => setForm420(p => ({ ...p, base_9_5: v }))} suffix="EUR" />
                                    <NumberInput label="Base incrementado 2 (13.5%)" value={form420.base_13_5 || 0} onChange={v => setForm420(p => ({ ...p, base_13_5: v }))} suffix="EUR" />
                                </div>
                                <h3 className="decl-form__section">IGIC Deducible</h3>
                                <div className="decl-form__grid">
                                    <NumberInput label="Cuota corrientes interiores" value={form420.cuota_corrientes_interiores || 0} onChange={v => setForm420(p => ({ ...p, cuota_corrientes_interiores: v }))} suffix="EUR" />
                                    <NumberInput label="Cuota inversion interiores" value={form420.cuota_inversion_interiores || 0} onChange={v => setForm420(p => ({ ...p, cuota_inversion_interiores: v }))} suffix="EUR" />
                                </div>
                                <h3 className="decl-form__section">Ajustes</h3>
                                <div className="decl-form__grid">
                                    <NumberInput label="Cuotas compensar anteriores" value={form420.cuotas_compensar_anteriores || 0} onChange={v => setForm420(p => ({ ...p, cuotas_compensar_anteriores: v }))} suffix="EUR" />
                                </div>
                            </div>
                        )}

                        {modelo === 'ipsi' && (
                            <FormIpsi data={formIpsi} onChange={setFormIpsi} quarter={quarter} territorio={ipsiTerritorio} />
                        )}

                        <div className="decl-form-actions">
                            <button className="decl-btn decl-btn--secondary" onClick={handleReset}>
                                Limpiar
                            </button>
                            <button
                                className="decl-btn decl-btn--primary"
                                onClick={handleSave}
                                disabled={!calcResult?.success || saving}
                            >
                                {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                                {saved ? 'Guardado' : 'Guardar declaración'}
                            </button>
                        </div>

                        {error && <div className="decl-error">{error}</div>}
                    </div>

                    {/* Right: Result + History */}
                    <div className="decl-sidebar">
                        {loading && (
                            <div className="decl-loading">
                                <Loader2 size={24} className="spin" /> Calculando...
                            </div>
                        )}

                        {calcResult?.success && calcResult.result && (
                            <ResultCard result={calcResult.result} modelo={modelo} />
                        )}

                        {/* Saved declarations */}
                        {declarations.length > 0 && (
                            <div className="decl-history">
                                <h3><BarChart3 size={18} /> Declaraciones {year}</h3>
                                <div className="decl-history__list">
                                    {declarations.map(d => (
                                        <div key={d.id} className="decl-history__item">
                                            <div className="decl-history__info">
                                                <span className="decl-history__type">M{d.declaration_type}</span>
                                                <span className="decl-history__quarter">{d.quarter}T</span>
                                                <span className="decl-history__territory">{d.territory}</span>
                                            </div>
                                            <div className="decl-history__amount">
                                                {(d.tax_due || 0).toFixed(2)} EUR
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
