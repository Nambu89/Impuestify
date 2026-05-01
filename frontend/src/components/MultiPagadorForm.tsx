import { useState } from 'react'
import { Pagador } from '../hooks/useFiscalProfile'
import './MultiPagadorForm.css'

interface MultiPagadorFormProps {
    pagadores: Pagador[]
    onChange: (pagadores: Pagador[]) => void
    maxPagadores?: number
}

const CLAVE_OPTIONS: { value: Pagador['clave']; label: string }[] = [
    { value: 'empleado', label: 'Empleado' },
    { value: 'pensionista', label: 'Pensionista' },
    { value: 'desempleo', label: 'Desempleo' },
    { value: 'otro', label: 'Otro' },
]

function emptyPagador(): Pagador {
    return {
        nombre: '',
        nif: undefined,
        clave: 'empleado',
        retribuciones_dinerarias: 0,
        retenciones: 0,
        gastos_deducibles: 0,
        retribuciones_especie: 0,
        ingresos_cuenta: 0,
    }
}

function PagadorCard({
    pagador,
    index,
    total,
    onChange,
    onDelete,
}: {
    pagador: Pagador
    index: number
    total: number
    onChange: (updated: Pagador) => void
    onDelete: () => void
}) {
    const [expanded, setExpanded] = useState(true)
    const [showExtra, setShowExtra] = useState(
        pagador.retribuciones_especie > 0 || pagador.ingresos_cuenta > 0
    )

    const update = (partial: Partial<Pagador>) => onChange({ ...pagador, ...partial })

    const hasData = pagador.nombre.trim() !== '' || pagador.retribuciones_dinerarias > 0

    const handleDelete = () => {
        if (hasData) {
            if (!window.confirm(`¿Eliminar el pagador "${pagador.nombre || `Pagador ${index + 1}`}"?`)) {
                return
            }
        }
        onDelete()
    }

    const displayName = pagador.nombre.trim() || `Pagador ${index + 1}`
    const claveLabel = CLAVE_OPTIONS.find(o => o.value === pagador.clave)?.label ?? pagador.clave

    return (
        <div className="mp-pagador">
            <div
                className={`mp-pagador__header ${expanded ? 'mp-pagador__header--expanded' : ''}`}
                onClick={() => setExpanded(e => !e)}
                role="button"
                tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(v => !v) } }}
                aria-expanded={expanded}
            >
                <div className="mp-pagador__header-info">
                    <span className="mp-pagador__header-index">{index + 1}</span>
                    <div>
                        <span className="mp-pagador__header-name">{displayName}</span>
                        {!expanded && pagador.retribuciones_dinerarias > 0 && (
                            <span className="mp-pagador__header-summary">
                                {pagador.retribuciones_dinerarias.toLocaleString('es-ES')} EUR · {claveLabel}
                            </span>
                        )}
                    </div>
                </div>
                <div className="mp-pagador__header-actions">
                    <span className="mp-pagador__chevron" aria-hidden="true">
                        {expanded ? '▲' : '▼'}
                    </span>
                    {total > 1 && (
                        <button
                            type="button"
                            className="mp-pagador__delete"
                            onClick={e => { e.stopPropagation(); handleDelete() }}
                            aria-label={`Eliminar ${displayName}`}
                            title="Eliminar pagador"
                        >
                            ×
                        </button>
                    )}
                </div>
            </div>

            {expanded && (
                <div className="mp-pagador__fields">
                    <div className="mp-field">
                        <label className="mp-field__label">Nombre del pagador</label>
                        <div className="mp-field__input-wrap">
                            <input
                                type="text"
                                className="mp-field__input"
                                value={pagador.nombre}
                                onChange={e => update({ nombre: e.target.value })}
                                placeholder="Nombre del pagador"
                            />
                        </div>
                    </div>

                    <div className="mp-field">
                        <label className="mp-field__label">Tipo de rendimiento</label>
                        <select
                            className="mp-field__select"
                            value={pagador.clave}
                            onChange={e => update({ clave: e.target.value as Pagador['clave'] })}
                        >
                            {CLAVE_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                    </div>

                    <div className="mp-field">
                        <label className="mp-field__label">Retribuciones brutas</label>
                        <div className="mp-field__input-wrap">
                            <input
                                type="number"
                                className="mp-field__input"
                                value={pagador.retribuciones_dinerarias || ''}
                                onChange={e => update({ retribuciones_dinerarias: parseFloat(e.target.value) || 0 })}
                                min={0}
                                step={100}
                                inputMode="decimal"
                                placeholder="0"
                            />
                            <span className="mp-field__suffix">EUR</span>
                        </div>
                    </div>

                    <div className="mp-field">
                        <label className="mp-field__label">Retenciones IRPF</label>
                        <div className="mp-field__input-wrap">
                            <input
                                type="number"
                                className="mp-field__input"
                                value={pagador.retenciones || ''}
                                onChange={e => update({ retenciones: parseFloat(e.target.value) || 0 })}
                                min={0}
                                step={100}
                                inputMode="decimal"
                                placeholder="0"
                            />
                            <span className="mp-field__suffix">EUR</span>
                        </div>
                    </div>

                    <div className="mp-field">
                        <label className="mp-field__label">Cotizaciones SS</label>
                        <div className="mp-field__input-wrap">
                            <input
                                type="number"
                                className="mp-field__input"
                                value={pagador.gastos_deducibles || ''}
                                onChange={e => update({ gastos_deducibles: parseFloat(e.target.value) || 0 })}
                                min={0}
                                step={10}
                                inputMode="decimal"
                                placeholder="0"
                            />
                            <span className="mp-field__suffix">EUR</span>
                        </div>
                        <span className="mp-field__help">Cuota del trabajador a la Seguridad Social</span>
                    </div>

                    <button
                        type="button"
                        className="mp-pagador__extra-toggle"
                        onClick={() => setShowExtra(v => !v)}
                    >
                        {showExtra ? '▲ Ocultar' : '▼ Mostrar'} retribuciones en especie e ingresos a cuenta
                    </button>

                    {showExtra && (
                        <div className="mp-pagador__extra-fields">
                            <div className="mp-field">
                                <label className="mp-field__label">Retribuciones en especie</label>
                                <div className="mp-field__input-wrap">
                                    <input
                                        type="number"
                                        className="mp-field__input"
                                        value={pagador.retribuciones_especie || ''}
                                        onChange={e => update({ retribuciones_especie: parseFloat(e.target.value) || 0 })}
                                        min={0}
                                        step={100}
                                        inputMode="decimal"
                                        placeholder="0"
                                    />
                                    <span className="mp-field__suffix">EUR</span>
                                </div>
                                <span className="mp-field__help">Coche empresa, seguro médico, tickets restaurante...</span>
                            </div>

                            <div className="mp-field">
                                <label className="mp-field__label">Ingresos a cuenta</label>
                                <div className="mp-field__input-wrap">
                                    <input
                                        type="number"
                                        className="mp-field__input"
                                        value={pagador.ingresos_cuenta || ''}
                                        onChange={e => update({ ingresos_cuenta: parseFloat(e.target.value) || 0 })}
                                        min={0}
                                        step={10}
                                        inputMode="decimal"
                                        placeholder="0"
                                    />
                                    <span className="mp-field__suffix">EUR</span>
                                </div>
                                <span className="mp-field__help">Ingreso a cuenta de retribuciones en especie</span>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default function MultiPagadorForm({
    pagadores,
    onChange,
    maxPagadores = 10,
}: MultiPagadorFormProps) {
    const handleChangePagador = (index: number, updated: Pagador) => {
        const next = [...pagadores]
        next[index] = updated
        onChange(next)
    }

    const handleDelete = (index: number) => {
        const next = pagadores.filter((_, i) => i !== index)
        onChange(next)
    }

    const handleAdd = () => {
        if (pagadores.length >= maxPagadores) return
        onChange([...pagadores, emptyPagador()])
    }

    const totalRetribuciones = pagadores.reduce(
        (sum, p) => sum + p.retribuciones_dinerarias + p.retribuciones_especie + p.ingresos_cuenta,
        0
    )
    const totalRetenciones = pagadores.reduce((sum, p) => sum + p.retenciones, 0)
    const totalSS = pagadores.reduce((sum, p) => sum + p.gastos_deducibles, 0)

    return (
        <div className="mp-form">
            {pagadores.map((pagador, index) => (
                <PagadorCard
                    key={index}
                    pagador={pagador}
                    index={index}
                    total={pagadores.length}
                    onChange={updated => handleChangePagador(index, updated)}
                    onDelete={() => handleDelete(index)}
                />
            ))}

            {pagadores.length < maxPagadores && (
                <button
                    type="button"
                    className="mp-form__add-btn"
                    onClick={handleAdd}
                >
                    + Añadir pagador
                </button>
            )}

            {pagadores.length > 0 && (
                <div className="mp-totals">
                    <div className="mp-totals__item">
                        <span className="mp-totals__label">Total retribuciones</span>
                        <span className="mp-totals__value">{totalRetribuciones.toLocaleString('es-ES')} EUR</span>
                    </div>
                    <div className="mp-totals__item">
                        <span className="mp-totals__label">Total retenciones</span>
                        <span className="mp-totals__value">{totalRetenciones.toLocaleString('es-ES')} EUR</span>
                    </div>
                    <div className="mp-totals__item">
                        <span className="mp-totals__label">Total SS</span>
                        <span className="mp-totals__value">{totalSS.toLocaleString('es-ES')} EUR</span>
                    </div>
                </div>
            )}
        </div>
    )
}
