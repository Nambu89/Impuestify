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
    // Phase 3: Payslip fields
    num_pagas_anuales?: number
    salario_base_mensual?: number
    complementos_salariales?: number
    irpf_retenido_porcentaje?: number
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
    trabajo?: {
        ingresos_brutos: number
        gastos_deducibles: number
        reduccion_trabajo: number
        rendimiento_neto: number
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

        // Must have some income to calculate
        const hasIncome = (input.ingresos_trabajo || 0) > 0 ||
            (input.intereses || 0) > 0 ||
            (input.dividendos || 0) > 0 ||
            (input.ganancias_fondos || 0) > 0 ||
            (input.ingresos_alquiler || 0) > 0
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
                    if (!data.success) setError(data.error || 'Error en la estimacion')
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
