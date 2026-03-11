import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ModeloType = '303' | '130' | '420' | 'ipsi'

export interface Calculate303Input {
    base_4?: number
    base_10?: number
    base_21?: number
    base_intracomunitarias?: number
    tipo_intracomunitarias?: number
    base_inversion_sp?: number
    mod_bases?: number
    mod_cuotas?: number
    cuota_corrientes_interiores?: number
    cuota_inversion_interiores?: number
    cuota_importaciones_corrientes?: number
    cuota_importaciones_inversion?: number
    cuota_intracom_corrientes?: number
    cuota_intracom_inversion?: number
    rectificacion_deducciones?: number
    compensacion_agricultura?: number
    regularizacion_inversion?: number
    regularizacion_prorrata?: number
    pct_atribucion_estado?: number
    cuotas_compensar_anteriores?: number
    regularizacion_anual?: number
    resultado_anterior_complementaria?: number
    quarter?: number
    year?: number
    territory?: string
}

export interface Calculate130Input {
    territory?: string
    quarter?: number
    ceuta_melilla?: boolean
    ingresos_acumulados?: number
    gastos_acumulados?: number
    retenciones_acumuladas?: number
    pagos_anteriores?: number
    rend_neto_anterior?: number
    tiene_vivienda_habitual?: boolean
    resultado_anterior_complementaria?: number
    ingresos_trimestre?: number
    gastos_trimestre?: number
    retenciones_trimestre?: number
    regimen?: string
    rend_neto_penultimo?: number
    retenciones_penultimo?: number
    volumen_operaciones_trimestre?: number
    retenciones_trimestre_gipuzkoa?: number
    anos_actividad?: number
    volumen_ventas_penultimo?: number
    modalidad?: string
    retenciones_acumuladas_navarra?: number
    pagos_anteriores_navarra?: number
}

export interface Calculate420Input {
    base_0?: number
    base_3?: number
    base_7?: number
    base_9_5?: number
    base_13_5?: number
    base_20?: number
    base_35?: number
    base_extracanarias?: number
    tipo_extracanarias?: number
    base_inversion_sp?: number
    cuota_corrientes_interiores?: number
    cuota_inversion_interiores?: number
    cuota_importaciones_corrientes?: number
    cuota_importaciones_inversion?: number
    cuota_extracanarias_corrientes?: number
    cuota_extracanarias_inversion?: number
    rectificacion_deducciones?: number
    compensacion_agricultura?: number
    regularizacion_inversion?: number
    regularizacion_prorrata?: number
    cuotas_compensar_anteriores?: number
    regularizacion_anual?: number
    resultado_anterior_complementaria?: number
    quarter?: number
}

export interface CalculateIpsiInput {
    territorio?: string
    base_0_5?: number
    base_1?: number
    base_2?: number
    base_4?: number
    base_8?: number
    base_10?: number
    base_importaciones?: number
    tipo_importaciones?: number
    base_inversion_sp?: number
    tipo_inversion_sp?: number
    mod_bases?: number
    mod_cuotas?: number
    cuota_corrientes_interiores?: number
    cuota_inversion_interiores?: number
    cuota_importaciones_corrientes?: number
    cuota_importaciones_inversion?: number
    rectificacion_deducciones?: number
    regularizacion_inversion?: number
    regularizacion_prorrata?: number
    cuotas_compensar_anteriores?: number
    regularizacion_anual?: number
    resultado_anterior_complementaria?: number
    quarter?: number
    year?: number
}

export interface CalculationResult {
    success: boolean
    result: Record<string, any>
    error?: string
}

export interface DeclarationSummary {
    id: string
    declaration_type: string
    territory: string
    year: number
    quarter: number
    tax_due: number
    status: string
    created_at: string
}

export interface ProjectionResult {
    quarterly_data: {
        quarters_130: number[]
        quarters_303: number[]
        quarters_420: number[]
        num_quarters_activity: number
        total_pagos_130: number
    }
    annualized: {
        ingresos: number
        gastos: number
        rendimiento_neto: number
        factor: number
        nota: string
    }
    iva_summary: {
        total_iva_devengado: number
        total_iva_deducible: number
        saldo_iva: number
    }
    projection: Record<string, any>
    confidence: string
    year: number
    jurisdiction: string
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const DEBOUNCE_MS = 400

export function useDeclarations() {
    const { apiRequest } = useApi()
    const [calcResult, setCalcResult] = useState<CalculationResult | null>(null)
    const [declarations, setDeclarations] = useState<DeclarationSummary[]>([])
    const [projection, setProjection] = useState<ProjectionResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const calculate = useCallback((
        modelo: ModeloType,
        input: Calculate303Input | Calculate130Input | Calculate420Input | CalculateIpsiInput,
    ) => {
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()

        timerRef.current = setTimeout(async () => {
            setLoading(true)
            setError(null)

            const controller = new AbortController()
            abortRef.current = controller

            try {
                const data = await apiRequest<CalculationResult>(
                    `/api/declarations/${modelo}/calculate`,
                    {
                        method: 'POST',
                        body: JSON.stringify(input),
                        signal: controller.signal,
                    }
                )
                if (!controller.signal.aborted) {
                    setCalcResult(data)
                    if (!data.success) setError(data.error || 'Error en el cálculo')
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

    const save = useCallback(async (
        declarationType: ModeloType,
        territory: string,
        year: number,
        quarter: number,
        formData: Record<string, any>,
        calculatedResult: Record<string, any>,
    ) => {
        setSaving(true)
        setError(null)
        try {
            const data = await apiRequest<CalculationResult>(
                '/api/declarations/save',
                {
                    method: 'POST',
                    body: JSON.stringify({
                        declaration_type: declarationType,
                        territory,
                        year,
                        quarter,
                        form_data: formData,
                        calculated_result: calculatedResult,
                    }),
                }
            )
            if (!data.success) setError(data.error || 'Error al guardar')
            return data
        } catch (err: any) {
            setError(err.message)
            return null
        } finally {
            setSaving(false)
        }
    }, [apiRequest])

    const loadYear = useCallback(async (year: number) => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<{ declarations: DeclarationSummary[] }>(
                `/api/declarations/${year}`
            )
            setDeclarations(data.declarations || [])
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const projectIrpf = useCallback(async (input: Record<string, any>) => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<CalculationResult>(
                '/api/declarations/projection',
                {
                    method: 'POST',
                    body: JSON.stringify(input),
                }
            )
            if (data.success) {
                setProjection(data.result as unknown as ProjectionResult)
            } else {
                setError(data.error || 'Error en la proyeccion')
            }
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const deleteDeclaration = useCallback(async (declarationId: string) => {
        try {
            await apiRequest(`/api/declarations/${declarationId}`, { method: 'DELETE' })
            setDeclarations(prev => prev.filter(d => d.id !== declarationId))
            return true
        } catch (err: any) {
            setError(err.message)
            return false
        }
    }, [apiRequest])

    const reset = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()
        setCalcResult(null)
        setError(null)
        setLoading(false)
    }, [])

    return {
        calcResult, declarations, projection,
        loading, saving, error,
        calculate, save, loadYear, projectIrpf, deleteDeclaration, reset,
    }
}
