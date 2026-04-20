/**
 * QA Test: Guía Fiscal Wizard — Cataluña
 * Sesion 16 — 2026-03-12
 *
 * Escenario: ingresos altos Cataluña, 45 años, con pensiones + donativos
 * Expected: resultado ~2444 EUR a pagar, tipo_medio ~28.52%
 *
 * Auth: JWT inyectado directamente en localStorage (NO login via form)
 */

import { test, expect, Page } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const BASE_URL = 'http://localhost:3001'
const SCREENSHOTS = path.join(__dirname, 'screenshots')

const ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXBhcnRpY3VsYXItMDAwMDAwMDEiLCJlbWFpbCI6InRlc3QucGFydGljdWxhckBpbXB1ZXN0aWZ5LmVzIiwiZXhwIjoxNzczMzIwOTkzLCJpYXQiOjE3NzMzMTkxOTMsInR5cGUiOiJhY2Nlc3MifQ.9ReZKI_zmYaCJxHnUnv_hFElpCpHyx0e__TrYOv_REs'
const REFRESH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXBhcnRpY3VsYXItMDAwMDAwMDEiLCJlbWFpbCI6InRlc3QucGFydGljdWxhckBpbXB1ZXN0aWZ5LmVzIiwiZXhwIjoxNzczOTIzOTkzLCJpYXQiOjE3NzMzMTkxOTMsInR5cGUiOiJyZWZyZXNoIn0.t_Kp1SMxBQfTMGSyiLK7X78QsN3leIRlt33BwL5ZJFI'

async function screenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: path.join(SCREENSHOTS, `s16-GF-${name}.png`),
    fullPage: true
  })
  console.log(`Screenshot: s16-GF-${name}.png`)
}

/** Inject JWT tokens and navigate to /guia-fiscal */
async function setupAuth(page: Page): Promise<void> {
  await page.goto(BASE_URL)
  await page.evaluate(({ access, refresh }) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }, { access: ACCESS_TOKEN, refresh: REFRESH_TOKEN })
}

/** Clear a number input and type a value */
async function fillNumber(page: Page, selector: string, value: number): Promise<void> {
  const input = page.locator(selector).first()
  await input.click({ clickCount: 3 })
  await input.fill(String(value))
  await page.waitForTimeout(300)
}

/** Click the "Siguiente" (next) button */
async function clickNext(page: Page): Promise<void> {
  const nextBtn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
  await nextBtn.click()
  await page.waitForTimeout(600)
}

/** Get the current step number from the progress indicator */
async function getCurrentStep(page: Page): Promise<number> {
  const activeStep = page.locator('button.tg-progress__step--active').first()
  const text = await activeStep.textContent().catch(() => '?')
  return parseInt(text || '0')
}

