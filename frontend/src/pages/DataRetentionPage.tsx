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

                <h1>Política de Retención de Datos</h1>
                <p className="subtitle">Responsable: Impuestify</p>
                <p className="last-updated">
                    Última actualización: 3 de enero de 2026 | Base legal: RGPD Art. 5.1.e
                </p>

                <section>
                    <h2>1. Principio de Limitación</h2>
                    <p>
                        Los datos personales se conservan <strong>únicamente durante el tiempo necesario</strong> para
                        los fines para los que fueron recogidos, en cumplimiento del RGPD Art. 5.1.e
                        (Limitación de conservación).
                    </p>
                </section>

                <section>
                    <h2>2. Plazos de Retención</h2>

                    <h3>2.1 Datos de Cuenta de Usuario</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo de Dato</th>
                                <th>Plazo</th>
                                <th>Eliminación</th>
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
                        <strong>Eliminación automática</strong>: Al eliminar cuenta, todos los datos
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
                                <td>Hasta eliminación por usuario</td>
                                <td>El usuario puede borrar</td>
                            </tr>
                            <tr>
                                <td>Metadata conversacion</td>
                                <td>Hasta eliminación</td>
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
                                <td>Eliminación automática</td>
                            </tr>
                            <tr>
                                <td>Notificaciones AEAT</td>
                                <td><strong>24 horas</strong></td>
                                <td>Eliminación automática</td>
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
                                <th>Eliminación</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Access logs</td>
                                <td>90 días</td>
                                <td>Automática</td>
                            </tr>
                            <tr>
                                <td>Error logs</td>
                                <td>90 días</td>
                                <td>Automática</td>
                            </tr>
                            <tr>
                                <td>Security events</td>
                                <td>90 días</td>
                                <td>Automática</td>
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
                                <td>Automática si usuario activo</td>
                            </tr>
                            <tr>
                                <td>Semantic cache</td>
                                <td>24 horas</td>
                                <td>No se renueva</td>
                            </tr>
                            <tr>
                                <td>Session tokens</td>
                                <td>30 min (access) / 7 días (refresh)</td>
                                <td>Automática</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section>
                    <h2>3. Excepciones Legales</h2>
                    <p>En ciertos casos, podemos conservar datos más allá de los plazos indicados:</p>
                    <ul>
                        <li>
                            <strong>Obligación Legal</strong>: Si existe obligación legal de conservar datos
                            (ej: requerimiento judicial). Base legal: RGPD Art. 6.1.c
                        </li>
                        <li>
                            <strong>Litigios</strong>: Si hay litigio pendiente, los datos relacionados
                            se conservan hasta resolución (RGPD Art. 17.3.e)
                        </li>
                        <li>
                            <strong>Datos Anonimizados</strong>: Los datos completamente anonimizados
                            pueden conservarse indefinidamente para estadisticas
                        </li>
                    </ul>
                </section>

                <section>
                    <h2>4. Proceso de Eliminación</h2>
                    <h3>4.1 Eliminación por Usuario (Derecho de Supresión)</h3>
                    <p>
                        <strong>Cómo ejercerlo</strong>: Desde Configuración &gt; Eliminar cuenta,
                        o enviando email a <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a>.
                    </p>
                    <p><strong>Plazo</strong>: Máximo 1 mes desde solicitud (RGPD Art. 12.3)</p>
                    <p><strong>Qué se elimina</strong>:</p>
                    <ul>
                        <li>Cuenta de usuario (email, contraseña hash)</li>
                        <li>Todas las conversaciones</li>
                        <li>Documentos subidos (si aún existen)</li>
                        <li>Preferencias de usuario</li>
                        <li>Logs asociados (se anonimizan)</li>
                    </ul>

                    <h3>4.2 Eliminación Automática</h3>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Tipo</th>
                                <th>Cuando</th>
                                <th>Método</th>
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
                                <td>90 días</td>
                                <td>Cron job semanal</td>
                            </tr>
                            <tr>
                                <td>Tokens expirados</td>
                                <td>7 días</td>
                                <td>Limpieza automática</td>
                            </tr>
                        </tbody>
                    </table>

                    <h3>4.3 Eliminación Segura</h3>
                    <p>
                        <strong>Método</strong>: Eliminación irreversible (DELETE sin backup).
                        No aplicamos soft delete ni archivado a largo plazo.
                    </p>
                </section>

                <section>
                    <h2>5. Backups y Restauracion</h2>
                    <p>
                        <strong>Frecuencia</strong>: Diaria (Turso automatico).
                        <strong> Retención</strong>: 30 días. Después: eliminación permanente.
                    </p>
                    <p>
                        Si un usuario solicita borrado, también se elimina de backups en el siguiente
                        ciclo (máximo 30 días). RGPD Art. 17.1 aplica a backups.
                    </p>
                </section>

                <section>
                    <h2>6. Notificaciones de Eliminación</h2>
                    <p>
                        Enviamos email de confirmacion cuando el usuario elimina su cuenta o conversaciones.
                        Si compartimos datos con terceros y el usuario solicita borrado, notificamos
                        a esos terceros (RGPD Art. 19).
                    </p>
                </section>

                <section>
                    <h2>7. Revisión y Actualización</h2>
                    <p>
                        Esta politica se revisa trimestralmente para asegurar plazos adecuados,
                        cumplir nueva normativa y ajustar según feedback de usuarios.
                    </p>
                    <p><strong>Proxima revision</strong>: Marzo 2026</p>
                </section>

                <section>
                    <h2>8. Derecho a Solicitar Información</h2>
                    <p>
                        Puede solicitar información sobre qué datos conservamos, cuándo serán eliminados
                        y el motivo de conservación.
                    </p>
                    <p><strong>Contacto</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a></p>
                </section>

                <section>
                    <h2>9. Contacto</h2>
                    <p>
                        <strong>Dudas sobre retención</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a><br />
                        <strong>Solicitar eliminación</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a><br />
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
