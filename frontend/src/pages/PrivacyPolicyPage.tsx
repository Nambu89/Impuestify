/**
 * Privacy Policy Page
 * Displays PRIVACY_POLICY.md content
 */
import { Link } from 'react-router-dom';
import './LegalPage.css';

export default function PrivacyPolicyPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">← Volver al chat</Link>

                <h1>Política de Privacidad</h1>
                <p className="last-updated">Última actualización: 3 de enero de 2026</p>

                <section>
                    <h2>1. Información del Responsable</h2>
                    <p><strong>Impuestify</strong></p>
                    <p>Email: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a></p>
                </section>

                <section>
                    <h2>2. Datos que Recogemos</h2>
                    <ul>
                        <li>Email (autenticación)</li>
                        <li>Contraseña (hash seguro)</li>
                        <li>Conversaciones con el asistente IA</li>
                        <li>Documentos PDF (procesamiento temporal - 24h)</li>
                    </ul>
                </section>

                <section>
                    <h2>3. Finalidad del Tratamiento</h2>
                    <p>Procesamos sus datos para prestar el servicio de asistencia fiscal mediante IA.</p>
                    <p><strong>Base legal</strong>: Ejecución de contrato (RGPD Art. 6.1.b)</p>
                </section>

                <section>
                    <h2>4. Destinatarios de Datos</h2>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Proveedor</th>
                                <th>Servicio</th>
                                <th>Ubicación</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>OpenAI</td>
                                <td>Modelo IA (GPT-4o-mini)</td>
                                <td>🇺🇸 USA (SCC)</td>
                            </tr>
                            <tr>
                                <td>Turso</td>
                                <td>Base de datos</td>
                                <td>🇩🇪 Frankfurt (UE)</td>
                            </tr>
                            <tr>
                                <td>Upstash</td>
                                <td>Cache Redis</td>
                                <td>🇩🇪 Frankfurt (UE)</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section>
                    <h2>5. Sus Derechos (RGPD)</h2>
                    <ul>
                        <li>✅ Acceso a sus datos</li>
                        <li>✅ Rectificación de datos inexactos</li>
                        <li>✅ Supresión ("derecho al olvido")</li>
                        <li>✅ Portabilidad de datos</li>
                        <li>✅ Oposición al tratamiento</li>
                    </ul>
                    <p><strong>Ejercer derechos</strong>: <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a></p>
                </section>

                <section>
                    <h2>6. Conservación de Datos</h2>
                    <p>Ver nuestra <Link to="/data-retention">Política de Retención de Datos</Link></p>
                </section>

                <section>
                    <h2>7. Cookies y almacenamiento local</h2>
                    <p>
                        Para más información sobre las cookies y tecnologías de almacenamiento local que utilizamos,
                        consulte nuestra <Link to="/politica-cookies">Política de Cookies</Link>.
                    </p>
                </section>

                <section>
                    <h2>8. Seguridad</h2>
                    <p>Implementamos cifrado TLS, hashing seguro de contraseñas, rate limiting y auditoría.</p>
                    <p>Ver <Link to="/security">SECURITY.md</Link></p>
                </section>

                <section>
                    <h2>9. Autoridad de Control</h2>
                    <p>
                        Agencia Española de Protección de Datos (AEPD)<br />
                        Web: <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer">www.aepd.es</a>
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Para cualquier consulta sobre privacidad,
                        contacte con <a href="mailto:privacy@impuestify.com">privacy@impuestify.com</a>
                    </p>
                </div>
            </div>
        </div>
    );
}
