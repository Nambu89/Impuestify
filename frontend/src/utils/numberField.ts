/**
 * Helpers para inputs numéricos que deben distinguir TRES estados:
 *
 *   1. vacío          → `undefined` (dato NO facilitado; la clave se omite del
 *                       payload y el backend aplica su valor por defecto)
 *   2. cero explícito → `0` (el usuario ha escrito un 0: es un dato)
 *   3. cualquier otro → el número
 *
 * Por qué importa: en el Modelo 130 el `rend_neto_anterior` por defecto vale
 * `None` en el backend. Un `0` explícito cae en el primer tramo del
 * art. 110.3.c) RIRPF (≤ 9.000 EUR → 100 EUR de minoración trimestral). Si el
 * frontend convierte "campo vacío" en `0`, la aplicación regala esos 100 EUR
 * por trimestre a quien no rellene el dato. Lo mismo, en otra dirección, con
 * `pct_atribucion_estado` (defecto 100 %) y `anos_actividad` (defecto 3).
 *
 * Los dos idioms que colapsan estados y que NO deben usarse en estos campos:
 *   - `parseFloat(e.target.value) || 0`  → vacío y NaN se vuelven 0
 *   - `value || ''`                      → un 0 explícito se muestra vacío
 */

/**
 * Convierte el valor crudo de un `<input>` en `number | undefined`.
 *
 * Cadena vacía (o solo espacios) → `undefined`. Cualquier cosa que no sea un
 * número finito (NaN, Infinity) → `undefined` también: preferimos "no
 * facilitado" a inventarnos un 0.
 */
export function parseOptionalNumber(raw: string): number | undefined {
    if (raw.trim() === '') return undefined
    const parsed = Number(raw)
    return Number.isFinite(parsed) ? parsed : undefined
}

/**
 * Valor a mostrar en el `<input>`. Un 0 explícito se muestra como "0"
 * (a diferencia de `value || ''`, que lo borraría de la pantalla).
 */
export function formatOptionalNumber(value: number | null | undefined): string {
    if (value === null || value === undefined) return ''
    if (!Number.isFinite(value)) return ''
    return String(value)
}

/**
 * Asigna un campo opcional en un objeto de formulario: si el valor es
 * `undefined` la clave se ELIMINA, para que no viaje como `null` ni quede
 * fantasma en el `form_data` que se persiste al guardar la declaración.
 */
export function withOptionalField<T extends object, K extends keyof T & string>(
    data: T,
    field: K,
    value: number | undefined,
): T {
    const next: Record<string, unknown> = { ...(data as Record<string, unknown>) }
    if (value === undefined) {
        delete next[field]
    } else {
        next[field] = value
    }
    return next as T
}
