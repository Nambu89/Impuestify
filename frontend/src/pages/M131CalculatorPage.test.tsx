import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import M131CalculatorPage from './M131CalculatorPage'
import type { M131Input, M131Result } from '../hooks/useM131'

const calculateMock = vi.fn<(input: M131Input) => Promise<void>>()
const hookState = {
    result: null as M131Result | null,
    loading: false,
    error: null as string | null,
    calculate: calculateMock,
    reset: vi.fn(),
}

vi.mock('../hooks/useM131', () => ({
    useM131: () => hookState,
}))

vi.mock('../hooks/useModeloPDF', () => ({
    useModeloPDF: () => ({ downloadPDF: vi.fn(), isLoading: false, error: null }),
}))

vi.mock('../components/Header', () => ({ default: () => null }))

/**
 * Apartado I, 18.000 EUR de rendimiento neto y ningun asalariado.
 * tipo_aplicado = 2 (YA en porcentaje, no 0,02) y minoracion de 100 EUR
 * porque el ejercicio anterior quedo por debajo de 9.000 EUR.
 */
const resultApartadoI: M131Result = {
    success: true,
    trimestre: 1,
    apartado: 'I',
    actividad_tipo: 'empresarial',
    territory: 'Comun',
    tipo_aplicado: 2,
    casillas: {
        '01_rendimiento_neto_modulos': 18000,
        '02_tipo_aplicable': 2,
        '03_resultado_empresarial': 360,
        '04_volumen_ingresos_agrario': 0,
        '05_cuota_agraria': 0,
        '06_total_cuotas': 360,
        '07_reducciones': 0,
        '08_resultado_tras_reducciones': 360,
        '09_retenciones_trimestre': 50,
        '10_pagos_anteriores': 0,
        '11_complementaria': 0,
        '12_resultado_final': 210,
    },
    desglose: {
        tipo_pct: 2,
        criterio_tipo: 'Sin asalariados',
        reduccion_pct: 0,
        reduccion_concepto: 'Sin reducción',
        minoracion_rendimientos_bajos: 100,
        rendimiento_neto_anterior: 8000,
    },
    resultado_final: 210,
    plazo: '1 al 20 de abril',
}

function renderPage() {
    return render(
        <MemoryRouter>
            <M131CalculatorPage />
        </MemoryRouter>,
    )
}

describe('M131CalculatorPage — resultado', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        hookState.result = resultApartadoI
        hookState.loading = false
        hookState.error = null
    })

    it('muestra el tipo como 2%, no como 200%', () => {
        const { container } = renderPage()
        const sub = container.querySelector('.m130-result-sub')
        expect(sub?.textContent).toContain('Tipo: 2%')
        expect(sub?.textContent).not.toContain('200%')
    })

    it('la tabla usa el numero y el concepto oficiales, no la clave del dict', () => {
        renderPage()
        // Concepto oficial en la columna de descripcion...
        expect(screen.getByText('Suma de rendimientos netos')).toBeInTheDocument()
        expect(screen.getByText('A deducir: retenciones e ingresos a cuenta')).toBeInTheDocument()
        expect(screen.getByText('Resultado de la declaración')).toBeInTheDocument()
        // ...y ni rastro de la clave cruda, que antes salia en las dos columnas.
        expect(screen.queryByText('09_retenciones_trimestre')).not.toBeInTheDocument()
        expect(screen.queryByText('12_resultado_final')).not.toBeInTheDocument()
    })

    it('numera el resultado como [15] y nunca como [12]', () => {
        const { container } = renderPage()
        const filas = Array.from(container.querySelectorAll('.m130-casilla-row'))
        const filaResultado = filas.find((tr) =>
            tr.textContent?.includes('Resultado de la declaración'),
        )
        expect(filaResultado?.querySelector('.m130-casilla-num')?.textContent).toBe('15')
        // [12] en el modelo oficial es "Pago de prestamos para la adquisicion
        // de vivienda habitual": etiquetar ahi el importe a ingresar seria
        // llamar al pago por el nombre de una deduccion.
        const nums = filas.map((tr) => tr.querySelector('.m130-casilla-num')?.textContent)
        expect(nums).not.toContain('12')
    })

    it('el porcentaje aplicable se imprime en % y los importes en EUR', () => {
        const { container } = renderPage()
        const filas = Array.from(container.querySelectorAll('.m130-casilla-row'))
        const filaTipo = filas.find((tr) => tr.textContent?.includes('Porcentaje aplicable'))
        expect(filaTipo?.querySelector('.m130-casilla-value')?.textContent).toBe('2%')
        const filaSuma = filas.find((tr) => tr.textContent?.includes('Suma de rendimientos netos'))
        expect(filaSuma?.querySelector('.m130-casilla-value')?.textContent).toBe('18.000,00 EUR')
    })

    it('muestra la minoracion del art. 110.3.c como casilla [09]', () => {
        const { container } = renderPage()
        const filas = Array.from(container.querySelectorAll('.m130-casilla-row'))
        const filaMin = filas.find((tr) => tr.textContent?.includes('art. 110.3.c'))
        expect(filaMin?.querySelector('.m130-casilla-num')?.textContent).toBe('09')
        expect(filaMin?.querySelector('.m130-casilla-value')?.textContent).toBe('100,00 EUR')
    })
})

