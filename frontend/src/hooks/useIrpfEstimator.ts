import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'

export interface IrpfEstimateInput {
    comunidad_autonoma: string
    year?: number
    ingresos_trabajo?: number
    ss_empleado?: number
    retenciones_trabajo?: number
    intereses?: number
    dividendos?: number
    ganancias_fondos?: number
    ingresos_alquiler?: number
    gastos_alquiler_total?: number
    valor_adquisicion_inmueble?: number
    edad_contribuyente?: number
    num_descendientes?: number
    anios_nacimiento_desc?: number[]
    custodia_compartida?: boolean
    num_ascendientes_65?: number
    num_ascendientes_75?: number
    discapacidad_contribuyente?: number
    ceuta_melilla?: boolean
    // Phase 1 fields
    aportaciones_plan_pensiones?: number
    aportaciones_plan_pensiones_empresa?: number
    hipoteca_pre2013?: boolean
    capital_amortizado_hipoteca?: number
    intereses_hipoteca?: number
    madre_trabajadora_ss?: boolean
    gastos_guarderia_anual?: number
    familia_numerosa?: boolean
    tipo_familia_numerosa?: string
    donativos_ley_49_2002?: number
    donativo_recurrente?: boolean
    retenciones_alquiler?: number
    retenciones_ahorro?: number
    // Activity income (autonomos)
    ingresos_actividad?: number
    gastos_actividad?: number
    cuota_autonomo_anual?: number
    amortizaciones_actividad?: number
    provisiones_actividad?: number
    otros_gastos_actividad?: number
    estimacion_actividad?: string
    inicio_actividad?: boolean
    un_solo_cliente?: boolean
    retenciones_actividad?: number
    pagos_fraccionados_130?: number
    // Phase 3: Payslip fields
    num_pagas_anuales?: number
    salario_base_mensual?: number
    complementos_salariales?: number
    irpf_retenido_porcentaje?: number
    // Inversiones, cripto y apuestas
    cripto_ganancia_neta?: number
    cripto_perdida_neta?: number
    ganancias_acciones?: number
    perdidas_acciones?: number
    ganancias_reembolso_fondos?: number
    perdidas_reembolso_fondos?: number
    ganancias_derivados?: number
    perdidas_derivados?: number
    premios_metalico_privados?: number
    perdidas_juegos_privados?: number
    premios_metalico_publicos?: number
    // Creator-specific (mapean a campos existentes del backend)
    plataformas_ingresos?: Record<string, number>
    epigrafe_iae?: string
    tiene_ingresos_intracomunitarios?: boolean
    ingresos_intracomunitarios?: number
    withholding_tax_pagado?: number
    gastos_equipo?: number
    gastos_software?: number
    gastos_coworking?: number
    gastos_transporte?: number
    gastos_formacion?: number
    // CCAA deductions
    deducciones_answers?: Record<string, any>
    donativos_autonomicos?: number
    gastos_educativos?: number
    inversion_vivienda?: number
    instalacion_renovable_importe?: number
    vehiculo_electrico_importe?: number
    obras_mejora_importe?: number
    cotizaciones_empleada_hogar?: number
    // Phase 2 fields
    tributacion_conjunta?: boolean
    tipo_unidad_familiar?: string
    alquiler_habitual_pre2015?: boolean
    alquiler_pagado_anual?: number
    valor_catastral_segundas_viviendas?: number
    valor_catastral_revisado_post1994?: boolean
}

export interface IrpfEstimateResult {
    success: boolean
    resultado_estimado: number
    cuota_liquida_total: number
    retenciones_pagadas: number
    base_imponible_general: number
    base_imponible_ahorro: number
    cuota_integra_general: number
    cuota_integra_ahorro: number
    tipo_medio_efectivo: number
    mpyf_estatal: number
    mpyf_autonomico: number
    deduccion_ceuta_melilla: number
    reduccion_planes_pensiones: number
    deduccion_vivienda_pre2013: number
    deduccion_maternidad: number
    deduccion_familia_numerosa: number
    deduccion_donativos: number
    total_deducciones_cuota: number
    // Phase 2 result fields
    reduccion_tributacion_conjunta: number
    deduccion_alquiler_pre2015: number
    renta_imputada_inmuebles: number
    // Fase 5: CCAA deductions
    deducciones_autonomicas?: Array<{ code: string; name: string; amount: number; percentage?: number; max_amount?: number; fixed_amount?: number }>
    total_deducciones_autonomicas?: number
    trabajo?: {
        ingresos_brutos: number
        gastos_deducibles: number
        reduccion_trabajo: number
        rendimiento_neto: number
    }
    actividad?: {
        ingresos_actividad: number
        total_gastos_deducibles: number
        gastos_dificil_justificacion: number
        rendimiento_neto: number
        reduccion_aplicada: number
        tipo_reduccion: string
        rendimiento_neto_reducido: number
        estimacion: string
    }
    error?: string
}

const DEBOUNCE_MS = 600

export function useIrpfEstimator() {
    const { apiRequest } = useApi()
    const [result, setResult] = useState<IrpfEstimateResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const estimate = useCallback((input: IrpfEstimateInput) => {
        // Must have at least CCAA to estimate
        if (!input.comunidad_autonoma) {
            setResult(null)
            return
        }

        // Must have some income to calculate (check both annual and monthly salary)
        const platformTotal = Object.values(input.plataformas_ingresos || {}).reduce((a, b) => a + b, 0)
        const hasIncome = (input.ingresos_trabajo || 0) > 0 ||
            (input.salario_base_mensual || 0) > 0 ||
            (input.ingresos_actividad || 0) > 0 ||
            platformTotal > 0 ||
            (input.intereses || 0) > 0 ||
            (input.dividendos || 0) > 0 ||
            (input.ganancias_fondos || 0) > 0 ||
            (input.ingresos_alquiler || 0) > 0 ||
            (input.cripto_ganancia_neta || 0) > 0 ||
            (input.ganancias_acciones || 0) > 0 ||
            (input.ganancias_reembolso_fondos || 0) > 0 ||
            (input.ganancias_derivados || 0) > 0 ||
            (input.premios_metalico_privados || 0) > 0 ||
            (input.premios_metalico_publicos || 0) > 0
        if (!hasIncome) {
            setResult(null)
            return
        }

        // Debounce
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()

        timerRef.current = setTimeout(async () => {
            setLoading(true)
            setError(null)

            const controller = new AbortController()
            abortRef.current = controller

            try {
                const data = await apiRequest<IrpfEstimateResult>(
                    '/api/irpf/estimate',
                    {
                        method: 'POST',
                        body: JSON.stringify(input),
                        signal: controller.signal,
                    }
                )
                if (!controller.signal.aborted) {
                    setResult(data)
                    if (!data.success) setError(data.error || 'Error en la estimación')
                }
            } catch (err: any) {
                if (err.name !== 'AbortError' && !controller.signal.aborted) {
                    setError(err.message)
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false)
            }
        }, DEBOUNCE_MS)
    }, [apiRequest])

    const reset = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()
        setResult(null)
        setError(null)
        setLoading(false)
    }, [])

    return { result, loading, error, estimate, reset }
}
