import { useState, useCallback, useEffect } from 'react'
import { useApi } from './useApi'

const TOKEN_KEY = 'access_token'
const API_URL = import.meta.env.VITE_API_URL || '/api'

export interface PlanUpgradeNeeded {
    required_plan: string
    current_plan: string
    message: string
}

export interface Pagador {
    nombre: string
    nif?: string
    clave: 'empleado' | 'pensionista' | 'desempleo' | 'otro'
    retribuciones_dinerarias: number
    retenciones: number
    gastos_deducibles: number
    retribuciones_especie: number
    ingresos_cuenta: number
}

export interface FiscalProfile {
    ccaa_residencia: string | null
    situacion_laboral: string | null
    fecha_nacimiento: string | null
    ingresos_trabajo: number | null
    ss_empleado: number | null
    num_descendientes: number | null
    anios_nacimiento_desc: number[] | null
    custodia_compartida: boolean
    num_ascendientes_65: number | null
    num_ascendientes_75: number | null
    discapacidad_contribuyente: number | null
    intereses: number | null
    dividendos: number | null
    ganancias_fondos: number | null
    ingresos_alquiler: number | null
    valor_adquisicion_inmueble: number | null
    // Phase 1: Reducciones y Deducciones
    aportaciones_plan_pensiones: number | null
    aportaciones_plan_pensiones_empresa: number | null
    hipoteca_pre2013: boolean
    capital_amortizado_hipoteca: number | null
    intereses_hipoteca: number | null
    madre_trabajadora_ss: boolean
    gastos_guarderia_anual: number | null
    familia_numerosa: boolean
    tipo_familia_numerosa: string | null
    donativos_ley_49_2002: number | null
    donativo_recurrente: boolean
    retenciones_trabajo: number | null
    retenciones_alquiler: number | null
    retenciones_ahorro: number | null
    // Phase 2 fields
    tributacion_conjunta: boolean
    tipo_unidad_familiar: string | null
    alquiler_habitual_pre2015: boolean
    alquiler_pagado_anual: number | null
    valor_catastral_segundas_viviendas: number | null
    valor_catastral_revisado_post1994: boolean
    // Autonomo calculation fields
    ingresos_actividad: number | null
    gastos_actividad: number | null
    cuota_autonomo_anual: number | null
    amortizaciones_actividad: number | null
    provisiones_actividad: number | null
    otros_gastos_actividad: number | null
    estimacion_actividad: string | null
    inicio_actividad: boolean
    un_solo_cliente: boolean
    retenciones_actividad: number | null
    pagos_fraccionados_130: number | null
    // Autonomo-specific fields
    epigrafe_iae: string | null
    tipo_actividad: string | null
    fecha_alta_autonomo: string | null
    metodo_estimacion_irpf: string | null
    regimen_iva: string | null
    rendimientos_netos_mensuales: number | null
    base_cotizacion_reta: number | null
    territorio_foral: boolean
    territorio_historico: string | null
    tipo_retencion_facturas: number | null
    tarifa_plana: boolean
    pluriactividad: boolean
    ceuta_melilla: boolean
    // Phase 3: Payslip/salary
    num_pagas_anuales: number | null
    salario_base_mensual: number | null
    complementos_salariales: number | null
    irpf_retenido_porcentaje: number | null
    // Roles adicionales
    roles_adicionales: string[] | null
    // Multi-pagador
    pagadores: Pagador[] | null
    num_pagadores: number | null
}

export interface FieldMeta {
    source: 'manual' | 'conversation' | 'unknown'
    updated: string
}

interface FiscalProfileResponse {
    ccaa_residencia: string | null
    situacion_laboral: string | null
    fecha_nacimiento: string | null
    fields: Record<string, any>
    field_meta: Record<string, FieldMeta>
}

