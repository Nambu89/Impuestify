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
    // Creator-specific fields
    plataformas_ingresos: Record<string, number>
    epigrafe_iae: string
    tiene_ingresos_intracomunitarios: boolean
    ingresos_intracomunitarios: number
    withholding_tax_pagado: number
    gastos_equipo: number
    gastos_software: number
    gastos_coworking: number
    gastos_transporte: number
    gastos_formacion: number
    // Step 3: Ahorro e inversiones
    intereses: number
    dividendos: number
    ganancias_fondos: number
    retenciones_ahorro: number
    // Step 4: Inversiones y cripto (NEW)
    tiene_criptomonedas: boolean
    cripto_ganancia_neta: number
    cripto_perdida_neta: number
    tiene_acciones_fondos: boolean
    ganancias_acciones: number
    perdidas_acciones: number
    ganancias_reembolso_fondos: number
    perdidas_reembolso_fondos: number
    tiene_derivados: boolean
    ganancias_derivados: number
    perdidas_derivados: number
    tiene_ganancias_juegos_privados: boolean
    premios_metalico_privados: number
    perdidas_juegos_privados: number
    tiene_premios_loterias: boolean
    premios_metalico_publicos: number
    // Step 5: Inmuebles
    ingresos_alquiler: number
    gastos_alquiler_total: number
    valor_adquisicion_inmueble: number
    retenciones_alquiler: number
    alquiler_habitual_pre2015: boolean
    alquiler_pagado_anual: number
    valor_catastral_segundas_viviendas: number
    valor_catastral_revisado_post1994: boolean
    // Step 6: Familia
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
    // Creator-specific defaults
    plataformas_ingresos: {},
    epigrafe_iae: '',
    tiene_ingresos_intracomunitarios: false,
    ingresos_intracomunitarios: 0,
    withholding_tax_pagado: 0,
    gastos_equipo: 0,
    gastos_software: 0,
    gastos_coworking: 0,
    gastos_transporte: 0,
    gastos_formacion: 0,
    intereses: 0,
    dividendos: 0,
    ganancias_fondos: 0,
    retenciones_ahorro: 0,
    // Inversiones y cripto
    tiene_criptomonedas: false,
    cripto_ganancia_neta: 0,
    cripto_perdida_neta: 0,
    tiene_acciones_fondos: false,
    ganancias_acciones: 0,
    perdidas_acciones: 0,
    ganancias_reembolso_fondos: 0,
    perdidas_reembolso_fondos: 0,
    tiene_derivados: false,
    ganancias_derivados: 0,
    perdidas_derivados: 0,
    tiene_ganancias_juegos_privados: false,
    premios_metalico_privados: 0,
    perdidas_juegos_privados: 0,
    tiene_premios_loterias: false,
    premios_metalico_publicos: 0,
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
    'Inversiones y cripto',
    'Familia',
    'Deducciones',
    'Resultado',
]

export const STEP_LABELS_PARTICULAR = [
    'Datos personales',
    'Trabajo',
    'Ahorro e inversiones',
    'Inmuebles',
    'Familia',
    'Deducciones',
    'Resultado',
]

export const STEP_LABELS_CREATOR = [
    'Datos personales',
    'Trabajo',
    'Actividad como creador',
    'Ahorro e inversiones',
    'Inmuebles',
    'Familia',
    'Deducciones',
    'Resultado',
]

export const STEP_LABELS_AUTONOMO = [
    'Datos personales',
    'Trabajo',
    'Actividad económica',
    'Ahorro e inversiones',
    'Inmuebles',
    'Familia',
    'Deducciones',
    'Resultado',
]

export const QUICK_STEP_LABELS = [
    'Datos básicos',
    'Resultado',
]

function getStepLabelsByPlan(userPlan?: string): string[] {
    if (userPlan === 'particular') return STEP_LABELS_PARTICULAR
    if (userPlan === 'creator') return STEP_LABELS_CREATOR
    // autonomo or default
    return STEP_LABELS_AUTONOMO
}

export function useTaxGuideProgress(userPlan?: string) {
    const [step, setStep] = useState(0)
    const [data, setData] = useState<TaxGuideData>(EMPTY_TAX_DATA)

    const fullStepLabels = getStepLabelsByPlan(userPlan)
    const stepLabels = data.wizard_mode === 'quick' ? QUICK_STEP_LABELS : fullStepLabels

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
