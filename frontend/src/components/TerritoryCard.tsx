import { Link } from 'react-router-dom'
import { Map, ArrowRight, CheckCircle } from 'lucide-react'
import './TerritoryCard.css'

interface TerritoryCardProps {
    name: string
    fullName: string
    hacienda: string
    deductionCount: number
    description: string
    slug: string
    isForal?: boolean
}

export default function TerritoryCard({
    name,
    fullName,
    hacienda,
    deductionCount,
    description,
    slug,
    isForal = false,
}: TerritoryCardProps) {
    return (
        <div className={`territory-card ${isForal ? 'territory-card--foral' : ''}`}>
            <div className="territory-card__header">
                <div className="territory-card__icon">
                    <Map size={24} />
                </div>
                <div className="territory-card__titles">
                    <h3 className="territory-card__name">{name}</h3>
                    <span className="territory-card__full-name">{fullName}</span>
                </div>
                {isForal && (
                    <span className="territory-card__badge">Foral</span>
                )}
            </div>

            <p className="territory-card__description">{description}</p>

            <div className="territory-card__meta">
                <div className="territory-card__hacienda">
                    <CheckCircle size={14} />
                    <span>{hacienda}</span>
                </div>
                <div className="territory-card__deductions">
                    <span className="territory-card__deduction-count">{deductionCount}</span>
                    <span className="territory-card__deduction-label">deducciones propias</span>
                </div>
            </div>

            <Link
                to={`/register?territory=${slug}`}
                className="territory-card__cta"
            >
                Calcula tu IRPF en {name}
                <ArrowRight size={16} />
            </Link>
        </div>
    )
}
