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

                <h1>Transparencia sobre el Uso de IA</h1>
                <p className="subtitle">Reglamento (UE) 2024/1689 - AI Act, Articulo 52</p>
                <p className="last-updated">Ultima actualizacion: 3 de enero de 2026</p>

                <div className="alert alert-info">
                    <strong><AlertTriangle size={16} className="inline-icon" /> Declaracion Importante</strong>
                    <p>
                        Impuestify utiliza un sistema de inteligencia artificial para responder
                        a sus consultas. La IA puede cometer errores. NO sustituye el asesoramiento
                        profesional.
                    </p>
                </div>

                <section>
                    <h2>1. Sistema de IA Utilizado</h2>
                    <table className="legal-table">
                        <thead>
                            <tr>
                                <th>Componente</th>
                                <th>Proveedor</th>
                                <th>Version</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Modelo de lenguaje</td>
                                <td>OpenAI</td>
                                <td>GPT-4o-mini / GPT-5-mini</td>
                            </tr>
                            <tr>
                                <td>Moderacion</td>
                                <td>Meta (via Groq)</td>
                                <td>Llama Guard 4</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section>
                    <h2>2. Clasificacion segun AI Act</h2>
                    <div className="badge-large">Sistema de IA de RIESGO LIMITADO (Art. 52)</div>
                    <p>
                        Impuestify es un asistente que interactua con usuarios, pero <strong>NO toma decisiones automatizadas</strong> que afecten derechos fundamentales.
                    </p>
                </section>

                <section>
                    <h2>3. Capacidades y Limitaciones</h2>
                    <div className="two-column">
                        <div>
                            <h3><CheckCircle size={16} className="inline-icon" /> Qué puede hacer</h3>
                            <ul>
                                <li>Responder preguntas sobre fiscalidad</li>
                                <li>Calcular IRPF y cuotas</li>
                                <li>Analizar PDFs de nóminas/AEAT</li>
                                <li>Buscar información oficial</li>
                            </ul>
                        </div>
                        <div>
                            <h3><XCircle size={16} className="inline-icon" /> Qué NO puede hacer</h3>
                            <ul>
                                <li>NO presenta declaraciones</li>
                                <li>NO garantiza exactitud 100%</li>
                                <li>NO sustituye asesor fiscal</li>
                                <li>NO toma decisiones por usted</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section>
                    <h2>4. Riesgos Conocidos</h2>
                    <div className="alert alert-warning">
                        <strong><AlertTriangle size={16} className="inline-icon" /> Alucinaciones de IA</strong>
                        <p>La IA puede generar información que parece correcta pero es errónea.</p>
                        <p><strong>Mitigación</strong>: RAG (fuentes documentadas) + citación de fuentes + disclaimers</p>
                    </div>

                    <div className="alert alert-warning">
                        <strong><AlertTriangle size={16} className="inline-icon" /> Información Desactualizada</strong>
                        <p>Normativa fiscal cambia frecuentemente.</p>
                        <p><strong>Mitigación</strong>: Búsqueda web en tiempo real + fecha en respuestas</p>
                    </div>
                </section>

                <section>
                    <h2>5. Supervisión Humana Requerida</h2>
                    <p className="highlight">
                        <Shield size={16} className="inline-icon" /> <strong>Usted SIEMPRE debe</strong>:
                    </p>
                    <ul>
                        <li>Revisar las respuestas de la IA</li>
                        <li>Verificar fuentes citadas</li>
                        <li>Consultar con asesor fiscal para decisiones importantes</li>
                        <li>Validar calculos antes de usarlos</li>
                    </ul>
                </section>

                <section>
                    <h2>6. Reportar Problemas</h2>
                    <p>Si la IA genera contenido incorrecto o inapropiado:</p>
                    <p>
                        <strong>Email</strong>: <a href="mailto:report@impuestify.com">report@impuestify.com</a>
                    </p>
                </section>

                <div className="legal-cta">
                    <p>
                        Para cualquier consulta sobre transparencia IA,
                        contacte con <a href="mailto:report@impuestify.com">report@impuestify.com</a>
                    </p>
                </div>
            </div>
        </div>
    );
}
