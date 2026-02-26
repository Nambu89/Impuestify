import { useState, useCallback, useEffect } from 'react'
import { useApi } from './useApi'

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
}

export function useFiscalProfile() {
    const { apiRequest } = useApi()
    const [profile, setProfile] = useState<FiscalProfile>(EMPTY_PROFILE)
    const [fieldMeta, setFieldMeta] = useState<Record<string, FieldMeta>>({})
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const refresh = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<FiscalProfileResponse>(
                '/api/users/me/fiscal-profile'
            )

            const merged: FiscalProfile = {
                ...EMPTY_PROFILE,
                ccaa_residencia: data.ccaa_residencia,
                situacion_laboral: data.situacion_laboral,
                fecha_nacimiento: data.fecha_nacimiento,
                ...data.fields,
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
        try {
            await apiRequest('/api/users/me/fiscal-profile', {
                method: 'PUT',
                body: JSON.stringify(data),
            })
            // Refresh to get updated field_meta
            await refresh()
            return true
        } catch (err: any) {
            setError(err.message)
            return false
        } finally {
            setSaving(false)
        }
    }, [apiRequest, refresh])

    // Load on mount
    useEffect(() => {
        refresh()
    }, [refresh])

    return { profile, fieldMeta, loading, saving, error, save, refresh }
}
