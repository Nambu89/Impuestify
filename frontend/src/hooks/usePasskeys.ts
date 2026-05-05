/**
 * Passkey / WebAuthn React hook for Impuestify.
 *
 * Wraps @simplewebauthn/browser + the /auth/webauthn/* endpoints.
 * Provides:
 *   - isSupported(): whether the browser supports WebAuthn
 *   - registerPasskey(label?): register a new credential for the logged-in user
 *   - loginWithPasskey(email): authenticate with a passkey, returns auth tokens
 *   - listPasskeys(): list user's registered credentials
 *   - deletePasskey(id): remove a credential
 */
import { useCallback, useState } from 'react'
import {
    startRegistration,
    startAuthentication,
    browserSupportsWebAuthn,
} from '@simplewebauthn/browser'
import { useApi } from './useApi'

export interface PasskeyCredential {
    id: string
    label: string
    created_at: string
    last_used_at: string | null
}

interface AuthTokens {
    access_token: string
    refresh_token: string
    token_type: string
    user: {
        id: string
        email: string
        name: string | null
        is_admin: boolean
        is_owner: boolean
    }
}

export function usePasskeys() {
    const { apiRequest } = useApi()
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const isSupported = useCallback(() => browserSupportsWebAuthn(), [])

    const registerPasskey = useCallback(async (label?: string) => {
        setLoading(true)
        setError(null)
        try {
            // 1. Get challenge from server
            const begin = await apiRequest<any>('/auth/webauthn/register/begin', {
                method: 'POST',
                body: JSON.stringify({}),
            })

            // 2. Map server response to PublicKeyCredentialCreationOptions
            const opts = {
                challenge: begin.challenge_b64,
                rp: { name: begin.rp_name, id: begin.rp_id },
                user: {
                    id: begin.user_id_b64,
                    name: begin.user_name,
                    displayName: begin.user_name,
                },
                pubKeyCredParams: [
                    { alg: -7, type: 'public-key' as const },
                    { alg: -257, type: 'public-key' as const },
                ],
                excludeCredentials: (begin.exclude_credentials || []).map((c: any) => ({
                    id: c.id,
                    type: 'public-key' as const,
                })),
                authenticatorSelection: {
                    residentKey: 'preferred' as const,
                    userVerification: 'preferred' as const,
                },
                timeout: 60000,
            }

            // 3. Browser prompts user
            const credential = await startRegistration({ optionsJSON: opts as any })

            // 4. Send result back
            await apiRequest('/auth/webauthn/register/complete', {
                method: 'POST',
                body: JSON.stringify({ credential, label }),
            })
            return true
        } catch (e: any) {
            const msg = e?.message || 'No se pudo registrar la passkey'
            setError(msg)
            return false
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const loginWithPasskey = useCallback(async (email: string): Promise<AuthTokens | null> => {
        setLoading(true)
        setError(null)
        try {
            const begin = await apiRequest<any>('/auth/webauthn/login/begin', {
                method: 'POST',
                body: JSON.stringify({ email }),
            })

            if (!begin.allow_credentials || begin.allow_credentials.length === 0) {
                throw new Error('No tienes passkeys registradas. Inicia con contraseña.')
            }

            const opts = {
                challenge: begin.challenge_b64,
                rpId: begin.rp_id,
                allowCredentials: begin.allow_credentials.map((c: any) => ({
                    id: c.id,
                    type: 'public-key' as const,
                })),
                userVerification: 'preferred' as const,
                timeout: 60000,
            }

            const assertion = await startAuthentication({ optionsJSON: opts as any })

            const tokens = await apiRequest<AuthTokens>('/auth/webauthn/login/complete', {
                method: 'POST',
                body: JSON.stringify({ email, credential: assertion }),
            })
            return tokens
        } catch (e: any) {
            const msg = e?.message || 'No se pudo iniciar sesión con passkey'
            setError(msg)
            return null
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const listPasskeys = useCallback(async (): Promise<PasskeyCredential[]> => {
        setLoading(true)
        try {
            const data = await apiRequest<{ credentials: PasskeyCredential[] }>('/auth/webauthn/credentials')
            return data.credentials || []
        } catch (e: any) {
            setError(e?.message || 'No se pudieron cargar las passkeys')
            return []
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const deletePasskey = useCallback(async (credId: string) => {
        setLoading(true)
        try {
            await apiRequest(`/auth/webauthn/credentials/${credId}`, { method: 'DELETE' })
            return true
        } catch (e: any) {
            setError(e?.message || 'No se pudo eliminar la passkey')
            return false
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    return {
        isSupported,
        registerPasskey,
        loginWithPasskey,
        listPasskeys,
        deletePasskey,
        loading,
        error,
    }
}
