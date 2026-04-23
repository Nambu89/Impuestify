/**
 * AI Transparency Page
 * AI Act Art. 52 compliance
 */
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, Shield } from 'lucide-react';
import './LegalPage.css';

export default function AITransparencyPage() {
    return (
        <div className="legal-page">
            <div className="legal-container">
                <Link to="/" className="back-link">&larr; Volver al inicio</Link>

                <h1>Transparencia sobre el uso de IA</h1>
                <p className="subtitle">Reglamento (UE) 2024/1689 — AI Act, artículo 52</p>
                <p className="last-updated">Última actualización: 3 de enero de 2026</p>

                <div className="alert alert-info">
                    <strong><AlertTriangle size={16} className="inline-icon" /> Lo que debes saber</strong>
                    <p>
                        Impuestify responde a tus consultas mediante un sistema de IA. La IA se equivoca y NO reemplaza
                        al asesor fiscal.
                    </p>
                </div>

                <section>
                    <h2>1. Sistema de IA que usamos</h2>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Componente</th>
                                <th>Proveedor</th>
                                <th>Versión</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Modelo de lenguaje</td>
                                <td>OpenAI</td>
                                <td>Últimos modelos disponibles</td>
                            </tr>
                            <tr>
                                <td>Moderación</td>
                                <td>Meta (vía Groq)</td>
                                <td>Llama Guard 4</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section>
                    <h2>2. Clasificación según el AI Act</h2>
                    <div className="badge-large">Sistema de IA de RIESGO LIMITADO (Art. 52)</div>
                    <p>
                        Impuestify es un asistente conversacional. <strong>No toma decisiones automatizadas</strong>
                        que puedan afectar a derechos fundamentales.
                    </p>
                </section>

                <section>
                    <h2>3. Qué puede y qué no puede hacer</h2>
                    <div className="two-column">
                        <div>
                            <h3><CheckCircle size={16} className="inline-icon" /> Sí puede</h3>
                            <ul>
                                <li>Responder dudas fiscales</li>
                                <li>Calcular IRPF y cuotas orientativas</li>
                                <li>Leer PDFs de nóminas y notificaciones AEAT</li>
                                <li>Consultar fuentes oficiales</li>
                            </ul>
                        </div>
                        <div>
                            <h3><XCircle size={16} className="inline-icon" /> No puede</h3>
                            <ul>
                                <li>Presentar tus declaraciones</li>
                                <li>Garantizar exactitud del 100 %</li>
                                <li>Sustituir a tu asesor fiscal</li>
                                <li>Decidir por ti</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section>
                    <h2>4. Riesgos conocidos</h2>
                    <div className="alert alert-warning">
                        <strong><AlertTriangle size={16} className="inline-icon" /> Alucinaciones</strong>
                        <p>La IA puede soltar un dato que suena impecable y resulta falso.</p>
                        <p><strong>Cómo lo mitigamos</strong>: RAG con fuentes documentadas, citas y avisos visibles.</p>
                    </div>

                    <div className="alert alert-warning">
                        <strong><AlertTriangle size={16} className="inline-icon" /> Información caducada</strong>
                        <p>La normativa fiscal cambia sin avisar.</p>
                        <p><strong>Cómo lo mitigamos</strong>: búsqueda web en tiempo real y fecha visible en cada respuesta.</p>
                    </div>
                </section>

                <section>
                    <h2>5. Supervisión humana obligatoria</h2>
                    <p className="highlight">
                        <Shield size={16} className="inline-icon" /> <strong>Tú siempre debes</strong>:
                    </p>
                    <ul>
                        <li>Leer la respuesta antes de actuar</li>
                        <li>Abrir las fuentes que se citan</li>
                        <li>Contrastar con un asesor si la decisión es relevante</li>
                        <li>Recalcular las cifras antes de presentarlas</li>
                    </ul>
                </section>

                <section>
                    <h2>6. Reportar problemas</h2>
                    <p>Si la IA te da algo incorrecto o fuera de lugar, avísanos.</p>
                    <p>
                        <strong>Correo</strong>: <a href="mailto:report@impuestify.com">report@impuestify.com</a>
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Dudas sobre transparencia: escríbenos a <a href="mailto:report@impuestify.com">report@impuestify.com</a>.
                    </p>
                </div>
            </div>
        </div>
    );
}