function casillasBase(): Record<string, number> {
    return {
        '01_rendimiento_neto_modulos': 0,
        '02_tipo_aplicable': 0,
        '03_resultado_empresarial': 0,
        '04_volumen_ingresos_agrario': 0,
        '05_cuota_agraria': 0,
        '06_total_cuotas': 0,
        '07_reducciones': 0,
        '08_resultado_tras_reducciones': 0,
        '09_retenciones_trimestre': 0,
        '10_pagos_anteriores': 0,
        '11_complementaria': 0,
        '12_resultado_final': 0,
    }
}

/** Devuelve [numero de casilla, concepto] de cada fila de la tabla. */
function filasDe(container: HTMLElement): Array<[string, string]> {
    return Array.from(container.querySelectorAll('.m130-casilla-row')).map((tr) => [
        tr.querySelector('.m130-casilla-num')?.textContent ?? '',
        tr.querySelector('.m130-casilla-label')?.textContent ?? '',
    ])
}

describe('M131CalculatorPage — numeracion de los apartados II y III', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        hookState.loading = false
        hookState.error = null
    })

    it('apartado II: volumen es [03] y el pago fraccionado previo [04]', () => {
        hookState.result = {
            ...resultApartadoI,
            apartado: 'II',
            actividad_tipo: 'sin_datos_base',
            casillas: {
                ...casillasBase(),
                '01_rendimiento_neto_modulos': 12000,
                '02_tipo_aplicable': 2,
                '03_resultado_empresarial': 240,
                '06_total_cuotas': 240,
                '12_resultado_final': 240,
            },
            desglose: {},
            resultado_final: 240,
        }
        const { container } = renderPage()
        const filas = filasDe(container)
        expect(filas).toContainEqual(['03', 'Volumen de ventas o ingresos'])
        expect(filas).toContainEqual(['04', 'Pago fraccionado previo'])
        expect(filas).toContainEqual(['07', 'Suma de los pagos fraccionados previos del trimestre'])
        expect(filas).toContainEqual(['15', 'Resultado de la declaración'])
    })

    it('apartado III: volumen es [05], pago fraccionado [06] y no hay fila de porcentaje', () => {
        hookState.result = {
            ...resultApartadoI,
            apartado: 'III',
            actividad_tipo: 'agraria',
            casillas: {
                ...casillasBase(),
                '04_volumen_ingresos_agrario': 10000,
                '05_cuota_agraria': 200,
                '06_total_cuotas': 200,
                '12_resultado_final': 200,
            },
            desglose: {},
            resultado_final: 200,
        }
        const { container } = renderPage()
        const filas = filasDe(container)
        expect(filas).toContainEqual(['05', 'Volumen de ingresos del trimestre'])
        expect(filas).toContainEqual(['06', 'Pago fraccionado previo del trimestre (2%)'])
        expect(filas).toContainEqual(['15', 'Resultado de la declaración'])
        // `02_tipo_aplicable` vale 0 en este apartado: pintarlo daria un "0%"
        // que contradice el 2% de la propia etiqueta de [06].
        expect(filas.map(([, concepto]) => concepto)).not.toContain('Porcentaje aplicable')
    })

    it('la minoracion del art. 110.3.c no se ofrece fuera del apartado I', () => {
        hookState.result = {
            ...resultApartadoI,
            apartado: 'III',
            actividad_tipo: 'agraria',
            casillas: { ...casillasBase(), '04_volumen_ingresos_agrario': 10000 },
            desglose: { minoracion_rendimientos_bajos: 100 },
        }
        const { container } = renderPage()
        expect(
            filasDe(container)
                .map(([, c]) => c)
                .join(' | '),
        ).not.toContain('110.3.c')
    })
})

