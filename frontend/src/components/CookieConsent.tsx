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
                            title: 'Utilizamos cookies',
                            description:
                                'Utilizamos cookies propias y tecnologías de almacenamiento local para el funcionamiento del servicio y mejorar tu experiencia. ' +
                                'Puedes aceptar todas, rechazar las no esenciales o configurar tus preferencias. ' +
                                'Consulta nuestra <a href="/politica-cookies">Política de Cookies</a> para más información.',
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
                                    title: 'Uso de cookies y almacenamiento local',
                                    description:
                                        'Utilizamos cookies y almacenamiento local (localStorage) para garantizar el funcionamiento del servicio ' +
                                        'y, en el futuro, para analizar el uso de la plataforma de forma anónima. ' +
                                        'Puedes activar o desactivar cada categoría según tus preferencias. ' +
                                        'Para más detalles, consulta nuestra <a href="/politica-cookies">Política de Cookies</a>.',
                                },
                                {
                                    title: 'Cookies estrictamente necesarias',
                                    description:
                                        'Estas cookies y datos de almacenamiento local son imprescindibles para que el sitio funcione correctamente. ' +
                                        'Incluyen la autenticación del usuario (JWT) y el registro de tus preferencias de cookies. ' +
                                        'No se pueden desactivar.',
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
                                        'Estas cookies nos permiten analizar de forma anónima cómo se utiliza la plataforma para poder mejorarla. ' +
                                        'Actualmente no utilizamos cookies analíticas, pero esta categoría queda preparada para el futuro. ' +
                                        'Están desactivadas por defecto y solo se activarán con tu consentimiento.',
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
                                        'Si tienes dudas sobre nuestra política de cookies, puedes <a href="mailto:privacy@impuestify.com">contactarnos</a>.',
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
