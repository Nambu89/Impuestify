import { useState, useEffect, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import {
    Shield, RefreshCw, AlertCircle, CheckCircle, Loader, Play,
    ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus,
    BarChart2, FileQuestion, ListFilter
} from 'lucide-react'
import { useSubscription } from '../hooks/useSubscription'
import { useApi } from '../hooks/useApi'
import Header from '../components/Header'
import './AdminRagQualityPage.css'

// ─── Types ───────────────────────────────────────────────────────────────────

interface QuestionResult {
    question: string
    category: string
    faithfulness: number
    context_relevance: number
    answer_correctness: number
    response_quality: number
    response: string
    expected?: string
}

interface CategoryScore {
    category: string
    faithfulness: number
    context_relevance: number
    answer_correctness: number
    response_quality: number
    count: number
}

interface EvaluationResult {
    id: string
    evaluated_at: string
    total_questions: number
    avg_faithfulness: number
    avg_context_relevance: number
    avg_answer_correctness: number
    avg_response_quality: number
    questions: QuestionResult[]
    categories: CategoryScore[]
}

interface HistoryEntry {
    id: string
    evaluated_at: string
    avg_faithfulness: number
    avg_context_relevance: number
    avg_answer_correctness: number
    avg_response_quality: number
    total_questions: number
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function scoreClass(score: number): string {
    if (score >= 0.85) return 'score--good'
    if (score >= 0.70) return 'score--warning'
    return 'score--danger'
}

function scoreLabel(score: number): string {
    return (score * 100).toFixed(1) + '%'
}

function statusIcon(score: number): string {
    if (score > 0.8) return '✓'
    if (score > 0.6) return '⚠'
    return '✗'
}

function statusClass(score: number): string {
    if (score > 0.8) return 'rag-status--good'
    if (score > 0.6) return 'rag-status--warning'
    return 'rag-status--danger'
}

function worstScore(q: QuestionResult): number {
    return Math.min(q.faithfulness, q.context_relevance, q.answer_correctness, q.response_quality)
}

function DeltaBadge({ current, prev }: { current: number; prev?: number }) {
    if (prev === undefined) return null
    const delta = current - prev
    const abs = Math.abs(delta * 100).toFixed(1)
    if (Math.abs(delta) < 0.005) return <span className="rag-delta rag-delta--neutral"><Minus size={10} />{abs}%</span>
    if (delta > 0) return <span className="rag-delta rag-delta--up"><TrendingUp size={10} />+{abs}%</span>
    return <span className="rag-delta rag-delta--down"><TrendingDown size={10} />-{abs}%</span>
}

function formatDate(s: string) {
    try {
        return new Date(s).toLocaleString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch { return s }
}

function formatShortDate(s: string) {
    try {
        return new Date(s).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
    } catch { return s }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ScoreCard({
    label,
    score,
    prevScore,
    icon,
}: {
    label: string
    score: number
    prevScore?: number
    icon: React.ReactNode
}) {
    return (
        <div className={`rag-score-card ${scoreClass(score)}`}>
            <div className="rag-score-card__icon">{icon}</div>
            <div className="rag-score-card__content">
                <span className="rag-score-card__value">{scoreLabel(score)}</span>
                <span className="rag-score-card__label">{label}</span>
                <DeltaBadge current={score} prev={prevScore} />
            </div>
        </div>
    )
}

function ProgressBar({ value, className }: { value: number; className?: string }) {
    return (
        <div className="rag-bar">
            <div
                className={`rag-bar__fill ${className || scoreClass(value)}`}
                style={{ width: `${Math.round(value * 100)}%` }}
            />
            <span className="rag-bar__label">{scoreLabel(value)}</span>
        </div>
    )
}

function TrendRow({ entry }: { entry: HistoryEntry }) {
    return (
        <div className="rag-trend-row">
            <span className="rag-trend-row__date">{formatShortDate(entry.evaluated_at)}</span>
            <div className="rag-trend-row__bars">
                <div className="rag-trend-row__bar-item">
                    <span className="rag-trend-row__bar-label">Fidelidad</span>
                    <ProgressBar value={entry.avg_faithfulness} />
                </div>
                <div className="rag-trend-row__bar-item">
                    <span className="rag-trend-row__bar-label">Relevancia</span>
                    <ProgressBar value={entry.avg_context_relevance} />
                </div>
                <div className="rag-trend-row__bar-item">
                    <span className="rag-trend-row__bar-label">Corrección</span>
                    <ProgressBar value={entry.avg_answer_correctness} />
                </div>
                <div className="rag-trend-row__bar-item">
                    <span className="rag-trend-row__bar-label">Calidad</span>
                    <ProgressBar value={entry.avg_response_quality} />
                </div>
            </div>
            <span className="rag-trend-row__count">{entry.total_questions} pregs.</span>
        </div>
    )
}

function QuestionRow({ q }: { q: QuestionResult }) {
    const [expanded, setExpanded] = useState(false)
    const worst = worstScore(q)

    return (
        <>
            <tr
                className={`rag-table__row ${expanded ? 'rag-table__row--expanded' : ''}`}
                onClick={() => setExpanded(e => !e)}
            >
                <td className="rag-cell-question">{q.question}</td>
                <td><span className="rag-category-badge">{q.category}</span></td>
                <td><span className={scoreClass(q.faithfulness)}>{scoreLabel(q.faithfulness)}</span></td>
                <td><span className={scoreClass(q.answer_correctness)}>{scoreLabel(q.answer_correctness)}</span></td>
                <td>
                    <span className={`rag-status-icon ${statusClass(worst)}`}>
                        {statusIcon(worst)}
                    </span>
                </td>
                <td className="rag-cell-expand">
                    {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </td>
            </tr>
            {expanded && (
                <tr className="rag-table__detail-row">
                    <td colSpan={6}>
                        <div className="rag-detail-panel">
                            <div className="rag-detail-panel__scores">
                                <span>Fidelidad: <strong className={scoreClass(q.faithfulness)}>{scoreLabel(q.faithfulness)}</strong></span>
                                <span>Relevancia ctx.: <strong className={scoreClass(q.context_relevance)}>{scoreLabel(q.context_relevance)}</strong></span>
                                <span>Corrección: <strong className={scoreClass(q.answer_correctness)}>{scoreLabel(q.answer_correctness)}</strong></span>
                                <span>Calidad: <strong className={scoreClass(q.response_quality)}>{scoreLabel(q.response_quality)}</strong></span>
                            </div>
                            {q.expected && (
                                <div className="rag-detail-panel__block">
                                    <p className="rag-detail-panel__block-title">Respuesta esperada</p>
                                    <p className="rag-detail-panel__block-text">{q.expected}</p>
                                </div>
                            )}
                            <div className="rag-detail-panel__block">
                                <p className="rag-detail-panel__block-title">Respuesta del sistema</p>
                                <p className="rag-detail-panel__block-text">{q.response}</p>
                            </div>
                        </div>
                    </td>
                </tr>
            )}
        </>
    )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminRagQualityPage() {
    const { isOwner, loading: subLoading } = useSubscription()
    const { apiRequest } = useApi()

    const [latest, setLatest] = useState<EvaluationResult | null>(null)
    const [history, setHistory] = useState<HistoryEntry[]>([])
    const [loading, setLoading] = useState(true)
    const [evaluating, setEvaluating] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
    const [categoriesOpen, setCategoriesOpen] = useState(false)

    const fetchData = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [latestData, historyData] = await Promise.all([
                apiRequest<EvaluationResult | null>('/api/admin/rag-quality/results').catch(() => null),
                apiRequest<{ evaluations: HistoryEntry[]; count: number }>('/api/admin/rag-quality/history').catch(() => ({ evaluations: [], count: 0 })),
            ])
            setLatest(latestData)
            setHistory(historyData?.evaluations || [])
        } catch (err: any) {
            setError(err.message || 'Error al cargar resultados de calidad RAG')
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    useEffect(() => {
        if (isOwner) fetchData()
    }, [isOwner, fetchData])

    useEffect(() => {
        if (message) {
            const t = setTimeout(() => setMessage(null), 6000)
            return () => clearTimeout(t)
        }
    }, [message])

    const handleEvaluate = async () => {
        if (evaluating) return
        setEvaluating(true)
        setMessage(null)
        try {
            await apiRequest('/api/admin/rag-quality/evaluate', { method: 'POST', timeout: 600000 })
            setMessage({ type: 'success', text: 'Evaluación completada.' })
            await fetchData()
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al iniciar la evaluación' })
        } finally {
            setEvaluating(false)
        }
    }

    const prevEntry = history.length > 1 ? history[1] : undefined

    const sortedQuestions = latest
        ? [...latest.questions].sort((a, b) => worstScore(a) - worstScore(b))
        : []

    if (subLoading) return <div className="loading-screen">Cargando...</div>
    if (!isOwner) return <Navigate to="/chat" replace />

    return (
        <div className="admin-page arqp-page">
            <Header />

            <main className="admin-main arqp-main">
                <div className="admin-container arqp-container">

                    {/* Page header */}
                    <div className="admin-header">
                        <div className="admin-title-row">
                            <h1><Shield size={26} /> Admin — Calidad RAG</h1>
                            <button
                                className="btn-refresh"
                                onClick={fetchData}
                                disabled={loading}
                                title="Recargar datos"
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>
                        <p className="admin-subtitle">Métricas de calidad del sistema RAG (fidelidad, relevancia, corrección)</p>
                    </div>

                    {/* Action bar */}
                    <div className="arqp-action-bar">
                        <div className="arqp-action-bar__info">
                            {latest ? (
                                <>
                                    <span className="arqp-action-bar__last">
                                        Última evaluación: {formatDate(latest.evaluated_at)}
                                    </span>
                                    <span className="arqp-action-bar__count">
                                        <FileQuestion size={14} /> {latest.total_questions} preguntas evaluadas
                                    </span>
                                </>
                            ) : (
                                <span className="arqp-action-bar__last">Sin evaluaciones previas</span>
                            )}
                        </div>
                        <button
                            className="arqp-eval-btn"
                            onClick={handleEvaluate}
                            disabled={evaluating}
                        >
                            {evaluating
                                ? <><Loader size={16} className="animate-spin" /> Evaluando...</>
                                : <><Play size={16} /> Ejecutar evaluación</>
                            }
                        </button>
                    </div>

                    {evaluating && (
                        <div className="arqp-eval-progress">
                            <div className="arqp-eval-progress__bar" />
                            <p>Evaluación en curso — puede tardar 30-60 segundos...</p>
                        </div>
                    )}

                    {/* Messages */}
                    {error && (
                        <div className="admin-message error">
                            <AlertCircle size={18} /> {error}
                        </div>
                    )}
                    {message && (
                        <div className={`admin-message ${message.type}`}>
                            {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                            {message.text}
                        </div>
                    )}

                    {loading ? (
                        <div className="admin-loading">
                            <Loader size={28} className="animate-spin" />
                            <p>Cargando métricas de calidad...</p>
                        </div>
                    ) : !latest ? (
                        /* Empty state */
                        <div className="arqp-empty">
                            <BarChart2 size={48} />
                            <h3>Sin evaluaciones</h3>
                            <p>Aún no se han ejecutado evaluaciones de calidad RAG.</p>
                            <button
                                className="arqp-eval-btn"
                                onClick={handleEvaluate}
                                disabled={evaluating}
                            >
                                <Play size={16} /> Ejecutar primera evaluación
                            </button>
                        </div>
                    ) : (
                        <>
                            {/* Summary cards */}
                            <div className="arqp-cards-grid">
                                <ScoreCard
                                    label="Fidelidad"
                                    score={latest.avg_faithfulness}
                                    prevScore={prevEntry?.avg_faithfulness}
                                    icon={<TrendingUp size={20} />}
                                />
                                <ScoreCard
                                    label="Relevancia Contexto"
                                    score={latest.avg_context_relevance}
                                    prevScore={prevEntry?.avg_context_relevance}
                                    icon={<ListFilter size={20} />}
                                />
                                <ScoreCard
                                    label="Corrección Respuesta"
                                    score={latest.avg_answer_correctness}
                                    prevScore={prevEntry?.avg_answer_correctness}
                                    icon={<CheckCircle size={20} />}
                                />
                                <ScoreCard
                                    label="Calidad General"
                                    score={latest.avg_response_quality}
                                    prevScore={prevEntry?.avg_response_quality}
                                    icon={<BarChart2 size={20} />}
                                />
                            </div>

                            {/* Trend section */}
                            {history.length > 0 && (
                                <div className="arqp-section">
                                    <h2 className="arqp-section__title">
                                        <TrendingUp size={18} /> Tendencia — últimas {Math.min(history.length, 5)} evaluaciones
                                    </h2>
                                    <div className="arqp-trend">
                                        {history.slice(0, 5).map(entry => (
                                            <TrendRow key={entry.id} entry={entry} />
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Category breakdown */}
                            {latest.categories && latest.categories.length > 0 && (
                                <div className="arqp-section">
                                    <button
                                        className="arqp-collapsible"
                                        onClick={() => setCategoriesOpen(o => !o)}
                                        aria-expanded={categoriesOpen}
                                    >
                                        <span>
                                            <ListFilter size={18} /> Desglose por categoría
                                        </span>
                                        {categoriesOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                    </button>

                                    {categoriesOpen && (
                                        <div className="arqp-categories">
                                            {latest.categories.map(cat => {
                                                const avg = (cat.faithfulness + cat.context_relevance + cat.answer_correctness + cat.response_quality) / 4
                                                return (
                                                    <div key={cat.category} className="arqp-category-row">
                                                        <div className="arqp-category-row__header">
                                                            <span className="arqp-category-name">{cat.category}</span>
                                                            <span className="arqp-category-count">{cat.count} pregs.</span>
                                                            <span className={`arqp-category-avg ${scoreClass(avg)}`}>{scoreLabel(avg)}</span>
                                                        </div>
                                                        <div className="arqp-category-bars">
                                                            <div className="arqp-category-bar-item">
                                                                <span>Fidelidad</span>
                                                                <ProgressBar value={cat.faithfulness} />
                                                            </div>
                                                            <div className="arqp-category-bar-item">
                                                                <span>Relevancia</span>
                                                                <ProgressBar value={cat.context_relevance} />
                                                            </div>
                                                            <div className="arqp-category-bar-item">
                                                                <span>Corrección</span>
                                                                <ProgressBar value={cat.answer_correctness} />
                                                            </div>
                                                            <div className="arqp-category-bar-item">
                                                                <span>Calidad</span>
                                                                <ProgressBar value={cat.response_quality} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Question details table */}
                            {sortedQuestions.length > 0 && (
                                <div className="arqp-section">
                                    <h2 className="arqp-section__title">
                                        <FileQuestion size={18} /> Detalle por pregunta
                                        <span className="arqp-section__subtitle">ordenado por peor puntuación primero</span>
                                    </h2>

                                    {/* Desktop table */}
                                    <div className="arqp-table-wrapper">
                                        <table className="arqp-table">
                                            <thead>
                                                <tr>
                                                    <th>Pregunta</th>
                                                    <th>Categoría</th>
                                                    <th>Fidelidad</th>
                                                    <th>Corrección</th>
                                                    <th>Estado</th>
                                                    <th></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {sortedQuestions.map((q, i) => (
                                                    <QuestionRow key={i} q={q} />
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Mobile cards */}
                                    <div className="arqp-mobile-cards">
                                        {sortedQuestions.map((q, i) => {
                                            const worst = worstScore(q)
                                            return (
                                                <div key={i} className="arqp-mobile-card">
                                                    <div className="arqp-mobile-card__top">
                                                        <span className="rag-category-badge">{q.category}</span>
                                                        <span className={`rag-status-icon ${statusClass(worst)}`}>
                                                            {statusIcon(worst)}
                                                        </span>
                                                    </div>
                                                    <p className="arqp-mobile-card__question">{q.question}</p>
                                                    <div className="arqp-mobile-card__scores">
                                                        <span>Fidelidad: <strong className={scoreClass(q.faithfulness)}>{scoreLabel(q.faithfulness)}</strong></span>
                                                        <span>Corrección: <strong className={scoreClass(q.answer_correctness)}>{scoreLabel(q.answer_correctness)}</strong></span>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