const EMPTY_PROFILE: FiscalProfile = {
    ccaa_residencia: null,
    situacion_laboral: null,
    fecha_nacimiento: null,
    ingresos_trabajo: null,
    ss_empleado: null,
    num_descendientes: null,
    anios_nacimiento_desc: null,
    custodia_compartida: false,
    num_ascendientes_65: null,
    num_ascendientes_75: null,
    discapacidad_contribuyente: null,
    intereses: null,
    dividendos: null,
    ganancias_fondos: null,
    ingresos_alquiler: null,
    valor_adquisicion_inmueble: null,
    // Phase 1: Reducciones y Deducciones
    aportaciones_plan_pensiones: null,
    aportaciones_plan_pensiones_empresa: null,
    hipoteca_pre2013: false,
    capital_amortizado_hipoteca: null,
    intereses_hipoteca: null,
    madre_trabajadora_ss: false,
    gastos_guarderia_anual: null,
    familia_numerosa: false,
    tipo_familia_numerosa: null,
    donativos_ley_49_2002: null,
    donativo_recurrente: false,
    retenciones_trabajo: null,
    retenciones_alquiler: null,
    retenciones_ahorro: null,
    // Phase 2 fields
    tributacion_conjunta: false,
    tipo_unidad_familiar: null,
    alquiler_habitual_pre2015: false,
    alquiler_pagado_anual: null,
    valor_catastral_segundas_viviendas: null,
    valor_catastral_revisado_post1994: true,
    // Autonomo calculation
    ingresos_actividad: null,
    gastos_actividad: null,
    cuota_autonomo_anual: null,
    amortizaciones_actividad: null,
    provisiones_actividad: null,
    otros_gastos_actividad: null,
    estimacion_actividad: null,
    inicio_actividad: false,
    un_solo_cliente: false,
    retenciones_actividad: null,
    pagos_fraccionados_130: null,
    // Autonomo-specific
    epigrafe_iae: null,
    tipo_actividad: null,
    fecha_alta_autonomo: null,
    metodo_estimacion_irpf: null,
    regimen_iva: null,
    rendimientos_netos_mensuales: null,
    base_cotizacion_reta: null,
    territorio_foral: false,
    territorio_historico: null,
    tipo_retencion_facturas: null,
    tarifa_plana: false,
    pluriactividad: false,
    ceuta_melilla: false,
    // Phase 3: Payslip/salary
    num_pagas_anuales: null,
    salario_base_mensual: null,
    complementos_salariales: null,
    irpf_retenido_porcentaje: null,
    // Roles adicionales
    roles_adicionales: null,
    // Multi-pagador
    pagadores: null,
    num_pagadores: null,
}

export function useFiscalProfile() {
    const { apiRequest } = useApi()
    const [profile, setProfile] = useState<FiscalProfile>(EMPTY_PROFILE)
    const [fieldMeta, setFieldMeta] = useState<Record<string, FieldMeta>>({})
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [planUpgradeNeeded, setPlanUpgradeNeeded] = useState<PlanUpgradeNeeded | null>(null)

    const clearPlanUpgrade = useCallback(() => {
        setPlanUpgradeNeeded(null)
    }, [])

    const refresh = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<FiscalProfileResponse>(
                '/api/users/me/fiscal-profile'
            )

            const merged: FiscalProfile = {
                ...EMPTY_PROFILE,
                ...data.fields,
                // Top-level DB columns ALWAYS override datos_fiscales duplicates
                ccaa_residencia: data.ccaa_residencia,
                situacion_laboral: data.situacion_laboral,
                fecha_nacimiento: data.fecha_nacimiento,
            }

            setProfile(merged)
            setFieldMeta(data.field_meta || {})
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const save = useCallback(async (data: Partial<FiscalProfile>) => {
        setSaving(true)
        setError(null)
        setPlanUpgradeNeeded(null)
        try {
            const token = localStorage.getItem(TOKEN_KEY)
            const response = await fetch(`${API_URL}/api/users/me/fiscal-profile`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token && { Authorization: `Bearer ${token}` }),
                },
                body: JSON.stringify(data),
            })

            if (response.status === 403) {
                const body = await response.json().catch(() => null)
                if (body?.detail === 'plan_incompatible') {
                    setPlanUpgradeNeeded({
                        required_plan: body.required_plan,
                        current_plan: body.current_plan,
                        message: body.message,
                    })
                    return false
                }
                setError('No tienes permiso para realizar esta acción')
                return false
            }

            if (response.status === 401) {
                localStorage.removeItem(TOKEN_KEY)
                window.location.href = '/login?expired=true'
                return false
            }

            if (!response.ok) {
                const body = await response.json().catch(() => null)
                setError(body?.detail || `Error ${response.status}`)
                return false
            }

            // Refresh to get updated field_meta
            await refresh()
            return true
        } catch (err: any) {
            setError(err.message || 'Error de conexión')
            return false
        } finally {
            setSaving(false)
        }
    }, [refresh])

    // Load on mount
    useEffect(() => {
        refresh()
    }, [refresh])

    return { profile, fieldMeta, loading, saving, error, save, refresh, planUpgradeNeeded, clearPlanUpgrade }
}
