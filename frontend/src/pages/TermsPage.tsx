/**
 * Terms of Service Page
 * Full terms adapted from TERMS_OF_SERVICE.md
 */
import { Link } from 'react-router-dom';
import { LegalEntity } from '../components/legal/LegalEntity';
import './LegalPage.css';

export default function TermsPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">&larr; Volver al inicio</Link>

                <h1>Términos y Condiciones de Servicio</h1>
                <p className="subtitle">Impuestify - Asistente Fiscal Inteligente</p>
                <p className="last-updated">Última actualización: 23 de abril de 2026 | Versión 1.1</p>

                <LegalEntity title="0. Titular del servicio" />

                <section>
                    <h2>1. Aceptación de los Términos</h2>
                    <p>
                        Al acceder y utilizar Impuestify (&quot;el Servicio&quot;), usted acepta estar sujeto
                        a estos Términos y Condiciones (&quot;Términos&quot;).
                    </p>
                    <p><strong>Si no está de acuerdo</strong>: No utilice el Servicio.</p>
                </section>

                <section>
                    <h2>2. Descripción del Servicio</h2>
                    <p>
                        Impuestify es un <strong>asistente fiscal conversacional</strong> basado en inteligencia
                        artificial que proporciona:
                    </p>
                    <ul>
                        <li>Respuestas a consultas sobre normativa fiscal española</li>
                        <li>Cálculos de IRPF y cuotas de autónomos</li>
                        <li>Análisis de nóminas y notificaciones AEAT</li>
                        <li>Búsqueda de información en fuentes oficiales</li>
                    </ul>
                    <div className="alert alert-warning">
                        <strong>Limitaciones del Servicio</strong>
                        <ul>
                            <li><strong>NO es un asesor fiscal profesional</strong></li>
                            <li>NO realiza trámites ante la AEAT</li>
                            <li>NO garantiza exactitud al 100%</li>
                            <li>NO sustituye asesoramiento legal</li>
                        </ul>
                    </div>
                </section>

                <section>
                    <h2>3. Disclaimer Legal</h2>
                    <div className="alert alert-info">
                        <strong>Importante</strong>
                        <p>
                            Las respuestas de Impuestify son <strong>ORIENTATIVAS</strong>. El contenido NO constituye
                            asesoramiento fiscal, legal o financiero profesional. SIEMPRE consulte con un asesor
                            fiscal cualificado antes de actuar.
                        </p>
                    </div>

                    <h3>3.1 No es Asesoramiento Profesional</h3>
                    <p>
                        Usted es el único responsable de las decisiones tomadas basándose
                        en información del Servicio.
                    </p>

                    <h3>3.2 Uso de Inteligencia Artificial</h3>
                    <p>Impuestify utiliza modelos de IA (OpenAI) que pueden:</p>
                    <ul>
                        <li>Cometer errores (&quot;alucinaciones&quot;)</li>
                        <li>Proporcionar información desactualizada</li>
                        <li>Malinterpretar consultas complejas</li>
                    </ul>
                    <p>
                        <strong>Mitigaciones aplicadas</strong>: RAG, citación de fuentes, moderación de contenido.
                        Ver <Link to="/ai-transparency">Transparencia IA</Link>.
                    </p>

                    <h3>3.3 Precisión de la Información</h3>
                    <p>
                        <strong>NO GARANTIZAMOS</strong>: Exactitud completa de cálculos, actualización en tiempo
                        real de normativa, ni aplicabilidad a su caso particular.
                    </p>
                </section>

                <section>
                    <h2>4. Registro y Cuenta de Usuario</h2>
                    <h3>4.1 Requisitos</h3>
                    <ul>
                        <li>Mayor de 16 años (RGPD Art. 8)</li>
                        <li>Información veraz y actualizada</li>
                        <li>Responsabilidad de mantener credenciales seguras</li>
                    </ul>

                    <h3>4.2 Seguridad de la Cuenta</h3>
                    <p>
                        Usted es responsable de mantener la confidencialidad de su contraseña,
                        todas las actividades bajo su cuenta, y notificar inmediatamente
                        cualquier uso no autorizado.
                    </p>
                </section>

                <section>
                    <h2>5. Uso Aceptable</h2>
                    <div className="two-column">
                        <div>
                            <h3>Usted PUEDE</h3>
                            <ul>
                                <li>Hacer consultas fiscales legítimas</li>
                                <li>Subir nóminas/notificaciones propias</li>
                                <li>Usar respuestas como información orientativa</li>
                                <li>Compartir respuestas (con atribución)</li>
                            </ul>
                        </div>
                        <div>
                            <h3>Usted NO PUEDE</h3>
                            <ul>
                                <li>Usar para evasión fiscal o actividades ilegales</li>
                                <li>Intentar hackear o manipular el sistema</li>
                                <li>Subir contenido malicioso</li>
                                <li>Hacer spam o uso masivo automatizado</li>
                                <li>Usar para servicios comerciales sin autorización</li>
                            </ul>
                        </div>
                    </div>
                    <p><strong>Violación</strong>: Podemos suspender o terminar su cuenta.</p>
                </section>

                <section>
                    <h2>6. Propiedad Intelectual</h2>
                    <h3>6.1 Derechos de Impuestify</h3>
                    <p>
                        Todo el contenido del Servicio (código, diseño, marca) es propiedad de
                        Impuestify o sus licenciantes. Se otorga licencia de uso personal no comercial.
                    </p>

                    <h3>6.2 Sus Derechos sobre sus Datos</h3>
                    <p>
                        Usted conserva la propiedad de sus consultas, documentos y conversaciones.
                        Nos otorga licencia limitada para procesar sus datos con el fin de prestar el Servicio.
                    </p>
                    <p>Ver: <Link to="/privacy-policy">Política de Privacidad</Link></p>
                </section>

                <section>
                    <h2>7. Privacidad y Datos Personales</h2>
                    <p>Cumplimos con:</p>
                    <ul>
                        <li>RGPD (Reglamento UE 2016/679)</li>
                        <li>LOPDGDD (Ley Orgánica 3/2018 - España)</li>
                        <li>AI Act (Reglamento UE 2024/1689)</li>
                    </ul>
                    <p>
                        Consulte nuestra <Link to="/privacy-policy">Política de Privacidad</Link> completa.
                    </p>
                </section>

                <section>
                    <h2>8. Limitación de Responsabilidad</h2>
                    <h3>8.1 Exclusión de Garantías</h3>
                    <p>
                        El Servicio se proporciona &quot;tal cual&quot; y &quot;según disponibilidad&quot;,
                        sin garantías de ningún tipo.
                    </p>

                    <h3>8.2 Límite de Responsabilidad</h3>
                    <p>
                        En la medida máxima permitida por la ley, Impuestify no será responsable de
                        decisiones fiscales tomadas basándose en el Servicio, multas, sanciones o
                        pérdidas económicas, errores u omisiones de la IA, pérdida de datos, ni daños
                        indirectos o consecuenciales.
                    </p>
                    <p>
                        <strong>Responsabilidad máxima</strong>: Importe pagado por el Servicio en los últimos 12 meses.
                    </p>

                    <h3>8.3 Jurisdicción</h3>
                    <p>Nada en estos Términos limita derechos del consumidor bajo ley aplicable (UE/España).</p>
                </section>

                <section>
                    <h2>9. Modificaciones del Servicio</h2>
                    <p>Nos reservamos el derecho de modificar, suspender o discontinuar el Servicio,
                        cambiar precios y actualizar funcionalidades.</p>
                    <p><strong>Notificación</strong>: Cambios sustanciales se notificarán con 30 días de antelación.</p>
                </section>

                <section>
                    <h2>10. Modificaciones de los Términos</h2>
                    <p>
                        Cambios sustanciales se notificarán por email 30 días antes con oportunidad
                        de rechazar y cerrar cuenta. Cambios menores se publican en web.
                        El uso continuado tras cambios implica aceptación de nuevos Términos.
                    </p>
                </section>

                <section>
                    <h2>11. Terminación</h2>
                    <h3>11.1 Por su Parte</h3>
                    <p>
                        Puede cancelar su cuenta en cualquier momento desde Configuración o
                        enviando email a <a href="mailto:support@impuestify.com">support@impuestify.com</a>.
                    </p>

                    <h3>11.2 Por Nuestra Parte</h3>
                    <p>
                        Podemos suspender o terminar su cuenta si viola estos Términos, usa
                        el Servicio para actividades ilegales o abusa del sistema.
                    </p>

                    <h3>11.3 Efectos de la Terminación</h3>
                    <p>
                        Tras terminación: su cuenta se cierra y los datos se eliminan
                        según la <Link to="/data-retention">Política de Retención de Datos</Link>.
                    </p>
                </section>

                <section>
                    <h2>12. Resolución de Disputas</h2>
                    <p>
                        Estos Términos se rigen por legislación española. Tribunales de España
                        tendrán jurisdicción exclusiva. Antes de acudir a tribunales,
                        contacte <a href="mailto:support@impuestify.com">support@impuestify.com</a> para
                        intentar resolver amistosamente.
                    </p>
                </section>

                <section>
                    <h2>13. Miscelánea</h2>
                    <ul>
                        <li><strong>Independencia de Cláusulas</strong>: Si alguna disposición es inválida, las demás permanecen en vigor.</li>
                        <li><strong>Renuncia</strong>: Fallo en ejercer derecho no constituye renuncia.</li>
                        <li><strong>Cesión</strong>: No puede ceder estos Términos sin nuestro consentimiento.</li>
                        <li><strong>Acuerdo Completo</strong>: Estos Términos junto con la Política de Privacidad constituyen el acuerdo completo.</li>
                    </ul>
                </section>

                <section>
                    <h2>14. Contacto</h2>
                    <p>
                        <strong>Preguntas sobre Terminos</strong>: <a href="mailto:legal@impuestify.com">legal@impuestify.com</a><br />
                        <strong>Soporte general</strong>: <a href="mailto:support@impuestify.com">support@impuestify.com</a><br />
                        <strong>Privacidad</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a>
                    </p>
                </section>

                <section>
                    <h2>15. Idioma</h2>
                    <p>
                        Estos Términos se proporcionan en español.
                        En caso de conflicto con traducciones, prevalece la versión en español.
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Al usar Impuestify, usted confirma que ha leído y entendido estos Términos,
                        la <Link to="/privacy-policy">Política de Privacidad</Link> y la
                        información sobre <Link to="/ai-transparency">Transparencia IA</Link>.
                    </p>
                </div>
            </div>
        </div>
    );
}
