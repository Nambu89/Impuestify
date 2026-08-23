import { describe, it, expect } from 'vitest'
import {
    buildModelo130PdfData,
    buildModelo130PdfDataFromLocal,
    foralVariantFor130,
    type Modelo130ApiResult,
} from './modelo130Pdf'

/**
 * Resultado real de `POST /api/declarations/130/calculate` (Territorio Común,
 * 2T): ingresos 30.000, gastos 10.000, retenciones 500, pagos anteriores 800,
 * rend. neto del año anterior 8.000 → minoración de 100 EUR (art. 110.3.c
 * RIRPF, primer tramo).
 */
const API_RESULT_COMUN: Modelo130ApiResult = {
    territory: 'Comun',
    quarter: 2,
    resultado: 2600,
    tipo_aplicado: 20,
    casillas: {
        '01_ingresos_acumulados': 30000,
        '02_gastos_acumulados': 10000,
        '03_rendimiento_neto': 20000,
        '04_cuota_20pct': 4000,
        '05_retenciones_acumuladas': 500,
        '06_pagos_anteriores': 800,
        '07_resultado_seccion_I': 2700,
        '12_total_liquidacion': 2700,
        '13_deduccion_art80bis': 100,
        '14_cuota_integra_minorada': 2600,
        '15_negativos_anteriores': 0,
        '16_deduccion_vivienda': 0,
        '17_cuota_diferencial': 2600,
        '18_declaracion_anterior': 0,
        '19_resultado_final': 2600,
    },
}

/**
 * Claves EXACTAS que lee `ModeloPDFGenerator._render_130`
 * (backend/app/services/modelo_pdf_generator.py). Si el backend las renombra,
 * este test debe romperse.
 */
const SECCION_I_KEYS = [
    'ingresos_computables',
    'gastos_deducibles',
    'rendimiento_neto',
    'veinte_porciento',
    'retenciones',
    'pagos_anteriores',
    'resultado_seccion',
] as const

describe('buildModelo130PdfData — Territorio Común', () => {
    it('produce las claves que lee _render_130', () => {
        const data = buildModelo130PdfData(API_RESULT_COMUN, 'Comun')
        expect(data).toHaveProperty('seccion_i')
        expect(data).toHaveProperty('deduccion_80bis')
        expect(data).toHaveProperty('resultado_final')
        const seccionI = data.seccion_i as Record<string, number>
        for (const key of SECCION_I_KEYS) {
            expect(seccionI).toHaveProperty(key)
        }
    })

    it('NINGUNA casilla del PDF sale a cero cuando el cálculo trae importes', () => {
        // Este es el bug: se enviaba `{...form, ...result}`, que no tiene
        // `seccion_i`, y el PDF salía con las casillas 01-07 y el resultado a
        // cero. El usuario se descargaba un Modelo 130 en blanco.
        const data = buildModelo130PdfData(API_RESULT_COMUN, 'Comun')
        const seccionI = data.seccion_i as Record<string, number>
        for (const key of SECCION_I_KEYS) {
            expect(seccionI[key], `casilla ${key} a cero en el PDF`).not.toBe(0)
        }
        expect(data.deduccion_80bis).not.toBe(0)
        expect(data.resultado_final).not.toBe(0)
    })

    it('cada importe cae en su casilla', () => {
        const data = buildModelo130PdfData(API_RESULT_COMUN, 'Comun')
        expect(data.seccion_i).toEqual({
            ingresos_computables: 30000,
            gastos_deducibles: 10000,
            rendimiento_neto: 20000,
            veinte_porciento: 4000,
            retenciones: 500,
            pagos_anteriores: 800,
            resultado_seccion: 2700,
        })
        expect(data.deduccion_80bis).toBe(100)
        expect(data.resultado_final).toBe(2600)
        expect(data.tipo_aplicado).toBe(20)
    })

    it('no intercambia retenciones con pagos anteriores', () => {
        // Las claves del calculador REST (`05_retenciones_acumuladas`,
        // `06_pagos_anteriores`) van al revés que la numeración AEAT (05 =
        // pagos, 06 = retenciones). Mapear por número los cruzaría.
        const data = buildModelo130PdfData(API_RESULT_COMUN, 'Comun')
        const seccionI = data.seccion_i as Record<string, number>
        expect(seccionI.retenciones).toBe(500)
        expect(seccionI.pagos_anteriores).toBe(800)
    })

    it('un resultado sin minoración manda 0, no undefined', () => {
        const sinMinoracion: Modelo130ApiResult = {
            ...API_RESULT_COMUN,
            resultado: 2700,
            casillas: { ...API_RESULT_COMUN.casillas, '13_deduccion_art80bis': 0 },
        }
        const data = buildModelo130PdfData(sinMinoracion, 'Comun')
        expect(data.deduccion_80bis).toBe(0)
        expect(data.resultado_final).toBe(2700)
    })

    it('tolera un resultado vacío sin reventar', () => {
        const data = buildModelo130PdfData(null, 'Comun')
        expect(data.seccion_i).toEqual({
            ingresos_computables: 0,
            gastos_deducibles: 0,
            rendimiento_neto: 0,
            veinte_porciento: 0,
            retenciones: 0,
            pagos_anteriores: 0,
            resultado_seccion: 0,
        })
    })
})

