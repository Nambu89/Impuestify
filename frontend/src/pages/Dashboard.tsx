import { useState } from 'react'
import { MessageSquare, Clock, TrendingUp, FileText } from 'lucide-react'
import Header from '../components/Header'
import './Dashboard.css'

interface Stats {
    total_chunks: number
    total_documents: number
    cache_hits?: number
    avg_response_time?: number
}

export default function Dashboard() {
    const [stats] = useState<Stats>({
        total_chunks: 1250,
        total_documents: 45,
        cache_hits: 0,
        avg_response_time: 0.8
    })
    const [isLoading] = useState(false)

    return (
        <div className="dashboard">
            <Header />

            <main className="dashboard-main">
                <div className="container">
                    <div className="dashboard-header">
                        <h1>Dashboard</h1>
                        <p>Estadísticas del sistema TaxIA</p>
                    </div>

                    {isLoading ? (
                        <div className="dashboard-loading">
                            <p>Cargando estadísticas...</p>
                        </div>
                    ) : (
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-icon">
                                    <FileText size={24} />
                                </div>
                                <div className="stat-content">
                                    <h3>{stats?.total_documents || 0}</h3>
                                    <p>Documentos Indexados</p>
                                </div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon">
                                    <MessageSquare size={24} />
                                </div>
                                <div className="stat-content">
                                    <h3>{stats?.total_chunks || 0}</h3>
                                    <p>Fragmentos de Texto</p>
                                </div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon">
                                    <Clock size={24} />
                                </div>
                                <div className="stat-content">
                                    <h3>{stats?.avg_response_time?.toFixed(2) || '< 1'}s</h3>
                                    <p>Tiempo de Respuesta</p>
                                </div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon">
                                    <TrendingUp size={24} />
                                </div>
                                <div className="stat-content">
                                    <h3>{stats?.cache_hits || 0}</h3>
                                    <p>Respuestas en Caché</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
