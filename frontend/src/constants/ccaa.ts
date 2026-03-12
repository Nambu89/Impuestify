/**
 * Single source of truth for CCAA identifiers in the frontend.
 * Convention: short names with correct Spanish accents.
 *
 * These values are stored in the DB and sent to the API.
 * Display labels are separate and only used for rendering.
 */

export const CCAA_IDS = [
    'Andalucía',
    'Aragón',
    'Asturias',
    'Baleares',
    'Canarias',
    'Cantabria',
    'Castilla y León',
    'Castilla-La Mancha',
    'Cataluña',
    'Ceuta',
    'Valencia',
    'Extremadura',
    'Galicia',
    'La Rioja',
    'Madrid',
    'Melilla',
    'Murcia',
    'Navarra',
    'Araba',
    'Bizkaia',
    'Gipuzkoa',
] as const

export type CcaaId = (typeof CCAA_IDS)[number]

/** Display labels where they differ from the canonical ID */
export const CCAA_DISPLAY_LABELS: Partial<Record<CcaaId, string>> = {
    Baleares: 'Illes Balears',
    Valencia: 'Comunitat Valenciana',
    Madrid: 'Comunidad de Madrid',
    Murcia: 'Región de Murcia',
    Araba: 'Araba/Álava',
}

/** Get the display label for a CCAA ID */
export function getCcaaLabel(id: string): string {
    return (CCAA_DISPLAY_LABELS as Record<string, string>)[id] || id
}

/** CCAA_OPTIONS for dropdowns: { value, label } */
export const CCAA_OPTIONS = CCAA_IDS.map(id => ({
    value: id,
    label: getCcaaLabel(id),
}))

/** CCAA_OPTIONS with empty placeholder for forms */
export const CCAA_OPTIONS_WITH_PLACEHOLDER = [
    { value: '', label: 'Selecciona tu comunidad' },
    ...CCAA_OPTIONS,
]

/** Foral territory IDs */
export const FORAL_CCAA: CcaaId[] = ['Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra']

/** Check if a CCAA is foral */
export function isForal(ccaa: string): boolean {
    return (FORAL_CCAA as string[]).includes(ccaa)
}

/** Check if a CCAA is Ceuta/Melilla */
export function isCeutaMelilla(ccaa: string): boolean {
    return ccaa === 'Ceuta' || ccaa === 'Melilla'
}
