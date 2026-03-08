import { useState } from 'react'
import { ChevronDown, ChevronRight, MapPin, Tag } from 'lucide-react'
import { useFiscalFields, FiscalSection, FiscalField } from '../hooks/useFiscalFields'
import './DynamicFiscalForm.css'

export interface DynamicFiscalFormProps {
    ccaa: string | null
    values: Record<string, any>
    onChange: (key: string, value: any) => void
    compact?: boolean
}

function FieldBadges({ field }: { field: FiscalField }) {
    return (
        <span className="dff-badges">
            {field.foral_only && (
                <span className="dff-badge dff-badge--foral">
                    <MapPin size={10} />
                    Foral
                </span>
            )}
            {(field.deductions_count ?? 0) > 0 && (
                <span className="dff-badge dff-badge--deductions">
                    <Tag size={10} />
                    {field.deductions_count} deducc.
                </span>
            )}
        </span>
    )
}

function FiscalFieldInput({
    field,
    value,
    onChange,
}: {
    field: FiscalField
    value: any
    onChange: (key: string, value: any) => void
}) {
    const handleChange = (raw: any) => {
        if (field.type === 'bool') {
            onChange(field.key, raw)
        } else if (field.type === 'number') {
            onChange(field.key, raw !== '' ? Number(raw) : null)
        } else {
            onChange(field.key, raw || null)
        }
    }

    if (field.type === 'bool') {
        return (
            <div className="dff-field dff-field--bool">
                <label className="dff-checkbox-label">
                    <input
                        type="checkbox"
                        checked={!!value}
                        onChange={(e) => handleChange(e.target.checked)}
                        className="dff-checkbox"
                    />
                    <span className="dff-checkbox-text">
                        {field.label}
                        <FieldBadges field={field} />
                    </span>
                </label>
                {field.help_text && (
                    <span className="dff-help-text">{field.help_text}</span>
                )}
            </div>
        )
    }

    if (field.type === 'select') {
        return (
            <div className="dff-field">
                <label className="dff-label">
                    {field.label}
                    <FieldBadges field={field} />
                    {field.required && <span className="dff-required">*</span>}
                </label>
                <select
                    className="form-input dff-select"
                    value={value ?? ''}
                    onChange={(e) => handleChange(e.target.value)}
                >
                    <option value="">Selecciona...</option>
                    {(field.options ?? []).map((opt) => (
                        <option key={opt} value={opt}>
                            {opt}
                        </option>
                    ))}
                </select>
                {field.help_text && (
                    <span className="dff-help-text">{field.help_text}</span>
                )}
            </div>
        )
    }

    if (field.type === 'date') {
        return (
            <div className="dff-field">
                <label className="dff-label">
                    {field.label}
                    <FieldBadges field={field} />
                </label>
                <input
                    type="date"
                    className="form-input"
                    value={value ?? ''}
                    onChange={(e) => handleChange(e.target.value)}
                />
                {field.help_text && (
                    <span className="dff-help-text">{field.help_text}</span>
                )}
            </div>
        )
    }

    if (field.type === 'number') {
        return (
            <div className="dff-field">
                <label className="dff-label">
                    {field.label}
                    <FieldBadges field={field} />
                </label>
                <div className="input-with-suffix">
                    <input
                        type="number"
                        className="form-input"
                        placeholder="0"
                        min="0"
                        value={value ?? ''}
                        onChange={(e) => handleChange(e.target.value)}
                    />
                    <span className="input-suffix">EUR</span>
                </div>
                {field.help_text && (
                    <span className="dff-help-text">{field.help_text}</span>
                )}
            </div>
        )
    }

    // text (fallback)
    return (
        <div className="dff-field">
            <label className="dff-label">
                {field.label}
                <FieldBadges field={field} />
            </label>
            <input
                type="text"
                className="form-input"
                placeholder=""
                value={value ?? ''}
                onChange={(e) => handleChange(e.target.value)}
            />
            {field.help_text && (
                <span className="dff-help-text">{field.help_text}</span>
            )}
        </div>
    )
}

function CollapsibleSection({
    section,
    values,
    onChange,
    compact,
}: {
    section: FiscalSection
    values: Record<string, any>
    onChange: (key: string, value: any) => void
    compact?: boolean
}) {
    const [open, setOpen] = useState(section.expanded_default ?? false)

    if (!section.collapsible) {
        return (
            <div className={`dff-section ${compact ? 'dff-section--compact' : ''}`}>
                <h4 className="dff-section-title">{section.title}</h4>
                <div className="dff-fields-grid">
                    {section.fields.map((field) => (
                        <FiscalFieldInput
                            key={field.key}
                            field={field}
                            value={values[field.key]}
                            onChange={onChange}
                        />
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className={`dff-section ${compact ? 'dff-section--compact' : ''}`}>
            <button
                type="button"
                className="collapsible-header dff-collapsible-header"
                onClick={() => setOpen((v) => !v)}
            >
                {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                <span>{section.title}</span>
            </button>
            {open && (
                <div className="collapsible-content dff-fields-grid">
                    {section.fields.map((field) => (
                        <FiscalFieldInput
                            key={field.key}
                            field={field}
                            value={values[field.key]}
                            onChange={onChange}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

export default function DynamicFiscalForm({
    ccaa,
    values,
    onChange,
    compact = false,
}: DynamicFiscalFormProps) {
    const { sections, regime, loading } = useFiscalFields(ccaa)

    if (!ccaa) {
        return (
            <div className="dff-empty">
                <MapPin size={20} className="dff-empty-icon" />
                <p>Selecciona tu comunidad autónoma para ver las deducciones disponibles</p>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="dff-loading">
                <span className="dff-spinner" />
                Cargando campos fiscales para {ccaa}...
            </div>
        )
    }

    if (sections.length === 0) {
        // Endpoint not available yet — degrade gracefully
        return null
    }

    return (
        <div className={`dff-root ${compact ? 'dff-root--compact' : ''}`}>
            {regime && (
                <div className="dff-regime-badge">
                    {regime === 'foral_vasco' && 'Régimen foral vasco'}
                    {regime === 'foral_navarra' && 'Régimen foral de Navarra'}
                    {regime === 'ceuta_melilla' && 'Régimen Ceuta / Melilla'}
                    {regime === 'canarias' && 'Régimen Canarias (IGIC)'}
                    {regime === 'comun' && 'Régimen común IRPF'}
                </div>
            )}

            {sections.map((section) => (
                <CollapsibleSection
                    key={section.id}
                    section={section}
                    values={values}
                    onChange={onChange}
                    compact={compact}
                />
            ))}
        </div>
    )
}
