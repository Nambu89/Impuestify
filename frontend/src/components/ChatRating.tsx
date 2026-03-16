import { useState, useEffect } from 'react'
import { ThumbsUp, ThumbsDown, Send, X } from 'lucide-react'
import { useFeedback } from '../hooks/useFeedback'
import './ChatRating.css'

interface ChatRatingProps {
    messageId: string
    conversationId?: string
}

const STORAGE_KEY_PREFIX = 'chat_rating_'

export default function ChatRating({ messageId, conversationId }: ChatRatingProps) {
    const { submitChatRating } = useFeedback()

    const storageKey = `${STORAGE_KEY_PREFIX}${messageId}`

    const [voted, setVoted] = useState<1 | -1 | null>(() => {
        const stored = localStorage.getItem(storageKey)
        if (stored === '1') return 1
        if (stored === '-1') return -1
        return null
    })
    const [showComment, setShowComment] = useState(false)
    const [comment, setComment] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [pendingRating, setPendingRating] = useState<1 | -1 | null>(null)

    // If already voted, show the result without comment box
    useEffect(() => {
        if (voted !== null) {
            setShowComment(false)
        }
    }, [voted])

    const handleVote = (rating: 1 | -1) => {
        if (voted !== null || submitting) return
        setPendingRating(rating)
        setShowComment(true)
    }

    const handleSubmit = async (skipComment = false) => {
        if (!pendingRating || submitting) return

        setSubmitting(true)
        try {
            await submitChatRating({
                message_id: messageId,
                conversation_id: conversationId,
                rating: pendingRating,
                ...(comment.trim() && !skipComment ? { comment: comment.trim() } : {}),
            })
            localStorage.setItem(storageKey, String(pendingRating))
            setVoted(pendingRating)
            setShowComment(false)
            setComment('')
        } catch {
            // Fail silently — rating is non-critical
            localStorage.setItem(storageKey, String(pendingRating))
            setVoted(pendingRating)
            setShowComment(false)
        } finally {
            setSubmitting(false)
            setPendingRating(null)
        }
    }

    const handleCancel = () => {
        setShowComment(false)
        setPendingRating(null)
        setComment('')
    }

    return (
        <div className="chat-rating">
            <div className="chat-rating__buttons">
                {voted === null ? (
                    <>
                        <button
                            className={`chat-rating__btn ${pendingRating === 1 ? 'active-up' : ''}`}
                            onClick={() => handleVote(1)}
                            disabled={submitting}
                            aria-label="Respuesta útil"
                            title="Respuesta útil"
                        >
                            <ThumbsUp size={14} />
                        </button>
                        <button
                            className={`chat-rating__btn ${pendingRating === -1 ? 'active-down' : ''}`}
                            onClick={() => handleVote(-1)}
                            disabled={submitting}
                            aria-label="Respuesta no útil"
                            title="Respuesta no útil"
                        >
                            <ThumbsDown size={14} />
                        </button>
                    </>
                ) : (
                    <span className={`chat-rating__result ${voted === 1 ? 'up' : 'down'}`}>
                        {voted === 1 ? <ThumbsUp size={13} /> : <ThumbsDown size={13} />}
                        {voted === 1 ? 'Útil' : 'No útil'}
                    </span>
                )}
            </div>

            {/* Optional comment after rating */}
            {showComment && (
                <div className="chat-rating__comment-box">
                    <div className="chat-rating__comment-header">
                        <span>
                            {pendingRating === 1
                                ? '¿Qué fue útil? (opcional)'
                                : '¿Qué falló? (opcional)'}
                        </span>
                        <button
                            className="chat-rating__comment-cancel"
                            onClick={handleCancel}
                            aria-label="Cancelar"
                        >
                            <X size={12} />
                        </button>
                    </div>
                    <div className="chat-rating__comment-input-row">
                        <input
                            type="text"
                            className="chat-rating__comment-input"
                            placeholder="Añade un comentario..."
                            value={comment}
                            onChange={e => setComment(e.target.value.slice(0, 300))}
                            onKeyDown={e => {
                                if (e.key === 'Enter') handleSubmit()
                                if (e.key === 'Escape') handleCancel()
                            }}
                            autoFocus
                            maxLength={300}
                        />
                        <button
                            className="chat-rating__send-btn"
                            onClick={() => handleSubmit()}
                            disabled={submitting}
                            aria-label="Enviar valoración"
                        >
                            <Send size={13} />
                        </button>
                        <button
                            className="chat-rating__skip-btn"
                            onClick={() => handleSubmit(true)}
                            disabled={submitting}
                        >
                            Omitir
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
