import { useState, useMemo } from 'react'
import {
    Monitor,
    ShoppingBag,
    Heart,
    Video,
    Coffee,
    Truck,
    AlertTriangle,
    CheckCircle2,
    Info,
    ChevronRight,
    Euro,
    TrendingUp,
} from 'lucide-react'
import Header from '../components/Header'
import './GastosDeduciblesPage.css'

// ============================================================
// Tipos
// ============================================================

interface GastoDeducible {
    nombre: string
    porcentaje: number | null // null = 0% (no deducible en IRPF)
    limite: string
    consejo: string
    conflictivo?: boolean
    porcentajeTexto?: string // para mostrar texto personalizado si porcentaje es null o especial
}

type PerfilId = 'consultor' | 'comercio' | 'sanitario' | 'creador' | 'hosteleria' | 'transporte'

interface Perfil {
    id: PerfilId
    nombre: string
    descripcion: string
    icon: React.ComponentType<{ size?: number; className?: string }>
    gastos: GastoDeducible[]
}

// ============================================================
// Datos fiscales por perfil
// ============================================================

const GASTOS_POR_PERFIL: Record<PerfilId, GastoDeducible[]> = {
    consultor: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible. Base mínima 2025: 230,15 EUR/mes',
        },
        {
            nombre: 'Software y herramientas SaaS',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Adobe CC, hosting, GitHub, Notion, licencias. Con factura.',
        },
        {
            nombre: 'Equipos informáticos',
            porcentaje: 100,
            limite: 'Amortizable si > 300 EUR (26% anual)',
            consejo: 'PC, monitor, teclado, ratón, disco externo. Guarda facturas.',
        },
        {
            nombre: 'Formación profesional',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Cursos, másters, certificaciones, libros técnicos relacionados con tu actividad.',
        },
        {
            nombre: 'Coworking / oficina',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Alquiler de espacio de trabajo. Siempre con factura a tu nombre.',
        },
        {
            nombre: 'Suministros del hogar (oficina en casa)',
            porcentaje: 30,
            limite: 'Proporcional a m² afectos',
            consejo: 'Fórmula: (m² usados / m² totales) × 30% × factura. Declara m² en modelo 036.',
        },
        {
            nombre: 'Internet y teléfono',
            porcentaje: 50,
            limite: 'Línea a tu nombre',
            consejo: 'Si no tienes línea separada, Hacienda puede denegar el 100%. Recomendable: línea exclusiva.',
        },
        {
            nombre: 'Seguro de salud',
            porcentaje: 100,
            limite: '500 EUR/persona/año (1.500 EUR si discapacidad)',
            consejo: 'Incluye cónyuge e hijos menores de 25 años que convivan contigo.',
        },
        {
            nombre: 'Comidas de trabajo',
            porcentaje: 100,
            limite: '26,67 EUR/día en España — 48,08 EUR en el extranjero',
            consejo: 'Solo en desplazamiento. Pago electrónico obligatorio. No valen comidas "de oficina".',
            conflictivo: true,
        },
        {
            nombre: 'Publicidad y marketing',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Web, SEM, redes sociales, diseño gráfico, branding.',
        },
        {
            nombre: 'Asesoría y gestoría',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Contable, fiscal, laboral. Con factura.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada. Incompatible con reducción TRADE.',
        },
        {
            nombre: 'Vehículo (IRPF)',
            porcentaje: null,
            porcentajeTexto: '0% IRPF / 50% IVA',
            limite: 'No deducible en IRPF',
            consejo: 'Hacienda deniega el vehículo en IRPF salvo actividades tasadas. El IVA sí puede deducirse al 50%.',
            conflictivo: true,
        },
    ],
    comercio: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible. Base mínima 2025: 230,15 EUR/mes',
        },
        {
            nombre: 'Existencias y mercancías',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Coste de adquisición de productos para venta. Requiere control de inventario.',
        },
        {
            nombre: 'Alquiler del local',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Uso exclusivo profesional. Con contrato de arrendamiento.',
        },
        {
            nombre: 'Suministros del local (luz, agua, gas)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Facturas a nombre del negocio o con dirección del local.',
        },
        {
            nombre: 'Packaging y embalaje',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Cajas, bolsas, papel burbuja, cintas, etiquetas.',
        },
        {
            nombre: 'Vehículo de reparto propio',
            porcentaje: 100,
            limite: 'Uso exclusivo para reparto',
            consejo: 'Si realizas reparto propio con vehículo afecto exclusivamente al negocio, deducible al 100%.',
        },
        {
            nombre: 'Publicidad y marketing',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Tienda online, SEM, redes sociales, catálogos, señalética.',
        },
        {
            nombre: 'Seguro de salud',
            porcentaje: 100,
            limite: '500 EUR/persona/año',
            consejo: 'Incluye cónyuge e hijos menores de 25 años que convivan contigo.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada.',
        },
        {
            nombre: 'Amortización de mobiliario',
            porcentaje: 100,
            limite: '10% anual (coeficiente lineal)',
            consejo: 'Estanterías, mostradores, cajas registradoras. Amortización anual.',
        },
        {
            nombre: 'Asesoría y gestoría',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Gestión contable, fiscal y laboral.',
        },
    ],
    sanitario: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible.',
        },
        {
            nombre: 'Material clínico y fungible',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Guantes, mascarillas, jeringas, gasas, material de consulta.',
        },
        {
            nombre: 'Alquiler de consulta',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Arrendamiento de local clínico. Con contrato.',
        },
        {
            nombre: 'Equipamiento médico',
            porcentaje: 100,
            limite: 'Amortizable según tabla',
            consejo: 'Camillas, aparatos diagnóstico, esterilizadores. Amortización anual.',
        },
        {
            nombre: 'Seguro de responsabilidad civil profesional',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Obligatorio para profesionales sanitarios. Totalmente deducible.',
        },
        {
            nombre: 'Colegio profesional',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Cuota del colegio de médicos, enfermería, fisioterapia, etc.',
        },
        {
            nombre: 'Formación y congresos sanitarios',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Cursos de especialización, congresos médicos, suscripciones a revistas científicas.',
        },
        {
            nombre: 'Software de gestión clínica',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Historia clínica digital, gestión de citas, facturación sanitaria.',
        },
        {
            nombre: 'Seguro de salud (personal)',
            porcentaje: 100,
            limite: '500 EUR/persona/año',
            consejo: 'Incluye cónyuge e hijos menores de 25 años que convivan contigo.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada.',
        },
        {
            nombre: 'Nota: IVA exento (Art. 20 LIVA)',
            porcentaje: null,
            porcentajeTexto: 'Atención',
            limite: 'Sin derecho a deducir IVA soportado',
            consejo: 'Las actividades sanitarias están exentas de IVA. No repercutes IVA pero tampoco puedes deducir el IVA de tus compras.',
            conflictivo: true,
        },
    ],
    creador: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible.',
        },
        {
            nombre: 'Equipo de grabación (cámara, micrófono)',
            porcentaje: 100,
            limite: 'Amortizable si > 300 EUR (26% anual)',
            consejo: 'Cámara, objetivo, micrófono, trípode, estabilizador. Guardar facturas.',
        },
        {
            nombre: 'Iluminación y decorado',
            porcentaje: 100,
            limite: 'Amortizable si > 300 EUR',
            consejo: 'Focos, difusores, pantallas, fondos. Uso exclusivo o mayoritariamente profesional.',
        },
        {
            nombre: 'Software de edición',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Adobe Premiere, Final Cut, DaVinci Resolve, Photoshop, plugins.',
        },
        {
            nombre: 'Ordenador y periféricos',
            porcentaje: 100,
            limite: 'Amortizable si > 300 EUR',
            consejo: 'PC de edición, monitor, disco duro externo, tarjetas de memoria.',
        },
        {
            nombre: 'Plataformas y suscripciones',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Herramientas de SEO, scheduling, analytics, música libre de derechos.',
        },
        {
            nombre: 'Viajes y desplazamientos para contenido',
            porcentaje: 100,
            limite: '26,67 EUR/día dietas — transporte con factura',
            consejo: 'Solo si el viaje está directamente vinculado a la creación de contenido. Documentar con vídeos/posts.',
            conflictivo: true,
        },
        {
            nombre: 'Formación (marketing, edición, SEO)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Cursos de YouTube, TikTok, edición de vídeo, fotografía relacionados con tu actividad.',
        },
        {
            nombre: 'Publicidad y promoción',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Anuncios pagados, colaboraciones, diseño de miniaturas, branding.',
        },
        {
            nombre: 'Seguro de salud',
            porcentaje: 100,
            limite: '500 EUR/persona/año',
            consejo: 'Incluye cónyuge e hijos menores de 25 años.',
        },
        {
            nombre: 'Internet y teléfono',
            porcentaje: 50,
            limite: 'Línea a tu nombre',
            consejo: 'Recomendable tener línea separada. Sin línea propia, Hacienda puede denegar el 100%.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada.',
        },
        {
            nombre: 'Vehículo (IRPF)',
            porcentaje: null,
            porcentajeTexto: '0% IRPF / 50% IVA',
            limite: 'No deducible en IRPF salvo excepciones',
            consejo: 'Solo deducible si puedes demostrar uso exclusivo profesional o actividad de transporte.',
            conflictivo: true,
        },
    ],
    hosteleria: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible.',
        },
        {
            nombre: 'Materias primas y alimentos',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Coste de alimentos y bebidas para elaborar o vender. Con albaranes y facturas.',
        },
        {
            nombre: 'Alquiler del local',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Arrendamiento del local de hostelería. Con contrato.',
        },
        {
            nombre: 'Suministros (luz, agua, gas, internet)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Facturas del local. Si hay parte de vivienda, proporcional a m².',
        },
        {
            nombre: 'Personal (nóminas y SS)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Sueldos, cotizaciones sociales y mutuas de los empleados.',
        },
        {
            nombre: 'Uniformes y ropa de trabajo',
            porcentaje: 100,
            limite: 'Solo ropa con logo o EPI',
            consejo: 'Uniformes con logo del establecimiento, EPIs. La ropa de calle NO es deducible aunque la uses en el trabajo.',
        },
        {
            nombre: 'Licencias y tasas municipales',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Licencia de apertura, tasa de terrazas, canon de música (SGAE).',
        },
        {
            nombre: 'Amortización de maquinaria',
            porcentaje: 100,
            limite: '12% anual (cocina industrial)',
            consejo: 'Hornos, freidoras, cámaras frigoríficas, cafetera industrial.',
        },
        {
            nombre: 'Mantenimiento y reparaciones',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Reparaciones del local y maquinaria. Con factura del técnico.',
        },
        {
            nombre: 'Publicidad y marketing',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Web, TripAdvisor, Google Ads, cartas y menús.',
        },
        {
            nombre: 'Seguro de salud',
            porcentaje: 100,
            limite: '500 EUR/persona/año',
            consejo: 'Incluye cónyuge e hijos menores de 25 años.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada.',
        },
    ],
    transporte: [
        {
            nombre: 'Cuota de autónomo (RETA)',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Siempre deducible.',
        },
        {
            nombre: 'Vehículo (compra o leasing)',
            porcentaje: 100,
            limite: 'Uso exclusivo para la actividad',
            consejo: 'Transportistas, repartidores, taxistas y VTC tienen deducción del 100% en IRPF e IVA. Es la única actividad con esta ventaja.',
        },
        {
            nombre: 'Combustible',
            porcentaje: 100,
            limite: 'Proporcional al uso profesional',
            consejo: 'Gasolina, gasóleo, electricidad para el vehículo de trabajo. Con ticket de gasolinera.',
        },
        {
            nombre: 'Seguro del vehículo',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Póliza de seguro del vehículo afecto a la actividad.',
        },
        {
            nombre: 'Mantenimiento y revisiones',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'ITV, cambios de aceite, neumáticos, reparaciones.',
        },
        {
            nombre: 'Peajes y aparcamiento',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Recibos de autopistas, tickets de parking. Con justificante.',
        },
        {
            nombre: 'Amortización del vehículo',
            porcentaje: 100,
            limite: '16% anual (camiones) / 20% anual (turismos empresa)',
            consejo: 'Si el vehículo supera 300 EUR se amortiza. Coeficiente según tabla simplificada.',
        },
        {
            nombre: 'Licencia de transporte',
            porcentaje: 100,
            limite: 'Sin límite',
            consejo: 'Licencia VTC, tarjeta de taxi, autorización de transporte de mercancías.',
        },
        {
            nombre: 'Dietas y manutención',
            porcentaje: 100,
            limite: '26,67 EUR/día en España — 48,08 EUR en el extranjero con pernocta',
            consejo: 'En desplazamiento. Pago electrónico y factura.',
        },
        {
            nombre: 'Seguro de salud',
            porcentaje: 100,
            limite: '500 EUR/persona/año',
            consejo: 'Incluye cónyuge e hijos menores de 25 años.',
        },
        {
            nombre: 'Gastos de difícil justificación',
            porcentaje: 5,
            limite: 'Máximo 2.000 EUR/año',
            consejo: 'Automático en estimación directa simplificada.',
        },
    ],
}

