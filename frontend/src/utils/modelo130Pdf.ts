/**
 * Adaptador: resultado de cálculo del Modelo 130 → payload que espera el
 * generador de PDF del backend (`ModeloPDFGenerator._render_130`).
 *
 * ## Por qué existe este fichero
 *
 * Hay DOS productores de resultados del Modelo 130 en el backend y devuelven
 * formas distintas:
 *
 *   - `app/tools/modelo_130_tool.py` (el que usa el chat) devuelve
 *     `seccion_i` / `deduccion_80bis` / `resultado_final`.
 *   - `app/utils/calculators/modelo_130.py` (el que sirve
 *     `POST /api/declarations/130/calculate`, el que consume esta página)
 *     devuelve `casillas` / `resultado`.
 *
 * `_render_130` lee la PRIMERA forma. `POST /api/export/modelo-pdf` pasa
 * `body.data` al renderizador tal cual, sin transformar. Así que enviarle
 * directamente el resultado del calculador producía un PDF con las casillas
 * 01-07 y el resultado a CERO, y la 13 omitida: el usuario se descargaba un
 * Modelo 130 en blanco creyendo que eran sus números.
 *
 * La traducción se hace aquí, en el cliente, y no en el renderizador, porque:
 *
 *   1. El contrato de `_render_130` está documentado y lo comparte el chat.
 *      Cambiarlo obligaría a tocar un fichero que ya tiene cambios sin mergear
 *      de otra rama.
 *   2. Solo el frontend sabe el territorio elegido en el selector, que es lo
 *      que decide la `variante_foral`. Sin ese dato el renderizador pinta un
 *      130 común aunque el cálculo sea de Bizkaia.
 *   3. Es una traducción de forma, no de lógica fiscal: ningún importe se
 *      recalcula aquí.
 *
 * ## Numeración de casillas: cuidado con la 05 y la 06
 *
 * El diseño de registro de la AEAT (DR130e15v12.xls) define:
 *   [05] pagos fraccionados de trimestres anteriores
 *   [06] retenciones e ingresos a cuenta soportados
 *
 * Pero las claves del calculador REST están al revés respecto a esa
 * numeración (`05_retenciones_acumuladas`, `06_pagos_anteriores`), por
 * compatibilidad histórica. Por eso el mapeo de abajo es SEMÁNTICO (retenciones
 * con retenciones, pagos con pagos) y no por número: copiar por número
 * intercambiaría los dos importes en el PDF.
 */

/** Resultado de `POST /api/declarations/130/calculate`. */
export interface Modelo130ApiResult {
    territory?: string
    quarter?: number
    resultado?: number
    tipo_aplicado?: number
    regimen?: string
    modalidad?: string
    casillas?: Record<string, number>
    desglose?: Record<string, unknown>
}

/**
 * Territorio del selector → `variante_foral` que reconoce el backend
 * (`MODELO_130_FORAL_VARIANTS` en `modelo_pdf_generator.py`).
 */
export const FORAL_VARIANT_BY_TERRITORY_130: Record<string, string> = {
    Araba: '130-araba',
    Gipuzkoa: '130-gipuzkoa',
    Bizkaia: '130-bizkaia',
    Navarra: '130-navarra',
}

export function foralVariantFor130(territory: string | undefined): string | undefined {
    if (!territory) return undefined
    return FORAL_VARIANT_BY_TERRITORY_130[territory.trim()]
}

function num(value: unknown): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

/** Importes de la Sección I, ya desambiguados semánticamente. */
export interface Seccion130Amounts {
    ingresos: number
    gastos: number
    rendimientoNeto: number
    cuota: number
    /** Retenciones e ingresos a cuenta soportados — casilla 06 AEAT. */
    retenciones: number
    /** Pagos fraccionados de trimestres anteriores — casilla 05 AEAT. */
    pagosAnteriores: number
    resultadoSeccion: number
    /** Minoración art. 110.3.c) RIRPF — casilla 13. */
    minoracion13: number
    resultadoFinal: number
    /** Porcentaje aplicado (20 / 8), en tanto por ciento. */
    tipoAplicado: number
}

/** Construye el payload común (Territorio Común / Ceuta-Melilla). */
export function buildComun130PdfData(amounts: Seccion130Amounts): Record<string, unknown> {
    return {
        seccion_i: {
            ingresos_computables: amounts.ingresos,
            gastos_deducibles: amounts.gastos,
            rendimiento_neto: amounts.rendimientoNeto,
            veinte_porciento: amounts.cuota,
            retenciones: amounts.retenciones,
            pagos_anteriores: amounts.pagosAnteriores,
            resultado_seccion: amounts.resultadoSeccion,
        },
        deduccion_80bis: amounts.minoracion13,
        tipo_aplicado: amounts.tipoAplicado,
        resultado_final: amounts.resultadoFinal,
    }
}

