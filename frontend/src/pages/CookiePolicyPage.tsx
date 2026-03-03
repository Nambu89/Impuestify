/**
 * Cookie Policy Page
 *
 * LSSI-CE (Art. 22.2) + RGPD compliant cookie policy.
 * Content follows AEPD Guía de Cookies (mayo 2024).
 */
import { Link } from 'react-router-dom';
import { showCookiePreferences } from '../components/CookieConsent';
import './LegalPage.css';

export default function CookiePolicyPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">← Volver al inicio</Link>

                <h1>Política de Cookies</h1>
                <p className="last-updated">Última actualización: 3 de marzo de 2026</p>

                <section>
                    <h2>1. ¿Qué son las cookies?</h2>
                    <p>
                        Las cookies son pequeños archivos de texto que los sitios web almacenan en tu dispositivo
                        (ordenador, tablet o móvil) cuando los visitas. Permiten que el sitio recuerde tus acciones
                        y preferencias durante un período de tiempo.
                    </p>
                    <p>
                        Además de las cookies HTTP tradicionales, existen otras tecnologías de almacenamiento local
                        como <strong>localStorage</strong> y <strong>sessionStorage</strong> que cumplen funciones similares.
                        De acuerdo con la normativa vigente (LSSI-CE Art. 22.2 y guía de la AEPD), informamos sobre
                        todas las tecnologías de almacenamiento utilizadas en nuestro sitio.
                    </p>
                </section>

                <section>
                    <h2>2. Cookies y almacenamiento que utilizamos</h2>
                    <p>A continuación se detalla cada elemento de almacenamiento utilizado por Impuestify:</p>

                    <h3>2.1 Cookies estrictamente necesarias</h3>
                    <p>
                        Son imprescindibles para el funcionamiento del sitio. No requieren consentimiento previo
                        (LSSI-CE Art. 22.2, excepción de cookies técnicas).
                    </p>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Proveedor</th>
                                <th>Propósito</th>
                                <th>Duración</th>
                                <th>Tipo</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><code>cc_cookie</code></td>
                                <td>Impuestify</td>
                                <td>Almacena tus preferencias de consentimiento de cookies</td>
                                <td>6 meses</td>
                                <td>Cookie HTTP</td>
                            </tr>
                            <tr>
                                <td><code>access_token</code></td>
                                <td>Impuestify</td>
                                <td>Token JWT para autenticación de usuario</td>
                                <td>Sesión (30 min)</td>
                                <td>localStorage</td>
                            </tr>
                            <tr>
                                <td><code>refresh_token</code></td>
                                <td>Impuestify</td>
                                <td>Token para renovar la sesión de forma segura</td>
                                <td>7 días</td>
                                <td>localStorage</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>2.2 Cookies analíticas</h3>
                    <p>
                        Actualmente <strong>no utilizamos cookies analíticas ni de terceros</strong>.
                        No se instala Google Analytics, Meta Pixel ni ningún otro servicio de tracking.
                    </p>
                    <p>
                        Si en el futuro incorporamos herramientas de analítica (como Plausible o Umami),
                        esta sección se actualizará y se solicitará tu consentimiento antes de su activación.
                    </p>

                    <h3>2.3 Cookies de marketing</h3>
                    <p>
                        <strong>No utilizamos cookies de marketing ni publicidad</strong>. Impuestify no muestra
                        anuncios ni comparte datos con plataformas publicitarias.
                    </p>
                </section>

                <section>
                    <h2>3. Base legal</h2>
                    <ul>
                        <li>
                            <strong>Cookies necesarias</strong>: Exentas de consentimiento por ser estrictamente necesarias
                            para la prestación del servicio (LSSI-CE Art. 22.2, considerando 25 Directiva 2002/58/CE).
                        </li>
                        <li>
                            <strong>Cookies analíticas</strong> (futuro): Requieren consentimiento explícito previo
                            del usuario (RGPD Art. 6.1.a, LSSI-CE Art. 22.2).
                        </li>
                    </ul>
                </section>

                <section>
                    <h2>4. Cómo gestionar las cookies</h2>

                    <h3>4.1 Desde nuestro panel de configuración</h3>
                    <p>
                        Puedes modificar tus preferencias de cookies en cualquier momento haciendo clic en el
                        siguiente botón:
                    </p>
                    <p>
                        <button
                            onClick={showCookiePreferences}
                            className="badge-large"
                            style={{ cursor: 'pointer', border: 'none' }}
                        >
                            Configurar preferencias de cookies
                        </button>
                    </p>

                    <h3>4.2 Desde tu navegador</h3>
                    <p>
                        También puedes configurar tu navegador para bloquear o eliminar cookies.
                        Ten en cuenta que bloquear las cookies necesarias puede impedir el funcionamiento del servicio.
                    </p>
                    <ul>
                        <li>
                            <strong>Google Chrome</strong>: Configuración → Privacidad y seguridad → Cookies y otros datos de sitios
                        </li>
                        <li>
                            <strong>Mozilla Firefox</strong>: Configuración → Privacidad y seguridad → Cookies y datos del sitio
                        </li>
                        <li>
                            <strong>Safari</strong>: Preferencias → Privacidad → Gestión de datos del sitio web
                        </li>
                        <li>
                            <strong>Microsoft Edge</strong>: Configuración → Cookies y permisos del sitio → Cookies y datos almacenados
                        </li>
                    </ul>
                    <p>
                        Para eliminar datos de <strong>localStorage</strong>, accede a las herramientas de desarrollo
                        de tu navegador (F12) → Aplicación → Almacenamiento local.
                    </p>
                </section>

                <section>
                    <h2>5. Cómo retirar el consentimiento</h2>
                    <p>
                        Puedes retirar tu consentimiento en cualquier momento utilizando el botón
                        "Configurar preferencias de cookies" de la sección anterior, o desde el enlace
                        "Configurar Cookies" disponible en el pie de página de cualquier página del sitio.
                    </p>
                    <p>
                        La retirada del consentimiento no afecta a la licitud del tratamiento basado en
                        el consentimiento previo a su retirada (RGPD Art. 7.3).
                    </p>
                </section>

                <section>
                    <h2>6. Transferencias internacionales</h2>
                    <p>
                        Las cookies y datos de almacenamiento local descritos en esta política se procesan
                        exclusivamente en tu dispositivo. No se transfieren a servidores de terceros países.
                    </p>
                    <p>
                        Para información sobre transferencias internacionales relacionadas con otros datos
                        personales, consulta nuestra <Link to="/privacy-policy">Política de Privacidad</Link>.
                    </p>
                </section>

                <section>
                    <h2>7. Responsable del tratamiento</h2>
                    <p><strong>Impuestify</strong></p>
                    <p>Email de contacto: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a></p>
                </section>

                <section>
                    <h2>8. Normativa aplicable</h2>
                    <ul>
                        <li>
                            <strong>LSSI-CE</strong> (Ley 34/2002, Art. 22.2) — Ley de Servicios de la Sociedad de la Información
                        </li>
                        <li>
                            <strong>RGPD</strong> (Reglamento UE 2016/679) — Reglamento General de Protección de Datos
                        </li>
                        <li>
                            <strong>LOPDGDD</strong> (Ley Orgánica 3/2018) — Ley Orgánica de Protección de Datos y Garantía de los Derechos Digitales
                        </li>
                        <li>
                            <strong>Guía de Cookies AEPD</strong> (actualizada mayo 2024) — Guía sobre el uso de cookies
                        </li>
                    </ul>
                </section>

                <section>
                    <h2>9. Autoridad de control</h2>
                    <p>
                        Agencia Española de Protección de Datos (AEPD)<br />
                        Web: <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">www.aepd.es</a>
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Para más información sobre cómo tratamos tus datos personales, consulta nuestra{' '}
                        <Link to="/privacy-policy">Política de Privacidad</Link>.
                    </p>
                </div>
            </div>
        </div>
    );
}