const PERFILES: Perfil[] = [
    {
        id: 'consultor',
        nombre: 'Consultor / IT / Servicios profesionales',
        descripcion: 'Freelance, programador, diseñador, abogado, arquitecto',
        icon: Monitor,
        gastos: GASTOS_POR_PERFIL['consultor'],
    },
    {
        id: 'comercio',
        nombre: 'Comercio / Tienda',
        descripcion: 'Tienda física, comercio online, retail',
        icon: ShoppingBag,
        gastos: GASTOS_POR_PERFIL['comercio'],
    },
    {
        id: 'sanitario',
        nombre: 'Sanitario / Terapeuta',
        descripcion: 'Médico, fisioterapeuta, psicólogo, enfermero',
        icon: Heart,
        gastos: GASTOS_POR_PERFIL['sanitario'],
    },
    {
        id: 'creador',
        nombre: 'Creador de contenido',
        descripcion: 'YouTuber, influencer, streamer, blogger, podcaster',
        icon: Video,
        gastos: GASTOS_POR_PERFIL['creador'],
    },
    {
        id: 'hosteleria',
        nombre: 'Hostelería / Restauración',
        descripcion: 'Bar, restaurante, cafetería, catering',
        icon: Coffee,
        gastos: GASTOS_POR_PERFIL['hosteleria'],
    },
    {
        id: 'transporte',
        nombre: 'Transporte / Repartidor',
        descripcion: 'Taxista, VTC, repartidor, transportista',
        icon: Truck,
        gastos: GASTOS_POR_PERFIL['transporte'],
    },
]