describe('M131CalculatorPage — lo que se envia al backend', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        hookState.result = null
        hookState.loading = false
        hookState.error = null
    })

    it('el apartado II pide su base y la envia (antes calculaba siempre 0)', async () => {
        const user = userEvent.setup()
        renderPage()
        await user.selectOptions(screen.getByLabelText('Apartado'), 'sin_datos_base')

        const campo = screen.getByLabelText(/Volumen de ventas o ingresos del trimestre/i)
        await user.type(campo, '9000')
        await user.click(screen.getByRole('button', { name: /Calcular Modelo 131/i }))

        expect(calculateMock.mock.calls[0][0].volumen_ingresos_trimestre).toBe(9000)
    })

    it('en el 1T no se envian pagos de trimestres anteriores aunque quede el importe', async () => {
        const user = userEvent.setup()
        renderPage()
        // El campo solo se habilita fuera del 1T: se teclea en el 3T...
        await user.click(screen.getByRole('button', { name: /3T/ }))
        await user.type(screen.getByLabelText(/Pagos fraccionados anteriores/i), '400')
        // ...y se vuelve al 1T, donde el control se deshabilita pero conserva
        // el valor. En el 1T no hay trimestres anteriores que restar.
        await user.click(screen.getByRole('button', { name: /1T/ }))
        await user.click(screen.getByRole('button', { name: /Calcular Modelo 131/i }))

        const payload = calculateMock.mock.calls[0][0]
        expect(payload.trimestre).toBe(1)
        expect(payload.pagos_anteriores).toBe(0)
    })

    it('fuera del 1T los pagos anteriores si viajan', async () => {
        const user = userEvent.setup()
        renderPage()
        await user.click(screen.getByRole('button', { name: /3T/ }))
        await user.type(screen.getByLabelText(/Pagos fraccionados anteriores/i), '400')
        await user.click(screen.getByRole('button', { name: /Calcular Modelo 131/i }))

        expect(calculateMock.mock.calls[0][0].pagos_anteriores).toBe(400)
    })
})

describe('M131CalculatorPage — rendimiento del ejercicio anterior (tres estados)', () => {
    beforeEach(() => {
        calculateMock.mockReset()
        hookState.result = null
        hookState.loading = false
        hookState.error = null
    })

    async function submitCon(valor: string | null) {
        const user = userEvent.setup()
        renderPage()
        if (valor !== null) {
            const campo = screen.getByLabelText(/Rendimiento neto del ejercicio anterior/i)
            await user.clear(campo)
            await user.type(campo, valor)
        }
        await user.click(screen.getByRole('button', { name: /Calcular Modelo 131/i }))
        expect(calculateMock).toHaveBeenCalledTimes(1)
        return calculateMock.mock.calls[0][0]
    }

    it('vacio: OMITE la clave del payload (no la manda como 0 ni como null)', async () => {
        const payload = await submitCon(null)
        expect('rendimiento_neto_anterior' in payload).toBe(false)
    })

    it('un 0 escrito por el usuario viaja como 0, y da derecho a la minoracion', async () => {
        const payload = await submitCon('0')
        expect(payload.rendimiento_neto_anterior).toBe(0)
    })

    it('un importe cualquiera viaja tal cual', async () => {
        const payload = await submitCon('8500')
        expect(payload.rendimiento_neto_anterior).toBe(8500)
    })

    it('un importe con decimales sobrevive al tecleo (12.5, no 125)', async () => {
        const payload = await submitCon('12.5')
        expect(payload.rendimiento_neto_anterior).toBe(12.5)
    })

    it('un ejercicio anterior en perdidas viaja negativo y entra en el primer tramo', async () => {
        // Escribir el signo menos deja un estado intermedio invalido para
        // `<input type=number>`; el importe final no puede salir como 300.
        const payload = await submitCon('-300')
        expect(payload.rendimiento_neto_anterior).toBe(-300)
    })

    it('avisa en pantalla de que un 0 explicito aplica la minoracion maxima', async () => {
        const user = userEvent.setup()
        renderPage()
        const campo = screen.getByLabelText(/Rendimiento neto del ejercicio anterior/i)
        await user.type(campo, '0')
        expect(screen.getByText(/se aplicará la minoración/i)).toBeInTheDocument()
    })
})
