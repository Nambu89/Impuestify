/**
 * Legal Footer Component
 * 
 * GDPR-compliant footer with links to legal documentation
 * Best practices: Visible on all pages, accessible, clear links
 */
import { Link } from 'react-router-dom';
import './Footer.css';

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="footer">
            <div className="footer-container">
                {/* Main Content */}
                <div className="footer-content">
                    <div className="footer-section">
                        <h3>Impuestify</h3>
                        <p className="footer-tagline">
                            Tu asistente fiscal inteligente
                        </p>
                        <p className="footer-disclaimer">
                            🤖 Este servicio utiliza inteligencia artificial.
                            La información es orientativa, no sustituye asesoramiento profesional.
                        </p>
                    </div>

                    <div className="footer-section">
                        <h4>Legal</h4>
                        <ul className="footer-links">
                            <li>
                                <Link to="/privacy-policy">📋 Política de Privacidad</Link>
                            </li>
                            <li>
                                <Link to="/terms">📜 Términos y Condiciones</Link>
                            </li>
                            <li>
                                <Link to="/ai-transparency">🤖 Transparencia IA</Link>
                            </li>
                            <li>
                                <Link to="/data-retention">🗄️ Retención de Datos</Link>
                            </li>
                        </ul>
                    </div>

                    <div className="footer-section">
                        <h4>Soporte</h4>
                        <ul className="footer-links">
                            <li>
                                <a href="mailto:support@impuestify.com">✉️ Contacto</a>
                            </li>
                            <li>
                                <a href="mailto:privacy@impuestify.com">🔒 Privacidad</a>
                            </li>
                            <li>
                                <Link to="/security">🛡️ Seguridad</Link>
                            </li>
                        </ul>
                    </div>

                    <div className="footer-section">
                        <h4>Cumplimiento</h4>
                        <div className="footer-badges">
                            <span className="badge">✅ RGPD</span>
                            <span className="badge">✅ AI Act</span>
                            <span className="badge">✅ LOPDGDD</span>
                        </div>
                        <p className="footer-small">
                            Autoridad de control:
                            <a
                                href="https://www.aepd.es"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                AEPD
                            </a>
                        </p>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="footer-bottom">
                    <p>
                        © {currentYear} Impuestify. Todos los derechos reservados.
                    </p>
                    <p className="footer-small">
                        Hecho con ❤️ en España |
                        <a
                            href="https://github.com/Nambu89/TaxIA"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {' '}GitHub
                        </a>
                    </p>
                </div>
            </div>
        </footer>
    );
}
