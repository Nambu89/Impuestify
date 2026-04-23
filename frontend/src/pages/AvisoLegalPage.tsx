/**
 * Aviso Legal (LSSI-CE Art. 10).
 *
 * Identificacion del prestador, condiciones de uso, propiedad intelectual,
 * limitacion de responsabilidad, legislacion aplicable y jurisdiccion.
 *
 * Complementario a Terminos y Condiciones: este documento identifica al
 * prestador y establece las reglas basicas de uso; los Terminos regulan
 * la relacion contractual de los usuarios registrados.
 */
import { Link } from 'react-router-dom';
import { LegalEntity } from '../components/legal/LegalEntity';
import './LegalPage.css';

export default function AvisoLegalPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">&larr; Volver al inicio</Link>

                <h1>Aviso Legal</h1>
                <p className="subtitle">Impuestify &mdash; Asistente Fiscal Inteligente</p>
                <p className="last-updated">Última actualización: 23 de abril de 2026 | Versión 1.0</p>

                <LegalEntity title="1. Identificación del prestador de servicios" />

                <section>
                    <h2>2. Objeto</h2>
                    <p>
                        El presente Aviso Legal regula el acceso y uso del sitio web{' '}
                        <a href="https://impuestify.com" target="_blank" rel="noreferrer">
                            https://impuestify.com
                        </a>{' '}
                        (en adelante, el &laquo;Sitio Web&raquo;) y de los servicios que se prestan a
                        través del mismo (en adelante, los &laquo;Servicios&raquo;), titularidad de Impuestify.
                    </p>
                    <p>
                        Los Servicios consisten en una plataforma web de asistencia fiscal apoyada en
                        inteligencia artificial que ofrece, entre otras funcionalidades: cálculo de IRPF,
                        simulador de Impuesto sobre Sociedades (Modelo 200), clasificación y contabilización
                        de facturas, generación de borradores de modelos oficiales, análisis de nóminas y
                        notificaciones de la AEAT, defensa frente a requerimientos tributarios (módulo
                        DefensIA) y calculadoras fiscales públicas. La descripción detallada de los Servicios,
                        así como los planes de suscripción y sus condiciones, se recogen en los{' '}
                        <Link to="/terms-of-service">Términos y Condiciones de Servicio</Link>.
                    </p>
                </section>

                <section>
                    <h2>3. Condiciones de acceso y uso</h2>
                    <p>
                        El acceso al Sitio Web es libre y gratuito. El uso de determinados Servicios requiere
                        el registro previo del usuario y la aceptación expresa de los{' '}
                        <Link to="/terms-of-service">Términos y Condiciones de Servicio</Link> y de la{' '}
                        <Link to="/privacy-policy">Política de Privacidad</Link>.
                    </p>
                    <p>
                        El usuario se compromete a utilizar el Sitio Web y los Servicios conforme a la
                        legislación vigente, la buena fe, la moral y el orden público, absteniéndose de
                        realizar cualquier conducta que pueda dañar la imagen, intereses o derechos de
                        Impuestify o de terceros, así como cualquier actividad que pueda inutilizar,
                        sobrecargar o deteriorar el Sitio Web o impedir su normal utilización.
                    </p>
                </section>

                <section>
                    <h2>4. Propiedad intelectual e industrial</h2>
                    <p>
                        Todos los contenidos del Sitio Web, incluyendo a título enunciativo y no limitativo
                        los textos, fotografías, gráficos, imágenes, iconos, tecnología, software, enlaces y
                        demás contenidos audiovisuales o sonoros, así como su diseño gráfico y códigos fuente,
                        son propiedad intelectual de Impuestify o de terceros, sin que puedan entenderse
                        cedidos al usuario ninguno de los derechos de explotación reconocidos por la normativa
                        vigente en materia de propiedad intelectual.
                    </p>
                    <p>
                        Las marcas, nombres comerciales, signos distintivos y logotipos mostrados en el Sitio
                        Web son titularidad de Impuestify o de terceros, no pudiendo entenderse que su acceso
                        al Sitio Web atribuye derecho alguno sobre los mismos.
                    </p>
                    <p>
                        Queda prohibida la reproducción, distribución, comunicación pública, transformación o
                        cualquier otra actividad que pueda realizarse con los contenidos del Sitio Web sin la
                        previa y expresa autorización de Impuestify.
                    </p>
                </section>

                <section>
                    <h2>5. Limitación de responsabilidad</h2>
                    <div className="alert alert-warning">
                        <strong>Impuestify es una herramienta de asistencia informativa.</strong>
                        <p>
                            Los contenidos, cálculos, simulaciones y borradores generados por el Sitio Web
                            son orientativos y no constituyen asesoramiento fiscal, jurídico, laboral ni
                            financiero profesional. El usuario es el único responsable de las decisiones
                            adoptadas sobre la base de la información proporcionada por los Servicios y
                            deberá, en todo caso, contrastar la información con un asesor fiscal o abogado
                            colegiado antes de presentar cualquier modelo, escrito o comunicación ante la
                            Administración Tributaria.
                        </p>
                    </div>

                    <p>
                        Impuestify no garantiza la disponibilidad ininterrumpida del Sitio Web ni la ausencia
                        de errores o fallos en su funcionamiento. Impuestify no será responsable, en ningún
                        caso, de los daños y perjuicios de cualquier naturaleza que puedan derivarse del
                        acceso o uso del Sitio Web o de sus contenidos por parte del usuario, incluyendo a
                        título enunciativo y no limitativo: errores u omisiones en los contenidos, falta de
                        disponibilidad temporal del Sitio Web, transmisión de virus o programas maliciosos
                        en los contenidos pese a haber adoptado todas las medidas tecnológicas necesarias
                        para evitarlo, y presentación extemporánea o incorrecta de declaraciones o modelos
                        tributarios por parte del usuario.
                    </p>
                    <p>
                        La responsabilidad máxima acumulada de Impuestify frente al usuario quedará limitada
                        al importe efectivamente abonado por este último por los Servicios en los doce (12)
                        meses anteriores al hecho que motive la reclamación.
                    </p>
                </section>

                <section>
                    <h2>6. Enlaces a sitios de terceros</h2>
                    <p>
                        El Sitio Web puede contener enlaces a sitios web de terceros, como las sedes
                        electrónicas de la Agencia Estatal de Administración Tributaria, el Boletín Oficial
                        del Estado y las Diputaciones Forales. Impuestify no controla dichos sitios ni se
                        hace responsable de sus contenidos, condiciones de uso o políticas de privacidad,
                        recomendándose al usuario la lectura de las mismas antes de su utilización.
                    </p>
                </section>

                <section>
                    <h2>7. Protección de datos personales</h2>
                    <p>
                        El tratamiento de los datos personales del usuario se rige por la{' '}
                        <Link to="/privacy-policy">Política de Privacidad</Link> y por la{' '}
                        <Link to="/cookie-policy">Política de Cookies</Link>, que forman parte integrante
                        del presente Aviso Legal.
                    </p>
                </section>

                <section>
                    <h2>8. Modificaciones</h2>
                    <p>
                        Impuestify se reserva el derecho a modificar, en cualquier momento y sin previo
                        aviso, la presentación y configuración del Sitio Web, así como el presente Aviso
                        Legal. Las modificaciones serán de aplicación desde su publicación en el Sitio Web.
                    </p>
                </section>

                <section>
                    <h2>9. Legislación aplicable y jurisdicción</h2>
                    <p>
                        El presente Aviso Legal se rige por la legislación española. Para cualquier
                        controversia que pudiera derivarse del acceso o uso del Sitio Web, las partes se
                        someten a los Juzgados y Tribunales del domicilio del consumidor, cuando este
                        tenga tal condición conforme a la normativa aplicable, o del domicilio del titular
                        del servicio en cualquier otro caso.
                    </p>
                </section>

                <section>
                    <h2>10. Contacto</h2>
                    <p>
                        Para cualquier consulta relacionada con el presente Aviso Legal, el usuario puede
                        dirigirse al correo electrónico{' '}
                        <a href="mailto:legal@impuestify.com">legal@impuestify.com</a>.
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Al acceder a este Sitio Web, el usuario declara haber leído y aceptado el presente
                        Aviso Legal, los <Link to="/terms-of-service">Términos y Condiciones de Servicio</Link>,
                        la <Link to="/privacy-policy">Política de Privacidad</Link> y la{' '}
                        <Link to="/cookie-policy">Política de Cookies</Link>.
                    </p>
                </div>
            </div>
        </div>
    );
}
