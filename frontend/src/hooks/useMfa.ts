import { useState, useCallback } from 'react'
import { useApi } from './useApi'

export interface MfaSetupData {
    qr_code_base64: string
    secret: string
    backup_codes: string[]
    uri: string
}

export interface MfaVerifyResult {
    success: boolean
    backup_codes?: string[]
}

export interface MfaLoginResult {
    access_token: string
    refresh_token: string
}

export function useMfa() {
    const { apiRequest } = useApi()
    const [mfaEnabled, setMfaEnabled] = useState(false)
    const [loading, setLoading] = useState(false)
    const [statusLoaded, setStatusLoaded] = useState(false)

    const checkStatus = useCallback(async () => {
        setLoading(true)
        try {
            const data = await apiRequest<{ enabled: boolean }>('/auth/mfa/status')
            setMfaEnabled(data.enabled)
            setStatusLoaded(true)
        } catch {
            // Si el endpoint no existe aún, asumir desactivado
            setMfaEnabled(false)
            setStatusLoaded(true)
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const setup = useCallback(async (): Promise<MfaSetupData | null> => {
        setLoading(true)
        try {
            const data = await apiRequest<MfaSetupData>('/auth/mfa/setup', { method: 'POST' })
            return data
        } catch (error: any) {
            throw new Error(error.message || 'Error al iniciar la configuración de 2FA')
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const verify = useCallback(async (code: string): Promise<MfaVerifyResult> => {
        setLoading(true)
        try {
            const data = await apiRequest<MfaVerifyResult>('/auth/mfa/verify', {
                method: 'POST',
                body: JSON.stringify({ code }),
            })
            if (data.success) {
                setMfaEnabled(true)
            }
            return data
        } catch (error: any) {
            throw new Error(error.message || 'Código incorrecto. Inténtalo de nuevo.')
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const disable = useCallback(async (code: string): Promise<boolean> => {
        setLoading(true)
        try {
            const data = await apiRequest<{ success: boolean }>('/auth/mfa/disable', {
                method: 'POST',
                body: JSON.stringify({ code }),
            })
            if (data.success) {
                setMfaEnabled(false)
            }
            return data.success
        } catch (error: any) {
            throw new Error(error.message || 'Código incorrecto. No se ha podido desactivar el 2FA.')
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const validateLogin = useCallback(async (mfaToken: string, code: string): Promise<MfaLoginResult> => {
        setLoading(true)
        try {
            const data = await apiRequest<MfaLoginResult>('/auth/mfa/validate', {
                method: 'POST',
                body: JSON.stringify({ mfa_token: mfaToken, code }),
            })
            return data
        } catch (error: any) {
            throw new Error(error.message || 'Código incorrecto. Inténtalo de nuevo.')
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    return {
        mfaEnabled,
        loading,
        statusLoaded,
        checkStatus,
        setup,
        verify,
        disable,
        validateLogin,
    }
}
