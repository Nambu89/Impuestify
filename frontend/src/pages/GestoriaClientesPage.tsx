import { useEffect, useState } from 'react'
import Header from '../components/Header'
import type { GestoriaClient, GestoriaClientInput, ClientTipo } from '../hooks/useGestoriaClients'
import { useActiveClient } from '../context/ActiveClientContext'

const MAX_CLIENTS = 3

const TIPOS: { value: ClientTipo; label: string }[] = [
    { value: 'particular', label: 'Particular' },
    { value: 'autonomo', label: 'Autónomo' },
    { value: 'sociedad', label: 'Sociedad (pyme)' },
]

const EMPTY: GestoriaClientInput = { nombre_cliente: '', tipo: 'particular' }

export default function GestoriaClientesPage() {
    const { clients, loading, error, fetchClients, createClient, updateClient, deleteClient } =
        useActiveClient()
    const [form, setForm] = useState<GestoriaClientInput>(EMPTY)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [formError, setFormError] = useState<string | null>(null)
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        void fetchClients()
    }, [fetchClients])

    const atLimit = clients.length >= MAX_CLIENTS && !editingId

    const onEdit = (c: GestoriaClient) => {
        setEditingId(c.id)
        setForm({
            nombre_cliente: c.nombre_cliente,
            tipo: c.tipo,
            nif: c.nif ?? '',
            ccaa: c.ccaa ?? '',
            situacion_laboral: c.situacion_laboral ?? '',
            epigrafe_iae: c.epigrafe_iae ?? '',
            regimen_iva: c.regimen_iva ?? '',
            fecha_alta: c.fecha_alta ?? '',
        })
        setFormError(null)
    }

    const onCancel = () => {
        setEditingId(null)
        setForm(EMPTY)
        setFormError(null)
    }

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError(null)
        if (!form.nombre_cliente.trim()) {
            setFormError('El nombre del cliente es obligatorio.')
            return
        }
        setSaving(true)
        try {
            if (editingId) {
                await updateClient(editingId, form)
            } else {
                await createClient(form)
            }
            onCancel()
        } catch (err: unknown) {
            const anyErr = err as { message?: string; status?: number }
            const is409 =
                anyErr?.status === 409 ||
                (typeof anyErr?.message === 'string' && anyErr.message.includes('409'))
            setFormError(
                is409
                    ? `Máximo ${MAX_CLIENTS} clientes en la demo.`
                    : anyErr?.message || 'Error al guardar el cliente.',
            )
        } finally {
            setSaving(false)
        }
    }

    return (
        <>
            <Header />
            <div
                style={{
                    maxWidth: 900,
                    margin: '0 auto',
                    padding: '24px 16px',
                }}
            >
                <h1 style={{ marginBottom: 4 }}>Clientes</h1>
                <p style={{ color: '#6b7280', marginTop: 0, marginBottom: 24 }}>
                    Gestiona tu cartera (máximo {MAX_CLIENTS} clientes en la demo).
                </p>

                {error && (
                    <div
                        style={{
                            background: '#fee2e2',
                            border: '1px solid #fca5a5',
                            borderRadius: 8,
                            padding: '12px 16px',
                            color: '#b91c1c',
                            marginBottom: 16,
                        }}
                    >
                        {error}
                    </div>
                )}

                {/* ── Roster ─────────────────────────────────────────── */}
                <section style={{ marginBottom: 40 }}>
                    <h2 style={{ fontSize: 18, marginBottom: 12 }}>Listado de clientes</h2>

                    {loading && <p style={{ color: '#6b7280' }}>Cargando clientes…</p>}

                    {!loading && clients.length === 0 && (
                        <p style={{ color: '#6b7280' }}>Aún no has añadido clientes.</p>
                    )}

                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {clients.map((c) => (
                            <li
                                key={c.id}
                                style={{
                                    border: '1px solid #e5e7eb',
                                    borderRadius: 8,
                                    padding: '12px 16px',
                                    marginBottom: 8,
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    background: '#fff',
                                }}
                            >
                                <div>
                                    <strong style={{ fontSize: 15 }}>{c.nombre_cliente}</strong>{' '}
                                    <span
                                        style={{
                                            fontSize: 12,
                                            background: '#eff6ff',
                                            color: '#1e40af',
                                            borderRadius: 4,
                                            padding: '2px 7px',
                                            fontWeight: 600,
                                            textTransform: 'capitalize',
                                        }}
                                    >
                                        {c.tipo}
                                    </span>
                                    <div
                                        style={{
                                            fontSize: 13,
                                            color: '#6b7280',
                                            marginTop: 4,
                                        }}
                                    >
                                        {c.ccaa || 'Sin CCAA'} &middot; {c.file_count ?? 0}{' '}
                                        documento
                                        {(c.file_count ?? 0) !== 1 ? 's' : ''}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button
                                        onClick={() => onEdit(c)}
                                        style={{
                                            padding: '6px 14px',
                                            borderRadius: 6,
                                            border: '1px solid #d1d5db',
                                            background: '#fff',
                                            cursor: 'pointer',
                                            fontSize: 13,
                                        }}
                                    >
                                        Editar
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (
                                                window.confirm(`¿Eliminar a ${c.nombre_cliente}?`)
                                            ) {
                                                void deleteClient(c.id)
                                            }
                                        }}
                                        style={{
                                            padding: '6px 14px',
                                            borderRadius: 6,
                                            border: '1px solid #fca5a5',
                                            background: '#fff',
                                            color: '#b91c1c',
                                            cursor: 'pointer',
                                            fontSize: 13,
                                        }}
                                    >
                                        Eliminar
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                </section>

                {/* ── Create / Edit form ────────────────────────────── */}
                <section
                    style={{
                        border: '1px solid #e5e7eb',
                        borderRadius: 10,
                        padding: 24,
                        background: '#fafafa',
                    }}
                >
                    <h2 style={{ fontSize: 18, marginTop: 0, marginBottom: 16 }}>
                        {editingId ? 'Editar cliente' : 'Nuevo cliente'}
                    </h2>

                    {atLimit && (
                        <p
                            style={{
                                background: '#fffbeb',
                                border: '1px solid #fde68a',
                                borderRadius: 6,
                                padding: '10px 14px',
                                color: '#92400e',
                                marginBottom: 16,
                            }}
                        >
                            Has alcanzado el máximo de {MAX_CLIENTS} clientes. Elimina uno para
                            añadir otro.
                        </p>
                    )}

                    <form
                        onSubmit={(e) => void onSubmit(e)}
                        style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                            gap: 16,
                        }}
                    >
                        {/* Nombre */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>
                                Nombre / Razón social <span style={{ color: '#b91c1c' }}>*</span>
                            </span>
                            <input
                                value={form.nombre_cliente}
                                onChange={(e) =>
                                    setForm({ ...form, nombre_cliente: e.target.value })
                                }
                                disabled={atLimit}
                                placeholder="Nombre del cliente"
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* Tipo */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>Tipo</span>
                            <select
                                value={form.tipo}
                                onChange={(e) =>
                                    setForm({ ...form, tipo: e.target.value as ClientTipo })
                                }
                                disabled={atLimit}
                                style={inputStyle(atLimit)}
                            >
                                {TIPOS.map((t) => (
                                    <option key={t.value} value={t.value}>
                                        {t.label}
                                    </option>
                                ))}
                            </select>
                        </label>

                        {/* NIF */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>NIF / CIF</span>
                            <input
                                value={form.nif ?? ''}
                                onChange={(e) => setForm({ ...form, nif: e.target.value })}
                                disabled={atLimit}
                                placeholder="00000000A"
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* CCAA */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>CCAA</span>
                            <input
                                value={form.ccaa ?? ''}
                                onChange={(e) => setForm({ ...form, ccaa: e.target.value })}
                                disabled={atLimit}
                                placeholder="p. ej. Melilla"
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* Epígrafe IAE */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>Epígrafe IAE</span>
                            <input
                                value={form.epigrafe_iae ?? ''}
                                onChange={(e) => setForm({ ...form, epigrafe_iae: e.target.value })}
                                disabled={atLimit}
                                placeholder="p. ej. 611"
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* Régimen IVA */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>Régimen IVA</span>
                            <input
                                value={form.regimen_iva ?? ''}
                                onChange={(e) => setForm({ ...form, regimen_iva: e.target.value })}
                                disabled={atLimit}
                                placeholder="p. ej. General"
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* Fecha de alta */}
                        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>Fecha de alta</span>
                            <input
                                type="date"
                                value={form.fecha_alta ?? ''}
                                onChange={(e) => setForm({ ...form, fecha_alta: e.target.value })}
                                disabled={atLimit}
                                style={inputStyle(atLimit)}
                            />
                        </label>

                        {/* Buttons + error — span all columns */}
                        <div style={{ gridColumn: '1 / -1' }}>
                            {formError && (
                                <div
                                    style={{
                                        background: '#fee2e2',
                                        border: '1px solid #fca5a5',
                                        borderRadius: 6,
                                        padding: '10px 14px',
                                        color: '#b91c1c',
                                        marginBottom: 12,
                                        fontSize: 14,
                                    }}
                                >
                                    {formError}
                                </div>
                            )}
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button
                                    type="submit"
                                    disabled={saving || (atLimit && !editingId)}
                                    style={{
                                        padding: '8px 20px',
                                        borderRadius: 6,
                                        border: 'none',
                                        background:
                                            saving || (atLimit && !editingId)
                                                ? '#9ca3af'
                                                : '#1a56db',
                                        color: '#fff',
                                        fontWeight: 600,
                                        cursor:
                                            saving || (atLimit && !editingId)
                                                ? 'not-allowed'
                                                : 'pointer',
                                        fontSize: 14,
                                    }}
                                >
                                    {saving
                                        ? 'Guardando…'
                                        : editingId
                                          ? 'Guardar cambios'
                                          : 'Añadir cliente'}
                                </button>
                                {editingId && (
                                    <button
                                        type="button"
                                        onClick={onCancel}
                                        style={{
                                            padding: '8px 20px',
                                            borderRadius: 6,
                                            border: '1px solid #d1d5db',
                                            background: '#fff',
                                            cursor: 'pointer',
                                            fontSize: 14,
                                        }}
                                    >
                                        Cancelar
                                    </button>
                                )}
                            </div>
                        </div>
                    </form>
                </section>
            </div>
        </>
    )
}

function inputStyle(disabled: boolean): React.CSSProperties {
    return {
        padding: '8px 10px',
        borderRadius: 6,
        border: '1px solid #d1d5db',
        fontSize: 14,
        background: disabled ? '#f3f4f6' : '#fff',
        color: disabled ? '#9ca3af' : '#111827',
        cursor: disabled ? 'not-allowed' : 'text',
    }
}
