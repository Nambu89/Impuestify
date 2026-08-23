import { describe, it, expect } from 'vitest'
import { parseOptionalNumber, formatOptionalNumber, withOptionalField } from './numberField'

describe('parseOptionalNumber — tres estados', () => {
    it('campo vacío es "no facilitado", NO cero', () => {
        expect(parseOptionalNumber('')).toBeUndefined()
        expect(parseOptionalNumber('   ')).toBeUndefined()
    })

    it('un cero escrito por el usuario es un cero', () => {
        // Regresión del bug del Modelo 130: `parseFloat(x) || 0` devolvía 0
        // tanto para "" como para "0", y el backend, que sí los distingue,
        // aplicaba la minoración de 100 EUR/trimestre a quien no rellenaba nada.
        expect(parseOptionalNumber('0')).toBe(0)
        expect(parseOptionalNumber('0.00')).toBe(0)
    })

    it('cualquier otro número pasa tal cual', () => {
        expect(parseOptionalNumber('9000')).toBe(9000)
        expect(parseOptionalNumber('12.5')).toBe(12.5)
        expect(parseOptionalNumber('-300')).toBe(-300)
    })

    it('lo que no es un número finito es "no facilitado", no cero', () => {
        // `parseFloat('')` da NaN y `NaN || 0` da 0: ese es el colapso a evitar.
        expect(parseOptionalNumber('abc')).toBeUndefined()
        expect(parseOptionalNumber('Infinity')).toBeUndefined()
    })
})

describe('formatOptionalNumber', () => {
    it('muestra el cero explícito en pantalla', () => {
        // `value || ''` lo borraba mientras se escribía.
        expect(formatOptionalNumber(0)).toBe('0')
    })

    it('deja el campo vacío cuando no hay dato', () => {
        expect(formatOptionalNumber(undefined)).toBe('')
        expect(formatOptionalNumber(null)).toBe('')
        expect(formatOptionalNumber(NaN)).toBe('')
    })

    it('muestra el resto de valores', () => {
        expect(formatOptionalNumber(9000)).toBe('9000')
        expect(formatOptionalNumber(12.5)).toBe('12.5')
    })
})

describe('withOptionalField', () => {
    it('elimina la clave cuando el valor no está facilitado', () => {
        const next = withOptionalField(
            { rend_neto_anterior: 8000, quarter: 2 },
            'rend_neto_anterior',
            undefined,
        )
        expect('rend_neto_anterior' in next).toBe(false)
        expect(next.quarter).toBe(2)
    })

    it('conserva el cero explícito', () => {
        const next = withOptionalField(
            { rend_neto_anterior: undefined as number | undefined },
            'rend_neto_anterior',
            0,
        )
        expect(next.rend_neto_anterior).toBe(0)
        expect('rend_neto_anterior' in next).toBe(true)
    })

    it('la clave omitida no viaja en el JSON del payload', () => {
        const omitido = withOptionalField(
            { rend_neto_anterior: 5 },
            'rend_neto_anterior',
            undefined,
        )
        const explicito = withOptionalField({ rend_neto_anterior: 5 }, 'rend_neto_anterior', 0)
        expect(JSON.parse(JSON.stringify(omitido))).toEqual({})
        expect(JSON.parse(JSON.stringify(explicito))).toEqual({ rend_neto_anterior: 0 })
    })

    it('no muta el objeto original', () => {
        const original = { rend_neto_anterior: 8000 }
        withOptionalField(original, 'rend_neto_anterior', undefined)
        expect(original.rend_neto_anterior).toBe(8000)
    })
})