describe('buildModelo130PdfData — variantes forales', () => {
    const API_RESULT_ARABA: Modelo130ApiResult = {
        territory: 'Araba',
        quarter: 2,
        resultado: 350,
        tipo_aplicado: 5,
        casillas: {
            '01_ingresos_trimestre': 12000,
            '02_gastos_trimestre': 2000,
            '03_rendimiento_neto_trimestral': 10000,
            '04_cuota_5pct': 500,
            '05_retenciones_trimestre': 150,
            '06_pagos_anteriores': 0,
            '07_resultado': 350,
        },
    }

    it('mapea el territorio del selector a la variante del backend', () => {
        expect(foralVariantFor130('Araba')).toBe('130-araba')
        expect(foralVariantFor130('Gipuzkoa')).toBe('130-gipuzkoa')
        expect(foralVariantFor130('Bizkaia')).toBe('130-bizkaia')
        expect(foralVariantFor130('Navarra')).toBe('130-navarra')
        expect(foralVariantFor130('Comun')).toBeUndefined()
        expect(foralVariantFor130(undefined)).toBeUndefined()
    })

    it('marca la variante foral: sin ella el backend pinta un 130 común vacío', () => {
        const data = buildModelo130PdfData(API_RESULT_ARABA, 'Araba')
        expect(data.variante_foral).toBe('130-araba')
        expect(data.casillas).toEqual(API_RESULT_ARABA.casillas)
        expect(data.resultado_final).toBe(350)
        expect(data.tipo_aplicado).toBe(5)
        // La ruta foral NO usa `seccion_i`.
        expect(data).not.toHaveProperty('seccion_i')
    })

    it('pasa las casillas sin numerar de Bizkaia/Navarra tal cual, sin inventar números', () => {
        // El calculador genérico devuelve claves sin prefijo numérico en
        // Bizkaia general/excepcional y en Navarra, y el renderizador saca el
        // número de casilla del prefijo: la columna "Casilla" sale como "base"
        // o "pago". Los importes y el resultado SÍ son correctos.
        //
        // Renumerar desde aquí sería inventarse una referencia normativa en un
        // documento tributario. Lo suyo es unificar las dos implementaciones
        // forales del backend; este test deja la limitación por escrito.
        const bizkaiaGeneral = {
            territory: 'Bizkaia',
            resultado: 1250,
            tipo_aplicado: 5,
            regimen: 'general',
            casillas: {
                rend_neto_penultimo: 40000,
                retenciones_penultimo: 3000,
                base_calculo: 40000,
                pago_trimestral: 1250,
            },
        }
        const data = buildModelo130PdfData(bizkaiaGeneral, 'Bizkaia')
        expect(data.casillas).toEqual(bizkaiaGeneral.casillas)
        expect(data.resultado_final).toBe(1250)
        expect(data.regimen).toBe('general')
    })

    it('arrastra régimen y modalidad cuando el calculador los devuelve', () => {
        const bizkaia = buildModelo130PdfData(
            { ...API_RESULT_ARABA, regimen: 'general' },
            'Bizkaia',
        )
        expect(bizkaia.regimen).toBe('general')
        const navarra = buildModelo130PdfData(
            { ...API_RESULT_ARABA, modalidad: 'segunda' },
            'Navarra',
        )
        expect(navarra.modalidad).toBe('segunda')
    })
})

describe('buildModelo130PdfDataFromLocal — calculadora pública', () => {
    // La calculadora del cliente numera 05 = pagos y 06 = retenciones (AEAT),
    // justo al revés que las claves del calculador del backend.
    const LOCAL = {
        casilla01: 30000,
        casilla02: 10000,
        casilla03: 20000,
        casilla04: 4000,
        casilla05: 800, // pagos fraccionados anteriores
        casilla06: 500, // retenciones
        casilla07: 2700,
        casilla13: 100,
        casilla19: 2600,
        porcentaje: 0.2,
    }

    it('mapea a la forma del renderizador sin ceros', () => {
        const data = buildModelo130PdfDataFromLocal(LOCAL)
        expect(data.seccion_i).toEqual({
            ingresos_computables: 30000,
            gastos_deducibles: 10000,
            rendimiento_neto: 20000,
            veinte_porciento: 4000,
            retenciones: 500,
            pagos_anteriores: 800,
            resultado_seccion: 2700,
        })
        expect(data.deduccion_80bis).toBe(100)
        expect(data.resultado_final).toBe(2600)
    })

    it('convierte el tipo de tanto por uno a porcentaje', () => {
        expect(buildModelo130PdfDataFromLocal(LOCAL).tipo_aplicado).toBe(20)
        expect(buildModelo130PdfDataFromLocal({ ...LOCAL, porcentaje: 0.08 }).tipo_aplicado).toBe(8)
    })
})
