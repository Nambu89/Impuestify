/**
 * Terms of Service Page
 * Full terms adapted from TERMS_OF_SERVICE.md
 */
import { Link } from 'react-router-dom';
import './LegalPage.css';

export default function TermsPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">&larr; Volver al inicio</Link>

                <h1>Terminos y Condiciones de Servicio</h1>
                <p className="subtitle">Impuestify - Asistente Fiscal Inteligente</p>
                <p className="last-updated">Ultima actualizacion: 3 de enero de 2026 | Version 1.0</p>

                <section>
                    <h2>1. Aceptacion de los Terminos</h2>
                    <p>
                        Al acceder y utilizar Impuestify (&quot;el Servicio&quot;), usted acepta estar sujeto
                        a estos Terminos y Condiciones (&quot;Terminos&quot;).
                    </p>
                    <p><strong>Si no esta de acuerdo</strong>: No utilice el Servicio.</p>
                </section>

                <section>
                    <h2>2. Descripcion del Servicio</h2>
                    <p>
                        Impuestify es un <strong>asistente fiscal conversacional</strong> basado en inteligencia
                        artificial que proporciona:
                    </p>
                    <ul>
                        <li>Respuestas a consultas sobre normativa fiscal espanola</li>
                        <li>Calculos de IRPF y cuotas de autonomos</li>
                        <li>Analisis de nominas y notificaciones AEAT</li>
                        <li>Busqueda de informacion en fuentes oficiales</li>
                    </ul>
                    <div className="alert alert-warning">
                        <strong>Limitaciones del Servicio</strong>
                        <ul>
                            <li><strong>NO es un asesor fiscal profesional</strong></li>
                            <li>NO realiza tramites ante la AEAT</li>
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
                        Usted es el unico responsable de las decisiones tomadas basandose
                        en informacion del Servicio.
                    </p>

                    <h3>3.2 Uso de Inteligencia Artificial</h3>
                    <p>Impuestify utiliza modelos de IA (OpenAI) que pueden:</p>
                    <ul>
                        <li>Cometer errores (&quot;alucinaciones&quot;)</li>
                        <li>Proporcionar informacion desactualizada</li>
                        <li>Malinterpretar consultas complejas</li>
                    </ul>
                    <p>
                        <strong>Mitigaciones aplicadas</strong>: RAG, citacion de fuentes, moderacion de contenido.
                        Ver <Link to="/ai-transparency">Transparencia IA</Link>.
                    </p>

                    <h3>3.3 Precision de la Informacion</h3>
                    <p>
                        <strong>NO GARANTIZAMOS</strong>: Exactitud completa de calculos, actualizacion en tiempo
                        real de normativa, ni aplicabilidad a su caso particular.
                    </p>
                </section>

                <section>
                    <h2>4. Registro y Cuenta de Usuario</h2>
                    <h3>4.1 Requisitos</h3>
                    <ul>
                        <li>Mayor de 16 anos (RGPD Art. 8)</li>
                        <li>Informacion veraz y actualizada</li>
                        <li>Responsabilidad de mantener credenciales seguras</li>
                    </ul>

                    <h3>4.2 Seguridad de la Cuenta</h3>
                    <p>
                        Usted es responsable de mantener la confidencialidad de su contrasena,
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
                                <li>Hacer consultas fiscales legitimas</li>
                                <li>Subir nominas/notificaciones propias</li>
                                <li>Usar respuestas como informacion orientativa</li>
                                <li>Compartir respuestas (con atribucion)</li>
                            </ul>
                        </div>
                        <div>
                            <h3>Usted NO PUEDE</h3>
                            <ul>
                                <li>Usar para evasion fiscal o actividades ilegales</li>
                                <li>Intentar hackear o manipular el sistema</li>
                                <li>Subir contenido malicioso</li>
                                <li>Hacer spam o uso masivo automatizado</li>
                                <li>Usar para servicios comerciales sin autorizacion</li>
                            </ul>
                        </div>
                    </div>
                    <p><strong>Violacion</strong>: Podemos suspender o terminar su cuenta.</p>
                </section>

                <section>
                    <h2>6. Propiedad Intelectual</h2>
                    <h3>6.1 Derechos de Impuestify</h3>
                    <p>
                        Todo el contenido del Servicio (codigo, diseno, marca) es propiedad de
                        Impuestify o sus licenciantes. Se otorga licencia de uso personal no comercial.
                    </p>

                    <h3>6.2 Sus Derechos sobre sus Datos</h3>
                    <p>
                        Usted conserva la propiedad de sus consultas, documentos y conversaciones.
                        Nos otorga licencia limitada para procesar sus datos con el fin de prestar el Servicio.
                    </p>
                    <p>Ver: <Link to="/privacy-policy">Politica de Privacidad</Link></p>
                </section>

                <section>
                    <h2>7. Privacidad y Datos Personales</h2>
                    <p>Cumplimos con:</p>
                    <ul>
                        <li>RGPD (Reglamento UE 2016/679)</li>
                        <li>LOPDGDD (Ley Organica 3/2018 - Espana)</li>
                        <li>AI Act (Reglamento UE 2024/1689)</li>
                    </ul>
                    <p>
                        Consulte nuestra <Link to="/privacy-policy">Politica de Privacidad</Link> completa.
                    </p>
                </section>

                <section>
                    <h2>8. Limitacion de Responsabilidad</h2>
                    <h3>8.1 Exclusion de Garantias</h3>
                    <p>
                        El Servicio se proporciona &quot;tal cual&quot; y &quot;segun disponibilidad&quot;,
                        sin garantias de ningún tipo.
                    </p>

                    <h3>8.2 Limite de Responsabilidad</h3>
                    <p>
                        En la medida maxima permitida por la ley, Impuestify no sera responsable de
                        decisiones fiscales tomadas basandose en el Servicio, multas, sanciones o
                        perdidas economicas, errores u omisiones de la IA, perdida de datos, ni danos
                        indirectos o consecuenciales.
                    </p>
                    <p>
                        <strong>Responsabilidad maxima</strong>: Importe pagado por el Servicio en los ultimos 12 meses.
                    </p>

                    <h3>8.3 Jurisdiccion</h3>
                    <p>Nada en estos Terminos limita derechos del consumidor bajo ley aplicable (UE/Espana).</p>
                </section>

                <section>
                    <h2>9. Modificaciones del Servicio</h2>
                    <p>Nos reservamos el derecho a modificar, suspender o discontinuar el Servicio,
                        cambiar precios y actualizar funcionalidades.</p>
                    <p><strong>Notificacion</strong>: Cambios sustanciales se notificaran con 30 dias de antelacion.</p>
                </section>

                <section>
                    <h2>10. Modificaciones de los Terminos</h2>
                    <p>
                        Cambios sustanciales se notificaran por email 30 dias antes con oportunidad
                        de rechazar y cerrar cuenta. Cambios menores se publican en web.
                        El uso continuado tras cambios implica aceptacion de nuevos Terminos.
                    </p>
                </section>

                <section>
                    <h2>11. Terminacion</h2>
                    <h3>11.1 Por su Parte</h3>
                    <p>
                        Puede cancelar su cuenta en cualquier momento desde Configuracion o
                        enviando email a <a href="mailto:support@impuestify.com">support@impuestify.com</a>.
                    </p>

                    <h3>11.2 Por Nuestra Parte</h3>
                    <p>
                        Podemos suspender o terminar su cuenta si viola estos Terminos, usa
                        el Servicio para actividades ilegales o abusa del sistema.
                    </p>

                    <h3>11.3 Efectos de la Terminacion</h3>
                    <p>
                        Tras terminacion: su cuenta se cierra y los datos se eliminan
                        segun la <Link to="/data-retention">Politica de Retencion de Datos</Link>.
                    </p>
                </section>

                <section>
                    <h2>12. Resolucion de Disputas</h2>
                    <p>
                        Estos Terminos se rigen por legislacion espanola. Tribunales de Espana
                        tendran jurisdiccion exclusiva. Antes de acudir a tribunales,
                        contacte <a href="mailto:support@impuestify.com">support@impuestify.com</a> para
                        intentar resolver amistosamente.
                    </p>
                </section>

                <section>
                    <h2>13. Miscelanea</h2>
                    <ul>
                        <li><strong>Independencia de Clausulas</strong>: Si alguna disposicion es invalida, las demas permanecen en vigor.</li>
                        <li><strong>Renuncia</strong>: Fallo en ejercer derecho no constituye renuncia.</li>
                        <li><strong>Cesion</strong>: No puede ceder estos Terminos sin nuestro consentimiento.</li>
                        <li><strong>Acuerdo Completo</strong>: Estos Terminos junto con la Politica de Privacidad constituyen el acuerdo completo.</li>
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
                        Estos Terminos se proporcionan en espanol.
                        En caso de conflicto con traducciones, prevalece la version en espanol.
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Al usar Impuestify, usted confirma que ha leido y entendido estos Terminos,
                        la <Link to="/privacy-policy">Politica de Privacidad</Link> y la
                        informacion sobre <Link to="/ai-transparency">Transparencia IA</Link>.
                    </p>
                </div>
            </div>
        </div>
    );
}