// ============================================================
// Helpers
// ============================================================

function getPorcentajeClass(porcentaje: number | null): string {
    if (porcentaje === null) return 'gd-pct--red'
    if (porcentaje === 100) return 'gd-pct--green'
    if (porcentaje >= 50) return 'gd-pct--yellow'
    return 'gd-pct--orange'
}

function getPorcentajeLabel(gasto: GastoDeducible): string {
    if (gasto.porcentajeTexto) return gasto.porcentajeTexto
    if (gasto.porcentaje === null) return '0%'
    if (gasto.porcentaje === 5) return '5% (GDJ)'
    return `${gasto.porcentaje}%`
}

function formatEur(value: number): string {
    return value.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

// ============================================================
// Componente principal
// ============================================================

export default function GastosDeduciblesPage() {
    const [perfilSeleccionado, setPerfilSeleccionado] = useState<PerfilId | null>(null)
    const [gastosInput, setGastosInput] = useState<string>('')

    const perfil = useMemo(
        () => PERFILES.find(p => p.id === perfilSeleccionado) ?? null,
        [perfilSeleccionado]
    )

    const gastosAnuales = parseFloat(gastosInput.replace(',', '.')) || 0
    const ahorroEstimado = Math.round(gastosAnuales * 12 * 0.25)

    const handlePerfilClick = (id: PerfilId) => {
        setPerfilSeleccionado(prev => (prev === id ? null : id))
        setGastosInput('')
    }

    return (
        <div className="gd-page">
            <Header />

            <main className="gd-main">

                {/* ---- Hero ---- */}
                <div className="gd-hero">
                    <h1 className="gd-title">
                        <span className="gd-title-highlight">¿Qué gastos puedes deducir</span>
                        {' '}como autónomo?
                    </h1>
                    <p className="gd-subtitle">
                        Descubre los gastos deducibles de tu actividad — con límites exactos y consejos para evitar inspecciones
                    </p>
                </div>

                {/* ---- Paso 1: Selecciona tu actividad ---- */}
                <section className="gd-section">
                    <div className="gd-step-header">
                        <span className="gd-step-badge">Paso 1</span>
                        <h2 className="gd-step-title">Selecciona tu actividad</h2>
                    </div>

                    <div className="gd-perfiles-grid">
                        {PERFILES.map(p => {
                            const Icon = p.icon
                            const activo = perfilSeleccionado === p.id
                            return (
                                <button
                                    key={p.id}
                                    className={`gd-perfil-card ${activo ? 'gd-perfil-card--activo' : ''}`}
                                    onClick={() => handlePerfilClick(p.id)}
                                    aria-pressed={activo}
                                >
                                    <div className="gd-perfil-icon-wrap">
                                        <Icon size={28} className="gd-perfil-icon" />
                                    </div>
                                    <span className="gd-perfil-nombre">{p.nombre}</span>
                                    <span className="gd-perfil-desc">{p.descripcion}</span>
                                    {activo && (
                                        <span className="gd-perfil-check">
                                            <CheckCircle2 size={16} />
                                        </span>
                                    )}
                                </button>
                            )
                        })}
                    </div>
                </section>

                {/* ---- Paso 2: Checklist personalizada ---- */}
                {perfil && (
                    <section className="gd-section gd-section--animate" key={perfil.id}>
                        <div className="gd-step-header">
                            <span className="gd-step-badge">Paso 2</span>
                            <h2 className="gd-step-title">
                                Gastos deducibles para: <span className="gd-step-perfil">{perfil.nombre}</span>
                            </h2>
                        </div>

                        {/* Tabla de gastos */}
                        <div className="gd-tabla-wrap">
                            <div className="gd-tabla-header">
                                <span className="gd-col-gasto">Gasto</span>
                                <span className="gd-col-pct">% Deducible</span>
                                <span className="gd-col-limite">Límite / Condición</span>
                                <span className="gd-col-consejo">Consejo clave</span>
                            </div>

                            {perfil.gastos.map((gasto, idx) => (
                                <div
                                    key={idx}
                                    className={`gd-tabla-fila ${idx % 2 === 0 ? 'gd-tabla-fila--par' : ''} ${gasto.conflictivo ? 'gd-tabla-fila--conflictivo' : ''}`}
                                >
                                    <span className="gd-col-gasto">
                                        {gasto.conflictivo && (
                                            <AlertTriangle size={14} className="gd-icon-warning" />
                                        )}
                                        {gasto.nombre}
                                    </span>
                                    <span className={`gd-col-pct gd-pct-badge ${getPorcentajeClass(gasto.porcentaje)}`}>
                                        {getPorcentajeLabel(gasto)}
                                    </span>
                                    <span className="gd-col-limite">{gasto.limite}</span>
                                    <span className="gd-col-consejo">{gasto.consejo}</span>
                                </div>
                            ))}
                        </div>

                        {/* Aviso vehiculo — solo si no es transporte */}
                        {perfil.id !== 'transporte' && (
                            <div className="gd-warning-card">
                                <AlertTriangle size={18} className="gd-warning-icon" />
                                <div>
                                    <p className="gd-warning-title">El vehículo: el gasto más conflictivo con Hacienda</p>
                                    <p className="gd-warning-text">
                                        En IRPF, el vehículo solo es deducible al 100% para actividades de transporte, reparto, taxi o
                                        VTC. Para el resto de autónomos, Hacienda deniega la deducción en IRPF porque alega uso mixto.
                                        El IVA sí puede deducirse al 50% si el vehículo es necesario para la actividad.
                                        Es el gasto que genera más litigios en la AEAT.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Aviso IVA exento — solo sanitarios */}
                        {perfil.id === 'sanitario' && (
                            <div className="gd-info-card">
                                <Info size={18} className="gd-info-icon" />
                                <div>
                                    <p className="gd-info-title">Actividad exenta de IVA (Art. 20 LIVA)</p>
                                    <p className="gd-info-text">
                                        Las actividades sanitarias reconocidas están exentas de IVA. Esto significa que no
                                        repercutes IVA en tus facturas, pero tampoco puedes deducir el IVA de tus gastos.
                                        En IRPF, los gastos se deducen por su importe total (IVA incluido), lo que en
                                        parte compensa.
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* ---- Paso 3: Calcula tu ahorro ---- */}
                        <div className="gd-section gd-ahorro-section">
                            <div className="gd-step-header">
                                <span className="gd-step-badge">Paso 3</span>
                                <h2 className="gd-step-title">Calcula tu ahorro fiscal estimado</h2>
                            </div>

                            <div className="gd-ahorro-layout">
                                <div className="gd-ahorro-input-wrap">
                                    <label className="gd-ahorro-label" htmlFor="gastos-mes">
                                        ¿Cuánto gastas al mes en gastos deducibles?
                                    </label>
                                    <div className="gd-ahorro-input-row">
                                        <Euro size={20} className="gd-ahorro-euro" />
                                        <input
                                            id="gastos-mes"
                                            type="number"
                                            className="gd-ahorro-input"
                                            placeholder="500"
                                            min={0}
                                            step={50}
                                            value={gastosInput}
                                            onChange={e => setGastosInput(e.target.value)}
                                        />
                                        <span className="gd-ahorro-suffix">EUR / mes</span>
                                    </div>
                                    <p className="gd-ahorro-hint">
                                        Suma todos los gastos deducibles de la tabla anterior
                                    </p>
                                </div>

                                {gastosAnuales > 0 && (
                                    <div className="gd-ahorro-resultado">
                                        <div className="gd-ahorro-card">
                                            <TrendingUp size={24} className="gd-ahorro-card-icon" />
                                            <div className="gd-ahorro-card-label">Ahorro estimado en IRPF al año</div>
                                            <div className="gd-ahorro-card-valor">
                                                {formatEur(ahorroEstimado)}
                                                <span className="gd-ahorro-card-eur">EUR</span>
                                            </div>
                                            <div className="gd-ahorro-card-base">
                                                Sobre {formatEur(gastosAnuales * 12)} EUR anuales de gastos
                                            </div>
                                        </div>
                                        <div className="gd-ahorro-disclaimer">
                                            <Info size={13} />
                                            <span>
                                                Estimación orientativa aplicando un tipo marginal medio del 25%.
                                                Para un cálculo exacto, usa la{' '}
                                                <a href="/guia-fiscal" className="gd-link">Guía Fiscal</a>.
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* ---- CTA ---- */}
                        <div className="gd-cta-section">
                            <p className="gd-cta-texto">
                                ¿Quieres saber exactamente cuánto te queda limpio cada mes?
                            </p>
                            <a href="/calculadora-neto" className="gd-cta-btn">
                                Calcula cuánto te queda limpio
                                <ChevronRight size={18} />
                            </a>
                        </div>

                    </section>
                )}

                {/* ---- Estado vacío ---- */}
                {!perfil && (
                    <div className="gd-empty-state">
                        <div className="gd-empty-icon">
                            <Info size={32} />
                        </div>
                        <p className="gd-empty-text">
                            Selecciona tu actividad para ver la checklist de gastos deducibles personalizada
                        </p>
                    </div>
                )}

            </main>
        </div>
    )
}