/**
 * Payload de PDF a partir del resultado de `/api/declarations/130/calculate`.
 *
 * @param result Resultado devuelto por el endpoint.
 * @param territory Territorio del selector: "Comun" | "Araba" | "Gipuzkoa" |
 *   "Bizkaia" | "Navarra".
 */
export function buildModelo130PdfData(
    result: Modelo130ApiResult | null | undefined,
    territory: string,
): Record<string, unknown> {
    const casillas = result?.casillas ?? {}
    const variante = foralVariantFor130(territory)

    if (variante) {
        // Ruta foral: `_render_130_foral` pinta la tabla directamente desde
        // `casillas`, así que se pasa tal cual. Lo que hay que añadir es la
        // `variante_foral` (si falta, el backend pinta un 130 común con
        // etiquetas que no corresponden y todas las filas a cero) y el
        // `resultado_final`, que el calculador llama `resultado`.
        //
        // LIMITACIÓN CONOCIDA — la arregla el backend, no esto:
        // el backend tiene DOS implementaciones forales del 130. Las dedicadas
        // (`modelo_130_bizkaia.py`, `modelo_130_gipuzkoa.py`, …), que alimentan
        // al chat, numeran las casillas (`01_base_calculo`, …). La genérica de
        // `/api/declarations/130/calculate`, que alimenta esta página, devuelve
        // claves sin numerar (`base_calculo`, `pago_trimestral`, …) en Bizkaia
        // general/excepcional y en Navarra. `_render_130_foral` saca el número
        // de casilla del prefijo de la clave, así que en esos casos la columna
        // "Casilla" sale como "base" o "pago" en vez de "01" o "06".
        //
        // NO se renumera aquí a propósito: asignar un número oficial de casilla
        // desde el frontend sería inventarse una referencia normativa en un
        // documento tributario. Los importes, los conceptos y el resultado sí
        // son correctos. La solución de verdad es unificar las dos
        // implementaciones forales del backend.
        const payload: Record<string, unknown> = {
            variante_foral: variante,
            casillas,
            resultado_final: num(result?.resultado),
        }
        if (result?.tipo_aplicado !== undefined) payload.tipo_aplicado = result.tipo_aplicado
        if (result?.regimen) payload.regimen = result.regimen
        if (result?.modalidad) payload.modalidad = result.modalidad
        return payload
    }

    return buildComun130PdfData({
        ingresos: num(casillas['01_ingresos_acumulados']),
        gastos: num(casillas['02_gastos_acumulados']),
        rendimientoNeto: num(casillas['03_rendimiento_neto']),
        cuota: num(casillas['04_cuota_20pct']),
        // Mapeo SEMÁNTICO: ver la nota sobre la 05/06 en la cabecera.
        retenciones: num(casillas['05_retenciones_acumuladas']),
        pagosAnteriores: num(casillas['06_pagos_anteriores']),
        resultadoSeccion: num(casillas['07_resultado_seccion_I']),
        minoracion13: num(casillas['13_deduccion_art80bis']),
        resultadoFinal: num(result?.resultado),
        tipoAplicado: num(result?.tipo_aplicado),
    })
}

/** Casillas de la calculadora pública `/calculadora-130` (cálculo en cliente). */
export interface Modelo130LocalResult {
    casilla01: number
    casilla02: number
    casilla03: number
    casilla04: number
    /** Pagos fraccionados anteriores (numeración AEAT). */
    casilla05: number
    /** Retenciones acumuladas (numeración AEAT). */
    casilla06: number
    casilla07: number
    casilla13: number
    casilla19: number
    /** Tipo en tanto por uno (0,2 / 0,08). */
    porcentaje: number
}

/**
 * Payload de PDF para la calculadora pública.
 *
 * Ojo: esta calculadora numera las casillas 05/06 según la AEAT (05 = pagos,
 * 06 = retenciones), justo al revés que las claves del calculador del backend.
 * Por eso el mapeo aquí no es el mismo que en `buildModelo130PdfData`.
 */
export function buildModelo130PdfDataFromLocal(
    result: Modelo130LocalResult,
): Record<string, unknown> {
    return buildComun130PdfData({
        ingresos: num(result.casilla01),
        gastos: num(result.casilla02),
        rendimientoNeto: num(result.casilla03),
        cuota: num(result.casilla04),
        retenciones: num(result.casilla06),
        pagosAnteriores: num(result.casilla05),
        resultadoSeccion: num(result.casilla07),
        minoracion13: num(result.casilla13),
        resultadoFinal: num(result.casilla19),
        tipoAplicado: num(result.porcentaje) * 100,
    })
}
