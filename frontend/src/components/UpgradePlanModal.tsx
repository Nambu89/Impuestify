import { useNavigate } from 'react-router-dom'
import { X, ArrowUpCircle } from 'lucide-react'
import './UpgradePlanModal.css'

// SYNC: backend/app/services/subscription_service.py:PLAN_PRICES
const PLAN_PRICES: Record<string, string> = {
    particular: '5',
    creator: '49',
    autonomo: '39',
}

const PLAN_LABELS: Record<string, string> = {
    particular: 'Particular',
    creator: 'Creador',
    autonomo: 'Autónomo',
}

function getPlanDescription(requiredPlan: string): string {
    switch (requiredPlan) {
        case 'autonomo':
            return 'El perfil de autónomo incluye cálculo de modelos 303/130, seguimiento trimestral, workspace de documentos y todas las deducciones para actividades económicas.'
        case 'creator':
            return 'El plan Creador incluye fiscalidad de plataformas digitales (YouTube, TikTok, Twitch), IVA por plataforma, Modelo 349 y DAC7.'
        default:
            return 'Actualiza tu suscripción para acceder a esta funcionalidad.'
    }
}

export interface UpgradePlanModalProps {
    isOpen: boolean
    onClose: () => void
    requiredPlan: string
    currentPlan: string
    message?: string
}

export function UpgradePlanModal({
    isOpen,
    onClose,
    requiredPlan,
    currentPlan,
    message,
}: UpgradePlanModalProps) {
    const navigate = useNavigate()

    if (!isOpen) return null

    const requiredLabel = PLAN_LABELS[requiredPlan] ?? requiredPlan
    const currentLabel = PLAN_LABELS[currentPlan] ?? currentPlan
    const price = PLAN_PRICES[requiredPlan]

    const handleUpgrade = () => {
        navigate(`/subscribe?highlight=${requiredPlan}`)
        onClose()
    }

    return (
        <div className="upgrade-modal-overlay" onClick={onClose}>
            <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
                <div className="upgrade-modal-header">
                    <div className="upgrade-modal-icon">
                        <ArrowUpCircle size={28} />
                    </div>
                    <button className="upgrade-modal-close" onClick={onClose} aria-label="Cerrar">
                        <X size={20} />
                    </button>
                </div>

                <div className="upgrade-modal-body">
                    <h3 className="upgrade-modal-title">Necesitas actualizar tu plan</h3>

                    <p className="upgrade-modal-plan-info">
                        Tu plan actual <strong>{currentLabel}</strong> no incluye esta funcionalidad.
                        Se requiere el plan <strong>{requiredLabel}</strong>.
                    </p>

                    {message && (
                        <p className="upgrade-modal-message">{message}</p>
                    )}

                    <p className="upgrade-modal-description">
                        {getPlanDescription(requiredPlan)}
                    </p>

                    {price && (
                        <div className="upgrade-modal-price">
                            <span className="upgrade-modal-price-amount">{price} EUR</span>
                            <span className="upgrade-modal-price-period">/mes (IVA incluido)</span>
                        </div>
                    )}
                </div>

                <div className="upgrade-modal-footer">
                    <button
                        type="button"
                        className="upgrade-modal-btn-cancel"
                        onClick={onClose}
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        className="upgrade-modal-btn-primary"
                        onClick={handleUpgrade}
                    >
                        <ArrowUpCircle size={16} />
                        Ver planes
                    </button>
                </div>
            </div>
        </div>
    )
}
