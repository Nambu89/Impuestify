import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, Calculator, Upload, ArrowRight, X } from 'lucide-react'
import './OnboardingModal.css'

const STORAGE_KEY = 'onboarding_seen'

interface OnboardingModalProps {
    userName?: string
}

export default function OnboardingModal({ userName }: OnboardingModalProps) {
    const [visible, setVisible] = useState(() => {
        return !localStorage.getItem(STORAGE_KEY)
    })
    const [step, setStep] = useState(0)

    if (!visible) return null

    const dismiss = () => {
        localStorage.setItem(STORAGE_KEY, 'true')
        setVisible(false)
    }

    const steps = [
        {
            icon: <MessageSquare size={40} />,
            title: `Bienvenido${userName ? `, ${userName}` : ''}`,
            desc: 'Impuestify es tu asistente fiscal con IA. Preguntale lo que quieras sobre impuestos, IRPF, deducciones, nominas o notificaciones de Hacienda.',
            tip: 'Prueba: "Cuanto pago de IRPF si gano 35.000 EUR en Madrid?"',
        },
        {
            icon: <Calculator size={40} />,
            title: 'Guia Fiscal interactiva',
            desc: 'Usa la Guia Fiscal para calcular tu IRPF paso a paso. Descubre deducciones autonomicas que quiza no conocias.',
            tip: 'Accede desde el menu: Guia Fiscal',
        },
        {
            icon: <Upload size={40} />,
            title: 'Sube tus documentos',
            desc: 'Puedes subir nominas, notificaciones de Hacienda o facturas. La IA los analiza y te da respuestas personalizadas.',
            tip: 'Ve a Workspaces para gestionar tus documentos',
        },
    ]

    const current = steps[step]
    const isLast = step === steps.length - 1

    return (
        <div className="onboarding-overlay" onClick={dismiss}>
            <div className="onboarding-modal" onClick={e => e.stopPropagation()}>
                <button className="onboarding-close" onClick={dismiss} aria-label="Cerrar">
                    <X size={20} />
                </button>

                <div className="onboarding-icon">{current.icon}</div>
                <h2 className="onboarding-title">{current.title}</h2>
                <p className="onboarding-desc">{current.desc}</p>
                <div className="onboarding-tip">{current.tip}</div>

                <div className="onboarding-dots">
                    {steps.map((_, i) => (
                        <span key={i} className={`onboarding-dot ${i === step ? 'onboarding-dot--active' : ''}`} />
                    ))}
                </div>

                <div className="onboarding-actions">
                    {isLast ? (
                        <Link to="/chat" className="btn btn-primary btn-lg onboarding-cta" onClick={dismiss}>
                            Empezar a usar Impuestify <ArrowRight size={18} />
                        </Link>
                    ) : (
                        <button className="btn btn-primary btn-lg onboarding-cta" onClick={() => setStep(s => s + 1)}>
                            Siguiente <ArrowRight size={18} />
                        </button>
                    )}
                    <button className="onboarding-skip" onClick={dismiss}>
                        Saltar tutorial
                    </button>
                </div>
            </div>
        </div>
    )
}

export function shouldShowOnboarding(): boolean {
    return !localStorage.getItem(STORAGE_KEY)
}
