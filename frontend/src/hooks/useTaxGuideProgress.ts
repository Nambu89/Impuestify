import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'tax_guide_progress'

export interface TaxGuideData {
    // Step 1: Datos personales
    comunidad_autonoma: string
    edad_contribuyente: number
    ceuta_melilla: boolean
    tributacion_conjunta: boolean
    tipo_unidad_familiar: string  // "matrimonio" | "monoparental"
    // Step 2: Trabajo
    salary_input_mode: 'annual' | 'monthly'  // UI-only
    ingresos_trabajo: number
    ss_empleado: number
    retenciones_trabajo: number
    num_pagas_anuales: 12 | 14
    salario_base_mensual: number
    complementos_salariales: number
    irpf_retenido_porcentaje: number
    // Step 2b: Actividad economica (autonomos)
    ingresos_actividad: number
    gastos_actividad: number
    cuota_autonomo_anual: number
    amortizaciones_actividad: number
    provisiones_actividad: number
    otros_gastos_actividad: number
    estimacion_actividad: string  // "directa_simplificada" | "directa_normal" | "objetiva"
    inicio_actividad: boolean
    un_solo_cliente: boolean
    retenciones_actividad: number
    pagos_fraccionados_130: number
    // Step 3: Ahorro e inversiones
    intereses: number
    dividendos: number
    ganancias_fondos: number
    retenciones_ahorro: number
    // Step 4: Inmuebles
    ingresos_alquiler: number
    gastos_alquiler_total: number
    valor_adquisicion_inmueble: number
    retenciones_alquiler: number
    alquiler_habitual_pre2015: boolean
    alquiler_pagado_anual: number
    valor_catastral_segundas_viviendas: number
    valor_catastral_revisado_post1994: boolean
    // Step 5: Familia
    num_descendientes: number
    anios_nacimiento_desc: number[]
    custodia_compartida: boolean
    num_ascendientes_65: number
    num_ascendientes_75: number
    discapacidad_contribuyente: number
    madre_trabajadora_ss: boolean
    gastos_guarderia_anual: number
    familia_numerosa: boolean
    tipo_familia_numerosa: string
    // Step 6: Deducciones y reducciones
    aportaciones_plan_pensiones: number
    aportaciones_plan_pensiones_empresa: number
    hipoteca_pre2013: boolean
    capital_amortizado_hipoteca: number
    intereses_hipoteca: number
    donativos_ley_49_2002: number
    donativo_recurrente: boolean
    // Wizard mode
    wizard_mode: 'quick' | 'full'
}

export const EMPTY_TAX_DATA: TaxGuideData = {
    comunidad_autonoma: '',
    edad_contribuyente: 35,
    ceuta_melilla: false,
    tributacion_conjunta: false,
    tipo_unidad_familiar: 'matrimonio',
    salary_input_mode: 'annual',
    ingresos_trabajo: 0,
    ss_empleado: 0,
    retenciones_trabajo: 0,
    num_pagas_anuales: 14,
    salario_base_mensual: 0,
    complementos_salariales: 0,
    irpf_retenido_porcentaje: 0,
    // Activity income
    ingresos_actividad: 0,
    gastos_actividad: 0,
    cuota_autonomo_anual: 0,
    amortizaciones_actividad: 0,
    provisiones_actividad: 0,
    otros_gastos_actividad: 0,
    estimacion_actividad: 'directa_simplificada',
    inicio_actividad: false,
    un_solo_cliente: false,
    retenciones_actividad: 0,
    pagos_fraccionados_130: 0,
    intereses: 0,
    dividendos: 0,
    ganancias_fondos: 0,
    retenciones_ahorro: 0,
    ingresos_alquiler: 0,
    gastos_alquiler_total: 0,
    valor_adquisicion_inmueble: 0,
    retenciones_alquiler: 0,
    alquiler_habitual_pre2015: false,
    alquiler_pagado_anual: 0,
    valor_catastral_segundas_viviendas: 0,
    valor_catastral_revisado_post1994: true,
    num_descendientes: 0,
    anios_nacimiento_desc: [],
    custodia_compartida: false,
    num_ascendientes_65: 0,
    num_ascendientes_75: 0,
    discapacidad_contribuyente: 0,
    madre_trabajadora_ss: false,
    gastos_guarderia_anual: 0,
    familia_numerosa: false,
    tipo_familia_numerosa: 'general',
    aportaciones_plan_pensiones: 0,
    aportaciones_plan_pensiones_empresa: 0,
    hipoteca_pre2013: false,
    capital_amortizado_hipoteca: 0,
    intereses_hipoteca: 0,
    donativos_ley_49_2002: 0,
    donativo_recurrente: false,
    wizard_mode: 'full',
}

export const STEP_LABELS = [
    'Datos personales',
    'Trabajo',
    'Ahorro e inversiones',
    'Inmuebles',
    'Familia',
    'Deducciones',
    'Resultado',
]

export const QUICK_STEP_LABELS = [
    'Datos basicos',
    'Resultado',
]

export function useTaxGuideProgress() {
    const [step, setStep] = useState(0)
    const [data, setData] = useState<TaxGuideData>(EMPTY_TAX_DATA)

    const stepLabels = data.wizard_mode === 'quick' ? QUICK_STEP_LABELS : STEP_LABELS

    // Load saved progress on mount
    useEffect(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY)
            if (saved) {
                const parsed = JSON.parse(saved)
                if (parsed.data) setData({ ...EMPTY_TAX_DATA, ...parsed.data })
                if (typeof parsed.step === 'number') setStep(parsed.step)
            }
        } catch {
            // ignore corrupt data
        }
    }, [])

    // Persist on change
    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }))
    }, [step, data])

    const updateData = useCallback((partial: Partial<TaxGuideData>) => {
        setData(prev => ({ ...prev, ...partial }))
    }, [])

    const nextStep = useCallback(() => {
        setStep(prev => Math.min(prev + 1, stepLabels.length - 1))
    }, [stepLabels.length])

    const prevStep = useCallback(() => {
        setStep(prev => Math.max(prev - 1, 0))
    }, [])

    const goToStep = useCallback((s: number) => {
        setStep(Math.max(0, Math.min(s, stepLabels.length - 1)))
    }, [stepLabels.length])

    const resetAll = useCallback(() => {
        setStep(0)
        setData(EMPTY_TAX_DATA)
        localStorage.removeItem(STORAGE_KEY)
    }, [])

    return { step, data, updateData, nextStep, prevStep, goToStep, resetAll, stepLabels }
}
