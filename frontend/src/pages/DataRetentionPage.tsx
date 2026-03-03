/**
 * Data Retention Policy Page
 * Full policy adapted from DATA_RETENTION.md
 */
import { Link } from 'react-router-dom';
import './LegalPage.css';

export default function DataRetentionPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">&larr; Volver al inicio</Link>

                <h1>Politica de Retencion de Datos</h1>
                <p className="subtitle">Responsable: Impuestify</p>
                <p className="last-updated">
                    Ultima actualizacion: 3 de enero de 2026 | Base legal: RGPD Art. 5.1.e
                </p>

                <section>
                    <h2>1. Principio de Limitacion</h2>
                    <p>
                        Los datos personales se conservan <strong>unicamente durante el tiempo necesario</strong> para
                        los fines para los que fueron recogidos, en cumplimiento del RGPD Art. 5.1.e
                        (Limitacion de conservacion).
                    </p>
                </section>

                <section>
                    <h2>2. Plazos de Retencion</h2>

                    <h3>2.1 Datos de Cuenta de Usuario</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo de Dato</th>
                                <th>Plazo</th>
                                <th>Eliminacion</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Email</td>
                                <td>Hasta baja voluntaria</td>
                                <td>Inmediata tras baja</td>
                            </tr>
                            <tr>
                                <td>Contrasena (hash)</td>
                                <td>Hasta baja voluntaria</td>
                                <td>Inmediata tras baja</td>
                            </tr>
                            <tr>
                                <td>Nombre</td>
                                <td>Hasta baja voluntaria</td>
                                <td>Inmediata tras baja</td>
                            </tr>
                        </tbody>
                    </table>
                    <p>
                        <strong>Eliminacion automatica</strong>: Al eliminar cuenta, todos los datos
                        asociados se eliminan en maximo 24 horas.
                    </p>

                    <h3>2.2 Conversaciones y Mensajes</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo de Dato</th>
                                <th>Plazo</th>
                                <th>Control Usuario</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Historial de chat</td>
                                <td>Hasta eliminacion por usuario</td>
                                <td>El usuario puede borrar</td>
                            </tr>
                            <tr>
                                <td>Metadata conversacion</td>
                                <td>Hasta eliminacion</td>
                                <td>Se borra con conversacion</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>2.3 Documentos PDF Subidos</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Plazo</th>
                                <th>Despues</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Nominas</td>
                                <td><strong>24 horas</strong></td>
                                <td>Eliminacion automatica</td>
                            </tr>
                            <tr>
                                <td>Notificaciones AEAT</td>
                                <td><strong>24 horas</strong></td>
                                <td>Eliminacion automatica</td>
                            </tr>
                        </tbody>
                    </table>
                    <p>
                        <strong>Proceso</strong>: El usuario sube el PDF, el sistema extrae el texto,
                        lo procesa con IA, y el PDF original se elimina tras 24h. El texto extraido
                        queda en la conversacion hasta que el usuario la borre.
                    </p>

                    <h3>2.4 Logs de Seguridad</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Plazo</th>
                                <th>Eliminacion</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Access logs</td>
                                <td>90 dias</td>
                                <td>Automatica</td>
                            </tr>
                            <tr>
                                <td>Error logs</td>
                                <td>90 dias</td>
                                <td>Automatica</td>
                            </tr>
                            <tr>
                                <td>Security events</td>
                                <td>90 dias</td>
                                <td>Automatica</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>2.5 Cache y Datos Temporales</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>TTL</th>
                                <th>Renovacion</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Redis conversation cache</td>
                                <td>1 hora</td>
                                <td>Automatica si usuario activo</td>
                            </tr>
                            <tr>
                                <td>Semantic cache</td>
                                <td>24 horas</td>
                                <td>No se renueva</td>
                            </tr>
                            <tr>
                                <td>Session tokens</td>
                                <td>30 min (access) / 7 dias (refresh)</td>
                                <td>Automatica</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section>
                    <h2>3. Excepciones Legales</h2>
                    <p>En ciertos casos, podemos conservar datos mas alla de los plazos indicados:</p>
                    <ul>
                        <li>
                            <strong>Obligacion Legal</strong>: Si existe obligacion legal de conservar datos
                            (ej: requerimiento judicial). Base legal: RGPD Art. 6.1.c
                        </li>
                        <li>
                            <strong>Litigios</strong>: Si hay litigio pendiente, los datos relacionados
                            se conservan hasta resolucion (RGPD Art. 17.3.e)
                        </li>
                        <li>
                            <strong>Datos Anonimizados</strong>: Los datos completamente anonimizados
                            pueden conservarse indefinidamente para estadisticas
                        </li>
                    </ul>
                </section>

                <section>
                    <h2>4. Proceso de Eliminacion</h2>
                    <h3>4.1 Eliminacion por Usuario (Derecho de Supresion)</h3>
                    <p>
                        <strong>Como ejercerlo</strong>: Desde Configuracion &gt; Eliminar cuenta,
                        o enviando email a <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a>.
                    </p>
                    <p><strong>Plazo</strong>: Maximo 1 mes desde solicitud (RGPD Art. 12.3)</p>
                    <p><strong>Que se elimina</strong>:</p>
                    <ul>
                        <li>Cuenta de usuario (email, contrasena hash)</li>
                        <li>Todas las conversaciones</li>
                        <li>Documentos subidos (si aun existen)</li>
                        <li>Preferencias de usuario</li>
                        <li>Logs asociados (se anonimizan)</li>
                    </ul>

                    <h3>4.2 Eliminacion Automatica</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Cuando</th>
                                <th>Metodo</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>PDFs</td>
                                <td>24h tras upload</td>
                                <td>Cron job diario</td>
                            </tr>
                            <tr>
                                <td>Cache</td>
                                <td>Al expirar TTL</td>
                                <td>Automatico</td>
                            </tr>
                            <tr>
                                <td>Logs</td>
                                <td>90 dias</td>
                                <td>Cron job semanal</td>
                            </tr>
                            <tr>
                                <td>Tokens expirados</td>
                                <td>7 dias</td>
                                <td>Limpieza automatica</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>4.3 Eliminacion Segura</h3>
                    <p>
                        <strong>Metodo</strong>: Eliminacion irreversible (DELETE sin backup).
                        No aplicamos soft delete ni archivado a largo plazo.
                    </p>
                </section>

                <section>
                    <h2>5. Backups y Restauracion</h2>
                    <p>
                        <strong>Frecuencia</strong>: Diaria (Turso automatico).
                        <strong> Retencion</strong>: 30 dias. Despues: eliminacion permanente.
                    </p>
                    <p>
                        Si un usuario solicita borrado, tambien se elimina de backups en el siguiente
                        ciclo (maximo 30 dias). RGPD Art. 17.1 aplica a backups.
                    </p>
                </section>

                <section>
                    <h2>6. Notificaciones de Eliminacion</h2>
                    <p>
                        Enviamos email de confirmacion cuando el usuario elimina su cuenta o conversaciones.
                        Si compartimos datos con terceros y el usuario solicita borrado, notificamos
                        a esos terceros (RGPD Art. 19).
                    </p>
                </section>

                <section>
                    <h2>7. Revision y Actualizacion</h2>
                    <p>
                        Esta politica se revisa trimestralmente para asegurar plazos adecuados,
                        cumplir nueva normativa y ajustar segun feedback de usuarios.
                    </p>
                    <p><strong>Proxima revision</strong>: Marzo 2026</p>
                </section>

                <section>
                    <h2>8. Derecho a Solicitar Informacion</h2>
                    <p>
                        Puede solicitar informacion sobre que datos conservamos, cuando seran eliminados
                        y el motivo de conservacion.
                    </p>
                    <p><strong>Contacto</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a></p>
                </section>

                <section>
                    <h2>9. Contacto</h2>
                    <p>
                        <strong>Dudas sobre retencion</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a><br />
                        <strong>Solicitar eliminacion</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a><br />
                        <strong>Reportar problema</strong>: <a href="mailto:support@impuestify.com">support@impuestify.com</a>
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Impuestify se compromete a conservar sus datos solo el tiempo estrictamente necesario.
                    </p>
                </div>
            </div>
        </div>
    );
}
