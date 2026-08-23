/**
 * Tests del CABLEADO de la página de Modelos Trimestrales.
 *
 * Los tests de `src/utils/modelo130Pdf.test.ts` prueban el adaptador; estos
 * prueban que la página lo usa. Sin ellos, la página podría volver a mandar el
 * resultado en crudo (el bug del PDF con todo a cero) o a convertir el campo
 * vacío en un 0 (el bug de los 100 EUR/trimestre regalados) y los tests de
 * utilidades seguirían en verde.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

const calculateMock = vi.fn()
const downloadPDFMock = vi.fn()
const resetMock = vi.fn()

const calcState = {
    calcResult: null as { success: boolean; result: Record<string, unknown> } | null,
    declarations: [],
    projection: null,
    loading: false,
    saving: false,
    error: null,
    calculate: calculateMock,
    save: vi.fn(),
    loadYear: vi.fn(),
    projectIrpf: vi.fn(),
    deleteDeclaration: vi.fn(),
    reset: resetMock,
}

vi.mock('../hooks/useDeclarations', () => ({
    useDeclarations: () => calcState,
}))
vi.mock('../hooks/useModeloPDF', () => ({
    useModeloPDF: () => ({ downloadPDF: downloadPDFMock, isLoading: false, error: null }),
}))
vi.mock('../hooks/useFiscalProfile', () => ({
    useFiscalProfile: () => ({ profile: null, loading: false, error: null }),
}))
vi.mock('../components/Header', () => ({ default: () => <div /> }))
vi.mock('../components/reactbits/CountUp', () => ({
    default: ({ to }: { to: number }) => <span>{to}</span>,
}))

import DeclarationsPage from './DeclarationsPage'

/** Resultado real de `POST /api/declarations/130/calculate` (Territorio Común). */
const RESULT_130_COMUN = {
    territory: 'Comun',
    quarter: 1,
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
        '13_deduccion_art80bis': 100,
        '19_resultado_final': 2600,
    },
}

/** El `<label>` no lleva `htmlFor`, así que hay que buscar por el contenedor. */
function fieldInput(label: string): HTMLInputElement {
    const field = Array.from(document.querySelectorAll('.decl-field')).find(
        (el) => el.querySelector('.decl-field__label')?.textContent === label,
    )
    if (!field) throw new Error(`No existe el campo "${label}"`)
    const input = field.querySelector('input')
    if (!input) throw new Error(`El campo "${label}" no tiene input`)
    return input as HTMLInputElement
}

/** Por `aria-label`, no por posición: el orden de los `<select>` es incidental. */
function territorySelect(): HTMLSelectElement {
    return screen.getByLabelText('Territorio del Modelo 130') as HTMLSelectElement
}

function lastCalculate130(): Record<string, unknown> {
    const call = [...calculateMock.mock.calls].reverse().find(([modelo]) => modelo === '130')
    if (!call) throw new Error('No se ha llamado a calculate("130", ...)')
    return call[1] as Record<string, unknown>
}

async function renderOn130() {
    const user = userEvent.setup()
    render(
        <MemoryRouter>
            <DeclarationsPage />
        </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /130 IRPF/i }))
    return user
}

describe('DeclarationsPage — rend_neto_anterior conserva los tres estados', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        downloadPDFMock.mockReset()
        calcState.calcResult = null
    })

    it('campo vacío: la clave NO viaja en el payload', async () => {
        const user = await renderOn130()
        await user.type(fieldInput('Ingresos acumulados'), '30000')

        const payload = lastCalculate130()
        // Ni presente ni como 0: si viajara un 0, el backend aplicaría los
        // 100 EUR/trimestre del primer tramo del art. 110.3.c) RIRPF.
        expect(payload).not.toHaveProperty('rend_neto_anterior')
        expect(JSON.parse(JSON.stringify(payload))).not.toHaveProperty('rend_neto_anterior')
    })

    it('cero escrito por el usuario: viaja como 0', async () => {
        const user = await renderOn130()
        await user.type(fieldInput('Ingresos acumulados'), '30000')
        await user.type(fieldInput('Rend. neto año anterior'), '0')

        expect(lastCalculate130().rend_neto_anterior).toBe(0)
        // Y se ve en pantalla (el viejo `value || ''` lo borraba al teclearlo).
        expect(fieldInput('Rend. neto año anterior').value).toBe('0')
    })

    it('un importe normal viaja tal cual', async () => {
        const user = await renderOn130()
        await user.type(fieldInput('Ingresos acumulados'), '30000')
        await user.type(fieldInput('Rend. neto año anterior'), '8000')

        expect(lastCalculate130().rend_neto_anterior).toBe(8000)
    })

    it('borrar el campo vuelve a "no facilitado", no a cero', async () => {
        const user = await renderOn130()
        await user.type(fieldInput('Ingresos acumulados'), '30000')
        await user.type(fieldInput('Rend. neto año anterior'), '8000')
        await user.clear(fieldInput('Rend. neto año anterior'))

        expect(lastCalculate130()).not.toHaveProperty('rend_neto_anterior')
    })
})

