interface NotificationAnalysis {
    id: string
    summary: string
    type: string
    deadlines: Array<{
        description: string
        date: string
        days_remaining: number
        is_urgent: boolean
    }>
    region: {
        region: string
        is_foral: boolean
    }
    severity: 'low' | 'medium' | 'high'
    reference_links: Array<{
        title: string
        url: string
    }>
}

interface NotificationAnalysisDisplayProps {
    analysis: NotificationAnalysis
}

export function NotificationAnalysisDisplay({ analysis }: NotificationAnalysisDisplayProps) {
    const severityColors = {
        low: { bg: '#f0fff4', border: '#9ae6b4', icon: '✅' },
        medium: { bg: '#fffaf0', border: '#fbd38d', icon: '⚠️' },
        high: { bg: '#fff5f5', border: '#fc8181', icon: '🚨' }
    }

    const colors = severityColors[analysis.severity]

    // Format date
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        })
    }

    return (
        <div className="notification-analysis">
            <div className="analysis-header" style={{
                background: colors.bg,
                borderLeft: `4px solid ${colors.border}`
            }}>
                <span className="severity-icon">{colors.icon}</span>
                <div>
                    <h3>{analysis.type}</h3>
                    <p className="region-info">
                        📍 {analysis.region.region}
                        {analysis.region.is_foral && <span className="foral-badge">Foral</span>}
                    </p>
                </div>
            </div>

            <div className="analysis-body">
                <section className="summary-section">
                    <h4>📋 Resumen</h4>
                    <p>{analysis.summary}</p>
                </section>

                {analysis.deadlines && analysis.deadlines.length > 0 && (
                    <section className="deadlines-section">
                        <h4>⏰ Plazos Importantes</h4>
                        {analysis.deadlines.map((deadline, idx) => (
                            <div
                                key={idx}
                                className={`deadline-item ${deadline.is_urgent ? 'urgent' : ''}`}
                            >
                                <div className="deadline-info">
                                    <strong>{deadline.description}</strong>
                                    <span className="deadline-date">
                                        Hasta el {formatDate(deadline.date)}
                                    </span>
                                </div>
                                <div className="deadline-countdown">
                                    {deadline.days_remaining > 0 ? (
                                        <>
                                            <span className="days-number">{deadline.days_remaining}</span>
                                            <span className="days-label">días restantes</span>
                                        </>
                                    ) : (
                                        <span className="overdue">¡VENCIDO!</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </section>
                )}

                {analysis.reference_links && analysis.reference_links.length > 0 && (
                    <section className="references-section">
                        <h4>🔗 Enlaces útiles</h4>
                        <ul>
                            {analysis.reference_links.map((ref, idx) => (
                                <li key={idx}>
                                    <a href={ref.url} target="_blank" rel="noopener noreferrer">
                                        {ref.title} ↗
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}
            </div>

            <style>{`
                .notification-analysis {
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                    margin: 20px 0;
                }

                .analysis-header {
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }

                .severity-icon {
                    font-size: 32px;
                }

                .analysis-header h3 {
                    margin: 0 0 4px 0;
                    font-size: 18px;
                    color: #2d3748;
                }

                .region-info {
                    margin: 0;
                    color: #718096;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .foral-badge {
                    background: #4299e1;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                }

                .analysis-body {
                    padding: 20px;
                }

                section {
                    margin-bottom: 24px;
                }

                section:last-child {
                    margin-bottom: 0;
                }

                section h4 {
                    margin: 0 0 12px 0;
                    font-size: 16px;
                    color: #2d3748;
                }

                .summary-section p {
                    line-height: 1.6;
                    color: #4a5568;
                    margin: 0;
                }

                .deadline-item {
                    background: #f7fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .deadline-item.urgent {
                    background: #fff5f5;
                    border-color: #feb2b2;
                }

                .deadline-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .deadline-info strong {
                    color: #2d3748;
                    font-size: 15px;
                }

                .deadline-date {
                    color: #718096;
                    font-size: 14px;
                }

                .deadline-countdown {
                    text-align: right;
                }

                .days-number {
                    display: block;
                    font-size: 28px;
                    font-weight: 700;
                    color: #4299e1;
                    line-height: 1;
                }

                .deadline-item.urgent .days-number {
                    color: #f56565;
                }

                .days-label {
                    display: block;
                    font-size: 12px;
                    color: #718096;
                    margin-top: 4px;
                }

                .overdue {
                    color: #c53030;
                    font-weight: 700;
                    font-size: 16px;
                }

                .references-section ul {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }

                .references-section li {
                    margin-bottom: 8px;
                }

                .references-section a {
                    color: #4299e1;
                    text-decoration: none;
                    transition: color 0.2s;
                }

                .references-section a:hover {
                    color: #3182ce;
                    text-decoration: underline;
                }

                @media (max-width: 768px) {
                    .deadline-item {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 12px;
                    }

                    .deadline-countdown {
                        text-align: left;
                    }
                }
            `}</style>
        </div>
    )
}
