import { useState } from 'react';
import { X, Link2, Copy, Check, Share2, Eye, EyeOff, MessageSquare } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import '../styles/ShareModal.css';

interface ShareModalProps {
  conversationId: string;
  conversationTitle: string;
  onClose: () => void;
}

export default function ShareModal({ conversationId, conversationTitle, onClose }: ShareModalProps) {
  const [anonymize, setAnonymize] = useState(true);
  const [loading, setLoading] = useState(false);
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [messageCount, setMessageCount] = useState(0);
  const { apiRequest } = useApi();

  const generateLink = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiRequest(`/api/conversations/${conversationId}/share`, {
        method: 'POST',
        body: JSON.stringify({ anonymize }),
      });
      const fullUrl = `${window.location.origin}${data.share_url}`;
      setShareUrl(fullUrl);
      setMessageCount(data.message_count);
    } catch (err: any) {
      setError(err.message || 'Error al generar el enlace');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const input = document.createElement('input');
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareTwitter = () => {
    const text = `Mira mi consulta fiscal en Impuestify`;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  const shareWhatsApp = () => {
    const text = `Mira esta consulta fiscal: ${shareUrl}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  const shareLinkedIn = () => {
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, '_blank');
  };

  return (
    <div className="share-modal-overlay" onClick={onClose}>
      <div className="share-modal" onClick={e => e.stopPropagation()}>
        <div className="share-modal-header">
          <div className="share-modal-title">
            <Share2 size={20} />
            <h3>Compartir conversación</h3>
          </div>
          <button onClick={onClose} className="share-modal-close"><X size={20} /></button>
        </div>

        <div className="share-modal-body">
          <div className="share-modal-conv-name">
            <MessageSquare size={16} />
            <span>{conversationTitle || 'Conversación'}</span>
          </div>

          <div className="share-modal-option">
            <div className="share-modal-option-info">
              {anonymize ? <EyeOff size={18} /> : <Eye size={18} />}
              <div>
                <strong>Anonimizar datos personales</strong>
                <p>Oculta DNI, teléfonos, emails, importes y nombres</p>
              </div>
            </div>
            <label className="share-modal-toggle">
              <input type="checkbox" checked={anonymize} onChange={e => setAnonymize(e.target.checked)} />
              <span className="share-modal-toggle-slider" />
            </label>
          </div>

          {!shareUrl ? (
            <>
              {error && <p className="share-modal-error">{error}</p>}
              <button onClick={generateLink} disabled={loading} className="share-modal-generate">
                <Link2 size={18} />
                {loading ? 'Generando...' : 'Generar enlace público'}
              </button>
              <p className="share-modal-hint">
                Cualquier persona con el enlace podrá ver esta conversación.
                {anonymize ? ' Los datos personales serán ocultados.' : ' Los datos se compartirán tal cual.'}
              </p>
            </>
          ) : (
            <>
              <div className="share-modal-url-box">
                <input type="text" value={shareUrl} readOnly className="share-modal-url" />
                <button onClick={copyToClipboard} className="share-modal-copy">
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? 'Copiado' : 'Copiar'}
                </button>
              </div>

              <p className="share-modal-stats">
                {messageCount} mensajes {anonymize ? '(anonimizados)' : ''}
              </p>

              <div className="share-modal-social">
                <button onClick={shareWhatsApp} className="share-social-btn whatsapp">WhatsApp</button>
                <button onClick={shareTwitter} className="share-social-btn twitter">X / Twitter</button>
                <button onClick={shareLinkedIn} className="share-social-btn linkedin">LinkedIn</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