describe('DeclarationsPage — % atribución Estado y años de actividad', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        downloadPDFMock.mockReset()
        calcState.calcResult = null
    })

    it('vaciar el % de atribución NO manda 0 (el defecto del backend es 100)', async () => {
        const user = userEvent.setup()
        render(
            <MemoryRouter>
                <DeclarationsPage />
            </MemoryRouter>,
        )
        await user.type(fieldInput('Base imponible 21%'), '1000')
        await user.clear(fieldInput('% Atribucion Estado'))

        const call = [...calculateMock.mock.calls].reverse().find(([modelo]) => modelo === '303')
        expect(call, 'no se ha llamado a calculate("303", ...)').toBeTruthy()
        expect(call![1]).not.toHaveProperty('pct_atribucion_estado')
    })

    it('vaciar los años de actividad NO manda 0 (el defecto del backend es 3)', async () => {
        const user = await renderOn130()
        await user.selectOptions(territorySelect(), 'Bizkaia')
        await user.type(fieldInput('Rend. neto penultimo ano'), '25000')
        await user.clear(fieldInput('Años de actividad'))

        expect(lastCalculate130()).not.toHaveProperty('anos_actividad')
    })
})

describe('DeclarationsPage — payload del PDF del Modelo 130', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        downloadPDFMock.mockReset()
        calcState.calcResult = { success: true, result: RESULT_130_COMUN }
    })

    it('manda la forma que lee _render_130, no el resultado en crudo', async () => {
        const user = await renderOn130()
        await user.click(screen.getByRole('button', { name: /Descargar PDF/i }))

        expect(downloadPDFMock).toHaveBeenCalledTimes(1)
        const [modelo, data] = downloadPDFMock.mock.calls[0]
        expect(modelo).toBe('130')
        expect(data).toHaveProperty('seccion_i')
        expect(data).toHaveProperty('deduccion_80bis', 100)
        expect(data).toHaveProperty('resultado_final', 2600)
        // El bug: se enviaba `{...form130, ...result}`, sin `seccion_i`.
        expect(data).not.toHaveProperty('casillas')
        expect(data.seccion_i).toEqual({
            ingresos_computables: 30000,
            gastos_deducibles: 10000,
            rendimiento_neto: 20000,
            veinte_porciento: 4000,
            retenciones: 500,
            pagos_anteriores: 800,
            resultado_seccion: 2700,
        })
    })

    it('en territorio foral manda variante_foral en data Y en contribuyente', async () => {
        calcState.calcResult = {
            success: true,
            result: {
                territory: 'Araba',
                resultado: 350,
                tipo_aplicado: 5,
                casillas: { '01_ingresos_trimestre': 12000, '07_resultado': 350 },
            },
        }
        const user = await renderOn130()
        await user.selectOptions(territorySelect(), 'Araba')
        await user.click(screen.getByRole('button', { name: /Descargar PDF/i }))

        const calls = downloadPDFMock.mock.calls
        const [, data, , , contribuyente] = calls[calls.length - 1]
        // El cuerpo del modelo lo lee de `data`...
        expect(data.variante_foral).toBe('130-araba')
        expect(data.resultado_final).toBe(350)
        // ...y la cabecera del PDF, de `contribuyente`.
        expect(contribuyente).toEqual({ variante_foral: '130-araba' })
    })

    it('cambiar de territorio descarta el resultado anterior', async () => {
        // El territorio decide la FORMA del payload (común vs foral). Si el
        // resultado viejo sobrevive al cambio, en la ventana del debounce se
        // descarga un cálculo común etiquetado como foral: cifras verosímiles
        // pero equivocadas, que es peor que un PDF vacío.
        const user = await renderOn130()
        resetMock.mockClear()
        await user.selectOptions(territorySelect(), 'Araba')

        expect(resetMock).toHaveBeenCalled()
    })

    it('en territorio común no manda variante_foral', async () => {
        const user = await renderOn130()
        await user.click(screen.getByRole('button', { name: /Descargar PDF/i }))

        const [, data, , , contribuyente] = downloadPDFMock.mock.calls[0]
        expect(data).not.toHaveProperty('variante_foral')
        expect(contribuyente).toBeUndefined()
    })
})
