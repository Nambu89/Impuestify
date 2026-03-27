import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { MessageSquare, Shield, Eye } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '../styles/SharedConversation.css';

interface SharedMessage {
  role: string;
  content: string;
  created_at?: string;
}

interface SharedData {
  title: string;
  messages: SharedMessage[];
  anonymized: boolean;
  created_at: string;
  view_count: number;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export default function SharedConversationPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<SharedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/api/shared/${token}`)
      .then(r => {
        if (!r.ok) throw new Error('Enlace no encontrado o expirado');
        return r.json();
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="shared-page">
        <div className="shared-loading">Cargando conversación...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="shared-page">
        <div className="shared-error">
          <h2>Enlace no disponible</h2>
          <p>{error || 'Esta conversación no existe o ha sido eliminada.'}</p>
          <a href="/" className="shared-cta-btn">Ir a Impuestify</a>
        </div>
      </div>
    );
  }

  return (
    <div className="shared-page">
      <div className="shared-container">
        {/* Header */}
        <div className="shared-header">
          <a href="/" className="shared-logo">
            <img src="/images/logo-header.webp" alt="Impuestify" height={32} />
          </a>
          <a href="/register" className="shared-cta-btn-sm">Prueba Impuestify</a>
        </div>

        {/* Title */}
        <div className="shared-title-bar">
          <MessageSquare size={20} />
          <h1>{data.title}</h1>
          {data.anonymized && (
            <span className="shared-badge">
              <Shield size={12} /> Datos anonimizados
            </span>
          )}
        </div>

        <div className="shared-meta">
          <span><Eye size={14} /> {data.view_count} visualizaciones</span>
          <span>Compartido desde Impuestify</span>
        </div>

        {/* Messages */}
        <div className="shared-messages">
          {data.messages.map((msg, i) => (
            <div key={i} className={`shared-msg shared-msg--${msg.role}`}>
              <div className="shared-msg-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="shared-msg-content">
                <div className="shared-msg-role">
                  {msg.role === 'user' ? 'Usuario' : 'Impuestify'}
                </div>
                <div className="shared-msg-text">
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="shared-cta">
          <h3>¿Tienes una consulta fiscal?</h3>
          <p>Impuestify es tu asistente fiscal con IA. Cubre los 21 territorios de España.</p>
          <a href="/register" className="shared-cta-btn">Empieza a usar Impuestify</a>
        </div>

        {/* Footer */}
        <div className="shared-footer">
          <p>Conversación compartida por un usuario de Impuestify. La información es orientativa.</p>
        </div>
      </div>
    </div>
  );
}
