/**
 * CookieConsent Component
 *
 * LSSI-CE + RGPD compliant cookie consent banner using vanilla-cookieconsent v3.
 * Configured with Spanish translations following AEPD guidelines:
 * - Accept/Reject buttons at same visual level (no dark patterns)
 * - Granular category configuration
 * - 6-month consent cookie duration
 */
import { useEffect } from 'react';
import 'vanilla-cookieconsent/dist/cookieconsent.css';
import * as CookieConsent from 'vanilla-cookieconsent';

export function showCookiePreferences() {
    CookieConsent.showPreferences();
}

export default function CookieConsentBanner() {
    useEffect(() => {
        CookieConsent.run({
            guiOptions: {
                consentModal: {
                    layout: 'bar',
                    position: 'bottom',
                    equalWeightButtons: true,
                },
                preferencesModal: {
                    layout: 'box',
                    position: 'right',
                    equalWeightButtons: true,
                },
            },

            categories: {
                necessary: {
                    enabled: true,
                    readOnly: true,
                },
                analytics: {},
            },

            cookie: {
                name: 'cc_cookie',
                expiresAfterDays: 182, // ~6 meses (recomendacion AEPD: max 13 meses)
            },

            language: {
                default: 'es',
                translations: {
                    es: {
                        consentModal: {
                            title: 'Cookies',
                            description:
                                'Usamos cookies propias y almacenamiento local para que el servicio funcione. Las no esenciales ' +
                                'las decides tú: aceptar, rechazar o afinarlas en preferencias. Detalles completos en la ' +
                                '<a href="/politica-cookies">Política de Cookies</a>.',
                            acceptAllBtn: 'Aceptar todas',
                            acceptNecessaryBtn: 'Rechazar',
                            showPreferencesBtn: 'Configurar cookies',
                        },
                        preferencesModal: {
                            title: 'Configuración de cookies',
                            acceptAllBtn: 'Aceptar todas',
                            acceptNecessaryBtn: 'Rechazar no esenciales',
                            savePreferencesBtn: 'Guardar preferencias',
                            closeIconLabel: 'Cerrar',
                            sections: [
                                {
                                    title: 'Cookies y almacenamiento local',
                                    description:
                                        'Usamos cookies y localStorage para que el servicio funcione. En el futuro podrán servir para métricas ' +
                                        'anónimas de uso. Activa o desactiva cada categoría según prefieras. ' +
                                        'Detalles en la <a href="/politica-cookies">Política de Cookies</a>.',
                                },
                                {
                                    title: 'Cookies estrictamente necesarias',
                                    description:
                                        'Sin estas cookies el sitio no funciona. Cubren la autenticación (JWT) y el propio registro de tus ' +
                                        'preferencias de cookies. No se pueden desactivar.',
                                    linkedCategory: 'necessary',
                                    cookieTable: {
                                        headers: {
                                            name: 'Nombre',
                                            domain: 'Proveedor',
                                            description: 'Propósito',
                                            expiration: 'Duración',
                                        },
                                        body: [
                                            {
                                                name: 'cc_cookie',
                                                domain: 'Impuestify',
                                                description: 'Almacena tus preferencias de consentimiento de cookies.',
                                                expiration: '6 meses',
                                            },
                                            {
                                                name: 'access_token',
                                                domain: 'Impuestify (localStorage)',
                                                description: 'Token de autenticación para mantener tu sesión iniciada.',
                                                expiration: 'Sesión',
                                            },
                                            {
                                                name: 'refresh_token',
                                                domain: 'Impuestify (localStorage)',
                                                description: 'Token para renovar la sesión de forma segura.',
                                                expiration: '7 días',
                                            },
                                        ],
                                    },
                                },
                                {
                                    title: 'Cookies analíticas',
                                    description:
                                        'Servirían para ver de forma anónima cómo se usa la plataforma. Hoy por hoy no usamos ninguna: ' +
                                        'esta categoría queda reservada por si las incorporamos más adelante. ' +
                                        'Están desactivadas por defecto y solo se activan con tu consentimiento.',
                                    linkedCategory: 'analytics',
                                    cookieTable: {
                                        headers: {
                                            name: 'Nombre',
                                            domain: 'Proveedor',
                                            description: 'Propósito',
                                            expiration: 'Duración',
                                        },
                                        body: [
                                            {
                                                name: 'Ninguna actualmente',
                                                domain: '-',
                                                description: 'No se utilizan cookies analíticas en este momento.',
                                                expiration: '-',
                                            },
                                        ],
                                    },
                                },
                                {
                                    title: 'Más información',
                                    description:
                                        'Si algo no te cuadra en la política de cookies, escríbenos a <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a>.',
                                },
                            ],
                        },
                    },
                },
            },
        });
    }, []);

    return null;
}