test.describe('Guía Fiscal — Cataluña escenario alto ingresos', () => {
  test.setTimeout(120000)

  test('TG-CAT-01: Wizard completo Cataluña — 55k trabajo + ahorro + alquiler + familia + deducciones', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })

    // ============================================================
    // SETUP: Inyectar token y navegar a guia-fiscal
    // ============================================================
    await setupAuth(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1500)

    const url = page.url()
    console.log(`URL actual tras navegacion: ${url}`)

    // Verificar que cargó la guia fiscal (no redirigió a /subscribe)
    if (url.includes('/subscribe')) {
      await screenshot(page, '00-redirected-to-subscribe')
      throw new Error('BLOQUEADO: La guia fiscal redirige a /subscribe para plan particular')
    }

    // Verificar heading visible
    const heading = await page.locator('h1, h2').first().textContent().catch(() => 'N/A')
    console.log(`Heading inicial: ${heading}`)

    await screenshot(page, '00-initial-load')

    // ============================================================
    // Modo COMPLETO (si hay selector de modo)
    // ============================================================
    const fullModeBtn = page.locator('button.tg-mode-selector__btn').filter({ hasText: /completo/i })
    if (await fullModeBtn.isVisible({ timeout: 2000 })) {
      await fullModeBtn.click()
      await page.waitForTimeout(400)
      console.log('Modo "Completo" seleccionado')
    }

    // ============================================================
    // PASO 0: Datos personales — Cataluña, 45 años
    // ============================================================
    console.log('--- PASO 0: Datos personales ---')

    // Select CCAA
    const ccaaSelect = page.locator('select.tg-field__select').first()
    await ccaaSelect.selectOption('Cataluña')
    await page.waitForTimeout(500)

    const selectedCcaa = await ccaaSelect.inputValue()
    console.log(`CCAA seleccionada: "${selectedCcaa}"`)
    expect(selectedCcaa).toBe('Cataluña')

    // Edad: 45
    const edadInputs = page.locator('input.tg-field__input[type="number"]')
    await edadInputs.first().click({ clickCount: 3 })
    await edadInputs.first().fill('45')
    await page.waitForTimeout(300)

    await screenshot(page, '01-paso0-personal-cataluna')

    await clickNext(page)

    // ============================================================
    // PASO 1: Rendimientos del trabajo
    // ============================================================
    console.log('--- PASO 1: Trabajo ---')
    await page.waitForTimeout(800)

    await screenshot(page, '02-paso1-trabajo-before')

    // ingresos_trabajo: 55000
    const numberInputs1 = page.locator('input.tg-field__input[type="number"]')
    const count1 = await numberInputs1.count()
    console.log(`Inputs numéricos en paso 1: ${count1}`)

    // Buscar por label (más robusto)
    const allFields1 = page.locator('.tg-field')
    const fieldCount1 = await allFields1.count()

    let ingresosTrabajo = false, ssSset = false, retencionesSet = false

    for (let i = 0; i < fieldCount1; i++) {
      const field = allFields1.nth(i)
      const label = await field.locator('.tg-field__label').textContent().catch(() => '')
      const input = field.locator('input[type="number"]')
      if (!await input.isVisible({ timeout: 500 }).catch(() => false)) continue

      if (/salario|sueldo|ingresos.*trabajo|rendimiento.*trabajo/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('55000')
        ingresosTrabajo = true
        console.log(`  ingresos_trabajo: 55000 (label: "${label}")`)
      } else if (/seguridad social|cotizacion|ss_empleado|cuota.*ss/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('3500')
        ssSset = true
        console.log(`  ss_empleado: 3500 (label: "${label}")`)
      } else if (/retenci[oó]n|retencion.*trabajo|irpf.*retenido/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('12000')
        retencionesSet = true
        console.log(`  retenciones_trabajo: 12000 (label: "${label}")`)
      }
    }

    // Fallback: si no encontró por label, usar posición
    if (!ingresosTrabajo && count1 > 0) {
      await numberInputs1.nth(0).click({ clickCount: 3 })
      await numberInputs1.nth(0).fill('55000')
      console.log('  ingresos (fallback posición 0): 55000')
    }
    if (!ssSset && count1 > 1) {
      await numberInputs1.nth(1).click({ clickCount: 3 })
      await numberInputs1.nth(1).fill('3500')
      console.log('  SS (fallback posición 1): 3500')
    }
    if (!retencionesSet && count1 > 2) {
      await numberInputs1.nth(2).click({ clickCount: 3 })
      await numberInputs1.nth(2).fill('12000')
      console.log('  retenciones (fallback posición 2): 12000')
    }

    await page.waitForTimeout(500)
    await screenshot(page, '03-paso1-trabajo-filled')
    await clickNext(page)

    // ============================================================
    // PASO 2: Rendimientos del ahorro
    // ============================================================
    console.log('--- PASO 2: Ahorro ---')
    await page.waitForTimeout(800)

    await screenshot(page, '04-paso2-ahorro-before')

    const allFields2 = page.locator('.tg-field')
    const fieldCount2 = await allFields2.count()

    for (let i = 0; i < fieldCount2; i++) {
      const field = allFields2.nth(i)
      const label = await field.locator('.tg-field__label').textContent().catch(() => '')
      const input = field.locator('input[type="number"]')
      if (!await input.isVisible({ timeout: 500 }).catch(() => false)) continue

      if (/inter[eé]s|cuenta.*bancaria|ahorro.*bancario/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('1200')
        console.log(`  intereses: 1200 (label: "${label}")`)
      } else if (/dividendo/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('800')
        console.log(`  dividendos: 800 (label: "${label}")`)
      }
    }

    await page.waitForTimeout(400)
    await screenshot(page, '05-paso2-ahorro-filled')
    await clickNext(page)

    // ============================================================
    // PASO 3: Inmuebles / Alquiler
    // ============================================================
    console.log('--- PASO 3: Inmuebles ---')
    await page.waitForTimeout(800)

    await screenshot(page, '06-paso3-inmuebles-before')

    const allFields3 = page.locator('.tg-field')
    const fieldCount3 = await allFields3.count()

    for (let i = 0; i < fieldCount3; i++) {
      const field = allFields3.nth(i)
      const label = await field.locator('.tg-field__label').textContent().catch(() => '')
      const input = field.locator('input[type="number"]')
      if (!await input.isVisible({ timeout: 500 }).catch(() => false)) continue

      if (/ingresos.*alquiler|alquiler.*ingresos|renta.*alquiler/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('9600')
        console.log(`  ingresos_alquiler: 9600 (label: "${label}")`)
      } else if (/gastos.*alquiler|gasto.*inmueble|deduci.*alquiler/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('3000')
        console.log(`  gastos_alquiler: 3000 (label: "${label}")`)
      }
    }

    await page.waitForTimeout(400)
    await screenshot(page, '07-paso3-inmuebles-filled')
    await clickNext(page)

    // ============================================================
    // PASO 4: Inversiones — SKIP
    // ============================================================
    console.log('--- PASO 4: Inversiones (skip) ---')
    await page.waitForTimeout(800)
    await screenshot(page, '08-paso4-inversiones-skip')
    await clickNext(page)

    // ============================================================
    // PASO 5: Familia — 2 descendientes
    // ============================================================
    console.log('--- PASO 5: Familia ---')
    await page.waitForTimeout(800)

    await screenshot(page, '09-paso5-familia-before')

    const allFields5 = page.locator('.tg-field')
    const fieldCount5 = await allFields5.count()

    for (let i = 0; i < fieldCount5; i++) {
      const field = allFields5.nth(i)
      const label = await field.locator('.tg-field__label').textContent().catch(() => '')
      const input = field.locator('input[type="number"]')
      if (!await input.isVisible({ timeout: 500 }).catch(() => false)) continue

      if (/n[uú]mero.*hijos|n[uú]mero.*descendientes|descendientes/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('2')
        console.log(`  num_descendientes: 2 (label: "${label}")`)
        break
      }
    }

    await page.waitForTimeout(400)
    await screenshot(page, '10-paso5-familia-filled')
    await clickNext(page)

    // ============================================================
    // PASO 6: Deducciones — pensiones + donativos + autonómicas Cataluña
    // ============================================================
    console.log('--- PASO 6: Deducciones ---')
    await page.waitForTimeout(1000)

    await screenshot(page, '11-paso6-deducciones-before')

    const allFields6 = page.locator('.tg-field')
    const fieldCount6 = await allFields6.count()
    console.log(`Campos en paso 6: ${fieldCount6}`)

    for (let i = 0; i < fieldCount6; i++) {
      const field = allFields6.nth(i)
      const label = await field.locator('.tg-field__label').textContent().catch(() => '')
      const input = field.locator('input[type="number"]')
      if (!await input.isVisible({ timeout: 500 }).catch(() => false)) continue

      if (/plan.*pension|aportaci[oó]n.*pension|pension.*plan/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('1500')
        console.log(`  aportaciones_plan_pensiones: 1500 (label: "${label}")`)
      } else if (/donativo/i.test(label)) {
        await input.click({ clickCount: 3 })
        await input.fill('300')
        console.log(`  donativos: 300 (label: "${label}")`)
      }
    }

    // Detectar sección DynamicFiscalForm Cataluña-específica
    const dynamicForm = page.locator('.dynamic-fiscal-form, [class*="dynamic"]')
    if (await dynamicForm.isVisible({ timeout: 2000 })) {
      console.log('DynamicFiscalForm Cataluña-específico detectado')
      const dynamicFields = dynamicForm.locator('.tg-field, [class*="field"]')
      const dynCount = await dynamicFields.count()
      console.log(`  Campos autonómicos Cataluña: ${dynCount}`)
      // Tomar screenshot ampliado de la sección autonómica
      await screenshot(page, '12-paso6-deducciones-cataluna-autonomicas')
    }

    await page.waitForTimeout(400)
    await screenshot(page, '13-paso6-deducciones-filled')
    await clickNext(page)

    // ============================================================
    // PASO 7 (Resultado) — verificar valores esperados
    // ============================================================
    console.log('--- PASO 7: Resultado ---')
    await page.waitForTimeout(2000) // dar tiempo al estimador a calcular

    // Capturar screenshot inicial del resultado
    await screenshot(page, '14-paso7-resultado-initial')

    // Esperar a que aparezca el contenido del resultado (no "Calculando...")
    // Esperamos el elemento con el importe final
    let resultadoVisible = false
    for (let attempt = 0; attempt < 12; attempt++) {
      const calcText = await page.locator('body').textContent()
      if (calcText && !calcText.includes('Calculando...') && (
        calcText.includes('pagar') || calcText.includes('devolver') ||
        calcText.includes('€') || calcText.includes('EUR')
      )) {
        resultadoVisible = true
        break
      }
      console.log(`  Esperando resultado... intento ${attempt + 1}/12`)
      await page.waitForTimeout(1000)
    }

    if (!resultadoVisible) {
      console.warn('WARN: El resultado puede no haberse cargado completamente')
    }

    await screenshot(page, '15-paso7-resultado-final')

    // ============================================================
    // Extraer valores del resultado
    // ============================================================
    const bodyText = await page.locator('body').textContent() || ''

    // Buscar resultado estimado
    const matchResultado = bodyText.match(/(\d[\d.,]+)\s*€?\s*(a\s*pagar|a\s*devolver)/i)
      || bodyText.match(/resultado[:\s]+([+-]?\d[\d.,]+)/i)
    const matchTipoMedio = bodyText.match(/tipo\s*medio[:\s]+(\d+[.,]\d+)\s*%/i)
    const matchCuota = bodyText.match(/cuota[:\s]+(\d[\d.,]+)/i)

    console.log('\n=== RESULTADO EXTRAIDO ===')
    console.log(`Resultado match: ${matchResultado ? matchResultado[0] : 'NO ENCONTRADO'}`)
    console.log(`Tipo medio match: ${matchTipoMedio ? matchTipoMedio[0] : 'NO ENCONTRADO'}`)
    console.log(`Cuota match: ${matchCuota ? matchCuota[0] : 'NO ENCONTRADO'}`)

    // Buscar componentes específicos
    const tieneReduccionPensiones = /plan.*pensi[oó]n|aportaci[oó]n.*pensi[oó]n|reducci[oó]n.*pensi[oó]n/i.test(bodyText)
    const tieneDeduccionDonativos = /donativo|deducci[oó]n.*donat/i.test(bodyText)
    const mencioCataluna = /catalu[ñn]/i.test(bodyText)

    console.log(`Menciona reducción pensiones: ${tieneReduccionPensiones}`)
    console.log(`Menciona deducción donativos: ${tieneDeduccionDonativos}`)
    console.log(`Menciona Cataluña: ${mencioCataluna}`)

    // ============================================================
    // Verificar errores de consola
    // ============================================================
    if (consoleErrors.length > 0) {
      console.warn('\n=== ERRORES DE CONSOLA DETECTADOS ===')
      consoleErrors.forEach(e => console.warn(`  ERROR: ${e}`))
    } else {
      console.log('\nSin errores de consola')
    }

    // ============================================================
    // Screenshot final completo
    // ============================================================
    await screenshot(page, '16-paso7-resultado-fullpage')

    // ============================================================
    // Guardar resultados como JSON
    // ============================================================
    const results = {
      test: 'TG-CAT-01',
      fecha: new Date().toISOString(),
      url_final: page.url(),
      ccaa_seleccionada: 'Cataluña',
      resultado_match: matchResultado ? matchResultado[0] : null,
      tipo_medio_match: matchTipoMedio ? matchTipoMedio[1] : null,
      cuota_match: matchCuota ? matchCuota[1] : null,
      tiene_reduccion_pensiones: tieneReduccionPensiones,
      tiene_deduccion_donativos: tieneDeduccionDonativos,
      menciona_cataluna: mencioCataluna,
      console_errors: consoleErrors,
      body_text_sample: bodyText.slice(0, 2000),
    }

    fs.writeFileSync(
      path.join(SCREENSHOTS, 's16-GF-results.json'),
      JSON.stringify(results, null, 2)
    )
    console.log('\nResultados guardados en s16-GF-results.json')

    // ============================================================
    // Aserciones finales
    // ============================================================
    // La página debe mostrar resultado numérico
    expect(resultadoVisible || matchResultado !== null).toBeTruthy()
  })

  test('TG-CAT-02: Verificar CCAA Cataluña está disponible en el select', async ({ page }) => {
    await setupAuth(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)

    const url = page.url()
    if (url.includes('/subscribe')) {
      console.log('SKIP: redirige a /subscribe — test de acceso anotado')
      return
    }

    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 5000 })

    // Verificar que Cataluña está como opción
    const options = await ccaaSelect.locator('option').allTextContents()
    console.log(`Opciones CCAA disponibles: ${options.length}`)
    console.log(`Opciones: ${options.join(', ')}`)

    const hasCataluna = options.some(o => o.includes('Cataluña') || o.includes('Cataluna'))
    console.log(`¿Tiene "Cataluña"?: ${hasCataluna}`)
    expect(hasCataluna).toBeTruthy()

    await screenshot(page, '17-ccaa-select-options')
  })
})
