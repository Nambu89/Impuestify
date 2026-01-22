/**
 * Legal Footer Component
 * 
 * GDPR-compliant footer with links to legal documentation
 * Best practices: Visible on all pages, accessible, clear links
 */
import { Link } from 'react-router-dom';
import { FileText, Scale, Bot, Database, Mail, Lock, Shield, CheckCircle } from 'lucide-react';
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
                            <Bot className="inline-icon" size={14} />
                            {' '}Este servicio utiliza inteligencia artificial.
                            La información es orientativa, no sustituye asesoramiento profesional.
                        </p>
                    </div>

                    <div className="footer-section">
                        <h4>Legal</h4>
                        <ul className="footer-links">
                            <li>
                                <Link to="/privacy-policy">
                                    <FileText size={16} className="link-icon" />
                                    Política de Privacidad
                                </Link>
                            </li>
                            <li>
                                <Link to="/terms">
                                    <Scale size={16} className="link-icon" />
                                    Términos y Condiciones
                                </Link>
                            </li>
                            <li>
                                <Link to="/ai-transparency">
                                    <Bot size={16} className="link-icon" />
                                    Transparencia IA
                                </Link>
                            </li>
                            <li>
                                <Link to="/data-retention">
                                    <Database size={16} className="link-icon" />
                                    Retención de Datos
                                </Link>
                            </li>
                        </ul>
                    </div>

                    <div className="footer-section">
                        <h4>Soporte</h4>
                        <ul className="footer-links">
                            <li>
                                <a href="mailto:support@impuestify.com">
                                    <Mail size={16} className="link-icon" />
                                    Contacto
                                </a>
                            </li>
                            <li>
                                <a href="mailto:privacy@impuestify.com">
                                    <Lock size={16} className="link-icon" />
                                    Privacidad
                                </a>
                            </li>
                            <li>
                                <Link to="/security">
                                    <Shield size={16} className="link-icon" />
                                    Seguridad
                                </Link>
                            </li>
                        </ul>
                    </div>

                    <div className="footer-section">
                        <h4>Cumplimiento</h4>
                        <div className="footer-badges">
                            <span className="badge">
                                <CheckCircle size={12} className="badge-icon" />
                                RGPD
                            </span>
                            <span className="badge">
                                <CheckCircle size={12} className="badge-icon" />
                                AI Act
                            </span>
                            <span className="badge">
                                <CheckCircle size={12} className="badge-icon" />
                                LOPDGDD
                            </span>
                        </div>
                        <p className="footer-small">
                            Autoridad de control:
                            <a
                                href="https://www.aepd.es"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                {' '}AEPD
                            </a>
                        </p>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="footer-bottom">
                    <p>
                        © {currentYear} Impuestify. Todos los derechos reservados.
                    </p>
                </div>
            </div>
        </footer>
    );
}
