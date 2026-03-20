import { TrendingDown, TrendingUp, Loader2, Calculator, AlertTriangle, CheckCircle2 } from 'lucide-react'
import CountUp from './reactbits/CountUp'
import type { IrpfEstimateResult } from '../hooks/useIrpfEstimator'
import './LiveEstimatorBar.css'

interface Props {
    result: IrpfEstimateResult | null
    loading: boolean
}

export default function LiveEstimatorBar({ result, loading }: Props) {
    const amount = result?.resultado_estimado ?? 0
    const isRefund = amount < 0
    const absAmount = Math.abs(amount)
    const tipoMedio = result?.tipo_medio_efectivo ?? 0

    // No result yet — show placeholder
    if (!result && !loading) {
        return (
            <div className="estimator-bar estimator-bar--empty">
                <Calculator size={20} />
                <span className="estimator-bar__hint">
                    Introduce tus datos para ver la estimación
                </span>
            </div>
        )
    }

    return (
        <div className={`estimator-bar ${isRefund ? 'estimator-bar--refund' : 'estimator-bar--payment'} ${loading ? 'estimator-bar--loading' : ''}`}>
            {loading ? (
                <div className="estimator-bar__loader">
                    <Loader2 size={20} className="spin" />
                    <span>Calculando...</span>
                </div>
            ) : (
                <>
                    <div className="estimator-bar__icon">
                        {isRefund ? <TrendingDown size={22} /> : <TrendingUp size={22} />}
                    </div>
                    <div className="estimator-bar__content">
                        <span className="estimator-bar__label">
                            {isRefund ? 'A devolver' : 'A pagar'}
                        </span>
                        <span className="estimator-bar__amount">
                            <CountUp to={absAmount} from={0} duration={0.8} separator="." />
                            <span className="estimator-bar__currency"> EUR</span>
                        </span>
                    </div>
                    <div className="estimator-bar__meta">
                        <span className="estimator-bar__rate">
                            Tipo medio: {tipoMedio.toFixed(1)}%
                        </span>
                    </div>
                    {result?.obligacion_declarar?.obligado === true && (
                        <div className="estimator-bar__obligacion estimator-bar__obligacion--obligado" title={result.obligacion_declarar.motivo}>
                            <AlertTriangle size={13} />
                            <span>Estás obligado a declarar</span>
                        </div>
                    )}
                    {result?.obligacion_declarar?.obligado === false && (
                        <div className="estimator-bar__obligacion estimator-bar__obligacion--libre" title={result.obligacion_declarar.motivo}>
                            <CheckCircle2 size={13} />
                            <span>No estás obligado a declarar</span>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
