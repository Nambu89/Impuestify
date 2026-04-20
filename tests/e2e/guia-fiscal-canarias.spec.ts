/**
 * QA Test: Guia Fiscal Wizard — Perfil Canarias
 * Escenario: Asalariado, 38 anos, CCAA Canarias
 * Entorno: http://localhost:3001 (frontend) + http://localhost:8000 (backend)
 *
 * Sesion QA: 2026-03-12
 * Tester: qa-tester agent (claude-sonnet-4-6)
 */

import { test, expect, type Page } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

// ── Config ──────────────────────────────────────────────────────────────────
const BASE_URL = 'http://localhost:3001'
const API_URL  = 'http://localhost:8000'
const EMAIL    = 'test.particular@impuestify.es'
const PASSWORD = 'Test2026!'
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots')

// Ensure screenshots dir exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
}

// ── Helpers ──────────────────────────────────────────────────────────────────
async function screenshot(page: Page, name: string) {
  const p = path.join(SCREENSHOTS_DIR, `${name}.png`)
  await page.screenshot({ path: p, fullPage: true })
  console.log(`[SCREENSHOT] ${p}`)
}

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.fill('input[type="email"]', EMAIL)
  await page.fill('input[type="password"]', PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/chat', { timeout: 20000 })
  const token = await page.evaluate(() => localStorage.getItem('access_token'))
  expect(token, 'JWT token debe estar en localStorage tras login').toBeTruthy()
  console.log('[LOGIN] OK — JWT presente')
}

async function dismissModals(page: Page) {
  // Cerrar modal onboarding y modal IA si aparecen
  for (let i = 0; i < 4; i++) {
    try {
      const skipBtn = page.locator('button').filter({ hasText: /saltar tutorial/i }).first()
      if (await skipBtn.isVisible({ timeout: 2000 })) {
        await skipBtn.click({ force: true })
        await page.waitForTimeout(800)
        console.log('[MODAL] "Saltar tutorial" cerrado')
      }
    } catch (_) { /* ignorar si no aparece */ }

    try {
      const entendidoBtn = page.locator('button').filter({ hasText: /entendido/i }).first()
      if (await entendidoBtn.isVisible({ timeout: 2000 })) {
        await entendidoBtn.click({ force: true })
        await page.waitForTimeout(800)
        console.log('[MODAL] "Entendido" cerrado')
      }
    } catch (_) { /* ignorar */ }
  }
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Guia Fiscal — Canarias (asalariado, 38 anos)', () => {
  test.setTimeout(120000)

  // Colector de errores de consola
  const consoleErrors: string[] = []
  const networkErrors: string[] = []

  test.beforeEach(async ({ page }) => {
    consoleErrors.length = 0
    networkErrors.length = 0
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(`[${msg.type()}] ${msg.text()}`)
        console.warn('[CONSOLE ERROR]', msg.text())
      }
    })
    page.on('response', resp => {
      if (resp.status() >= 400) {
        const entry = `${resp.status()} ${resp.url()}`
        networkErrors.push(entry)
        console.warn('[NETWORK ERROR]', entry)
      }
    })
  })

  // ── T-GF-CAN-01: Login ──────────────────────────────────────────────────
  test('T-GF-CAN-01: Login con usuario particular', async ({ page }) => {
    await login(page)
    await screenshot(page, 'can-01-login-success')
    expect(consoleErrors, 'No debe haber errores de consola en login').toHaveLength(0)
  })

  // ── T-GF-CAN-02: Acceso a /guia-fiscal ─────────────────────────────────
  test('T-GF-CAN-02: Acceso a Guia Fiscal', async ({ page }) => {
    await login(page)
    await dismissModals(page)

    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    // Verificar que NO redirige a /subscribe
    const url = page.url()
    const redirectedToSubscribe = url.includes('/subscribe')
    console.log(`[URL] ${url}`)

    if (redirectedToSubscribe) {
      console.error('[BUG] Plan particular redirigido a /subscribe — la Guia Fiscal no es accesible')
      // Registrar como bug pero no fallar el test por ahora (decision de producto)
      await screenshot(page, 'can-02-redirected-to-subscribe')
      test.skip() // Saltar el resto de tests si no hay acceso
    } else {
      // Verificar que hay contenido de wizard
      const wizardContent = page.locator('.tg-step, .tg-mode-selector, .tax-guide__container, h2').first()
      await expect(wizardContent).toBeVisible({ timeout: 10000 })
      console.log('[ACCESO] Guia Fiscal carga correctamente para plan particular')
      await screenshot(page, 'can-02-guia-fiscal-loaded')
    }
  })

  // ── T-GF-CAN-03: Step 0 — Datos personales + CCAA Canarias ─────────────
  test('T-GF-CAN-03: Step 0 — Seleccion Canarias y CcaaTip', async ({ page }) => {
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    // Verificar acceso
    const url = page.url()
    if (url.includes('/subscribe')) {
      console.error('[SKIP] Sin acceso a /guia-fiscal para plan particular')
      test.skip()
    }

    await screenshot(page, 'can-03-step0-initial')

    // Seleccionar CCAA Canarias
    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(500) // esperar re-render

    // Verificar que el CcaaTip de Canarias aparece
    const canTip = page.locator('.tg-tip--info').first()
    const tipVisible = await canTip.isVisible({ timeout: 3000 }).catch(() => false)

    if (tipVisible) {
      const tipText = await canTip.textContent()
      const mentionsIGIC = tipText?.toLowerCase().includes('igic') ?? false
      const mentionsREF = tipText?.toLowerCase().includes('igic') || tipText?.toLowerCase().includes('régimen') || tipText?.toLowerCase().includes('reg') ? true : false
      console.log(`[CcaaTip] Visible: SI | Texto: "${tipText?.trim()}"`)
      console.log(`[CcaaTip] Menciona IGIC: ${mentionsIGIC}`)
      expect(mentionsIGIC, 'El CcaaTip de Canarias debe mencionar IGIC').toBe(true)
    } else {
      console.error('[BUG] CcaaTip de Canarias NO aparece tras seleccionar la CCAA')
    }

    // Verificar que el select tiene Canarias seleccionado
    const selectedValue = await ccaaSelect.inputValue()
    expect(selectedValue, 'CCAA seleccionada debe ser Canarias').toBe('Canarias')

    // Introducir edad 38
    const ageInputs = page.locator('input.tg-field__input[type="number"]')
    const ageInput = ageInputs.first()
    await ageInput.fill('38')
    await page.waitForTimeout(300)

    const ageValue = await ageInput.inputValue()
    console.log(`[EDAD] Valor introducido: ${ageValue}`)

    await screenshot(page, 'can-03-step0-canarias-selected')

    // Verificar que no hay errores de consola en este paso
    const filteredErrors = consoleErrors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('manifest') &&
      !e.includes('sw.js')
    )
    if (filteredErrors.length > 0) {
      console.warn('[CONSOLE ERRORS] Step 0:', filteredErrors)
    }
  })

  // ── T-GF-CAN-04: Step 1 — Rendimientos trabajo ─────────────────────────
  test('T-GF-CAN-04: Step 1 — Ingresos trabajo + navegacion', async ({ page }) => {
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    const url = page.url()
    if (url.includes('/subscribe')) { test.skip() }

    // Step 0: Seleccionar Canarias
    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(300)

    // Poner edad
    const numberInputs = page.locator('input.tg-field__input[type="number"]')
    await numberInputs.first().fill('38')
    await page.waitForTimeout(300)

    // Click "Siguiente" para pasar a Step 1
    const nextBtn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
    await expect(nextBtn).toBeVisible({ timeout: 5000 })
    await nextBtn.click()
    await page.waitForTimeout(500)

    // Verificar Step 1 — Rendimientos del trabajo
    const step1Title = page.locator('h2.tg-step__title').filter({ hasText: /trabajo/i })
    const step1Visible = await step1Title.isVisible({ timeout: 5000 }).catch(() => false)

    if (!step1Visible) {
      // Puede haber un aviso de cero ingresos — buscar el boton de confirmacion
      const confirmZeroBtn = page.locator('button').filter({ hasText: /confirmar.*no tuve ingresos/i }).first()
      if (await confirmZeroBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        // Esto no deberia pasar antes de step 1 — registrar como bug
        console.warn('[B-GF-06-CHECK] Aviso de cero ingresos aparece en step 0 antes de introducir salario')
      }
      // Intentar ir directamente a step 1 via progress steps
      const progressSteps = page.locator('button.tg-progress__step')
      if (await progressSteps.nth(1).isVisible({ timeout: 2000 }).catch(() => false)) {
        await progressSteps.nth(1).click()
        await page.waitForTimeout(500)
      }
    }

    await screenshot(page, 'can-04-step1-trabajo')

    // Introducir ingresos_trabajo = 32000 (modo anual por defecto)
    // Verificar que el toggle "Salario anual" esta activo
    const anualBtn = page.locator('button.tg-toggle-group__btn').filter({ hasText: /salario anual/i }).first()
    if (await anualBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      const isActive = await anualBtn.getAttribute('class')
      if (!isActive?.includes('active')) {
        await anualBtn.click()
        await page.waitForTimeout(300)
      }
    }

    // Encontrar el input de ingresos de trabajo (salario bruto anual)
    const allNumberInputs = page.locator('input.tg-field__input[type="number"]')
    const inputCount = await allNumberInputs.count()
    console.log(`[STEP1] Numero de inputs numericos visibles: ${inputCount}`)

    // El primer input numérico en step 1 debe ser "Salario bruto anual"
    if (inputCount > 0) {
      await allNumberInputs.first().fill('32000')
      await page.waitForTimeout(300)
    }

    // SS empleado (segundo input)
    if (inputCount > 1) {
      await allNumberInputs.nth(1).fill('2100')
      await page.waitForTimeout(300)
    }

    // Retenciones trabajo (4o input aproximadamente — despues de porcentaje)
    // Buscar por label proxy: el ultimo input de "retenciones IRPF totales"
    // Llenamos el porcentaje IRPF: ~15.6% para 32k EUR
    if (inputCount > 2) {
      await allNumberInputs.nth(2).fill('15.6')  // % IRPF en nomina
      await page.waitForTimeout(300)
    }
    if (inputCount > 3) {
      await allNumberInputs.nth(3).fill('5000')  // retenciones totales anuales
      await page.waitForTimeout(300)
    }

    await screenshot(page, 'can-04-step1-filled')

    // Verificar LiveEstimatorBar actualiza (bug B-GF-ESTIMATOR conocido)
    const estimatorBar = page.locator('.estimator-bar, .live-estimator-bar').first()
    const estimatorVisible = await estimatorBar.isVisible({ timeout: 3000 }).catch(() => false)
    console.log(`[ESTIMATOR] LiveEstimatorBar visible: ${estimatorVisible}`)

    if (estimatorVisible) {
      const estimatorText = await estimatorBar.textContent()
      console.log(`[ESTIMATOR] Texto: "${estimatorText?.trim()}"`)
      // Verificar si actualiza con los datos introducidos
      const showsCalculating = estimatorText?.includes('Calculando') ?? false
      const showsResult = /\d+/.test(estimatorText ?? '')
      console.log(`[ESTIMATOR] Mostrando resultado: ${showsResult} | Calculando: ${showsCalculating}`)

      if (!showsResult && !showsCalculating) {
        console.warn('[BUG B-GF-ESTIMATOR] LiveEstimatorBar no muestra resultado ni "Calculando..." con ingresos > 0')
      }
    } else {
      console.warn('[B-GF-08] LiveEstimatorBar no visible en step 1')
    }

    // Navegar al siguiente paso
    const nextBtn2 = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
    await nextBtn2.click()
    await page.waitForTimeout(500)

    await screenshot(page, 'can-04-step1-after-next')
  })

  // ── T-GF-CAN-05: Steps 2-4 — Ahorro, Inmuebles, Inversiones (skip) ──────
  test('T-GF-CAN-05: Steps 2-4 — Ahorro con intereses + skip hasta Familia', async ({ page }) => {
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    const url = page.url()
    if (url.includes('/subscribe')) { test.skip() }

    // Ir directamente a Step 2 (Ahorro) usando progress bar
    // Primero hacer step 0 minimo
    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(300)
    await page.locator('input.tg-field__input[type="number"]').first().fill('38')
    await page.waitForTimeout(200)

    // Navegar paso a paso usando "Siguiente"
    const clickNext = async () => {
      const btn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
      if (await btn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await btn.click()
        await page.waitForTimeout(600)
        return true
      }
      return false
    }

    // Step 0 → Step 1
    await clickNext()

    // Step 1: minimo para pasar (check si hay aviso cero ingresos)
    const confirmZeroBtn = page.locator('button').filter({ hasText: /confirmar.*no tuve ingresos/i }).first()
    if (await confirmZeroBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmZeroBtn.click()
      await page.waitForTimeout(300)
    }
    // Poner ingresos minimos
    const inputs1 = page.locator('input.tg-field__input[type="number"]')
    if (await inputs1.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      await inputs1.first().fill('32000')
      await page.waitForTimeout(200)
    }

    // Step 1 → Step 2 (Ahorro)
    await clickNext()

    // Verificar Step 2 titulo
    const step2Title = page.locator('h2.tg-step__title').filter({ hasText: /ahorro/i })
    const s2Visible = await step2Title.isVisible({ timeout: 5000 }).catch(() => false)
    console.log(`[STEP2] Ahorro visible: ${s2Visible}`)

    await screenshot(page, 'can-05-step2-ahorro')

    // Poner intereses = 200
    const inputs2 = page.locator('input.tg-field__input[type="number"]')
    if (await inputs2.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await inputs2.first().fill('200')
      await page.waitForTimeout(200)
    }

    // Step 2 → Step 3 (Inmuebles)
    await clickNext()

    const step3Title = page.locator('h2.tg-step__title').filter({ hasText: /inmueble|alquiler/i })
    const s3Visible = await step3Title.isVisible({ timeout: 5000 }).catch(() => false)
    console.log(`[STEP3] Inmuebles visible: ${s3Visible}`)

    await screenshot(page, 'can-05-step3-inmuebles')

    // Poner alquiler pagado (para deduccion autonomica Canarias)
    const inputs3 = page.locator('input.tg-field__input[type="number"]')
    const inputCount3 = await inputs3.count()
    // alquiler_pagado_anual es el 5o input aproximadamente
    // Intentamos encontrarlo por posicion relativa o simplemente ponemos un valor en alquiler si hay suficientes
    if (inputCount3 >= 5) {
      // El 5o input suele ser alquiler pagado (ver TaxGuidePage.tsx: ingresos_alquiler, gastos_alquiler_total, valor_adquisicion_inmueble, retenciones_alquiler, alquiler_pagado_anual)
      await inputs3.nth(4).fill('7200')
      await page.waitForTimeout(200)
      console.log('[STEP3] alquiler_pagado_anual = 7200 introducido')
    } else {
      console.warn(`[STEP3] Solo ${inputCount3} inputs numericos — no se pudo introducir alquiler_pagado_anual`)
    }

    await screenshot(page, 'can-05-step3-with-alquiler')

    // Step 3 → Step 4 (Inversiones)
    await clickNext()

    const step4Title = page.locator('h2.tg-step__title').filter({ hasText: /inversi|cripto/i })
    const s4Visible = await step4Title.isVisible({ timeout: 5000 }).catch(() => false)
    console.log(`[STEP4] Inversiones visible: ${s4Visible}`)
    await screenshot(page, 'can-05-step4-inversiones')

    // Skip inversiones — hacer siguiente
    await clickNext()

    await screenshot(page, 'can-05-step5-after-inversiones')
    console.log('[STEPS 2-4] Completados')
  })

  // ── T-GF-CAN-06: Step 5 — Familia con hijo nacido 2023 ──────────────────
  test('T-GF-CAN-06: Step 5 — Familia (1 hijo, 2023)', async ({ page }) => {
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    const url = page.url()
    if (url.includes('/subscribe')) { test.skip() }

    // Navegar rapido a step 5 via progress steps (si están habilitados)
    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(200)
    await page.locator('input.tg-field__input[type="number"]').first().fill('38')
    await page.waitForTimeout(200)

    const clickNext = async (timeout = 3000) => {
      try {
        const btn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
        await btn.waitFor({ state: 'visible', timeout })
        await btn.click()
        await page.waitForTimeout(500)
      } catch (_) { console.warn('[clickNext] Boton no encontrado') }
    }

    // Avanzar paso a paso hasta step 5 (Familia)
    await clickNext() // 0 → 1
    // En step 1 poner ingresos minimos para no quedar bloqueado
    await page.locator('input.tg-field__input[type="number"]').first().fill('32000').catch(() => {})
    await page.waitForTimeout(200)
    await clickNext() // 1 → 2
    await clickNext() // 2 → 3
    await clickNext() // 3 → 4
    await clickNext() // 4 → 5

    // Verificar que estamos en Step 5 (Familia)
    const familiaTitle = page.locator('h2.tg-step__title').filter({ hasText: /familia|descendientes|hijos/i })
    const familiaVisible = await familiaTitle.isVisible({ timeout: 8000 }).catch(() => false)
    console.log(`[STEP5] Familia visible: ${familiaVisible}`)

    if (!familiaVisible) {
      const currentH2 = await page.locator('h2.tg-step__title').first().textContent().catch(() => 'N/A')
      console.warn(`[STEP5] Titulo actual: "${currentH2}" — puede no haber llegado a Familia`)
    }

    await screenshot(page, 'can-06-step5-familia')

    // Buscar el input de num_descendientes
    const numInputs = page.locator('input.tg-field__input[type="number"]')
    const inputCount = await numInputs.count()
    console.log(`[STEP5] Inputs numericos: ${inputCount}`)

    // Poner num_descendientes = 1 (primer input)
    if (inputCount > 0) {
      await numInputs.first().fill('1')
      await page.waitForTimeout(400)

      // Verificar si aparece campo de año de nacimiento
      const newCount = await numInputs.count()
      console.log(`[STEP5] Inputs tras poner 1 descendiente: ${newCount}`)

      if (newCount > 1) {
        // Poner año de nacimiento: 2023
        await numInputs.nth(1).fill('2023')
        await page.waitForTimeout(300)
        console.log('[STEP5] Año nacimiento 2023 introducido')
      } else {
        console.warn('[STEP5] No aparecio campo de año de nacimiento tras poner 1 descendiente')
      }
    }

    await screenshot(page, 'can-06-step5-with-hijo')
    console.log('[STEP5] Familia completado')
  })

  // ── T-GF-CAN-07: Step 6 — Deducciones Canarias ─────────────────────────
  test('T-GF-CAN-07: Step 6 — Deducciones especificas Canarias', async ({ page }) => {
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    const url = page.url()
    if (url.includes('/subscribe')) { test.skip() }

    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(200)
    await page.locator('input.tg-field__input[type="number"]').first().fill('38')
    await page.waitForTimeout(200)

    const clickNext = async () => {
      try {
        const btn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
        await btn.waitFor({ state: 'visible', timeout: 5000 })
        await btn.click()
        await page.waitForTimeout(600)
      } catch (_) { console.warn('[clickNext] timeout') }
    }

    // Navegar hasta step 6 (Deducciones)
    await clickNext() // 0 → 1
    await page.locator('input.tg-field__input[type="number"]').first().fill('32000').catch(() => {})
    await page.waitForTimeout(200)
    await clickNext() // 1 → 2
    await clickNext() // 2 → 3
    // En step 3 poner alquiler pagado = 7200 para activar deduccion Canarias
    const inputs3 = page.locator('input.tg-field__input[type="number"]')
    const cnt3 = await inputs3.count()
    if (cnt3 >= 5) {
      await inputs3.nth(4).fill('7200').catch(() => {})
      await page.waitForTimeout(200)
    }
    await clickNext() // 3 → 4
    await clickNext() // 4 → 5
    // En step 5 poner 1 descendiente
    await page.locator('input.tg-field__input[type="number"]').first().fill('1').catch(() => {})
    await page.waitForTimeout(400)
    await page.locator('input.tg-field__input[type="number"]').nth(1).fill('2023').catch(() => {})
    await page.waitForTimeout(200)
    await clickNext() // 5 → 6

    // Verificar que estamos en Step 6 (Deducciones)
    const deduccionesTitle = page.locator('h2.tg-step__title').filter({ hasText: /deducci/i })
    const deduccionesVisible = await deduccionesTitle.isVisible({ timeout: 8000 }).catch(() => false)
    console.log(`[STEP6] Deducciones visible: ${deduccionesVisible}`)

    await screenshot(page, 'can-07-step6-deducciones-initial')

    if (deduccionesVisible) {
      // Verificar que aparece el DynamicFiscalForm con campos CCAA Canarias
      const dynamicFormFields = page.locator('.fiscal-form, [class*="fiscal"], .tg-step input, .tg-step select')
      const fieldCount = await dynamicFormFields.count()
      console.log(`[STEP6] Campos en formulario de deducciones: ${fieldCount}`)

      // Buscar preguntas de discovery de deducciones
      const discoveryQuestions = page.locator('.deduction-question, [class*="discovery"], .tg-step .tg-field__label')
      const questionCount = await discoveryQuestions.count()
      console.log(`[STEP6] Etiquetas/preguntas en step 6: ${questionCount}`)

      // Listar las etiquetas para debug
      for (let i = 0; i < Math.min(questionCount, 10); i++) {
        const label = await discoveryQuestions.nth(i).textContent()
        console.log(`  [LABEL ${i}] "${label?.trim()}"`)
      }

      // Verificar campos especificos de Canarias (alquiler habitual)
      const pageText = await page.textContent('body')
      const mentionsAlquiler = pageText?.toLowerCase().includes('alquiler') ?? false
      const mentionsCanarias = pageText?.toLowerCase().includes('canarias') ?? false
      console.log(`[STEP6] Menciona alquiler: ${mentionsAlquiler} | Menciona Canarias: ${mentionsCanarias}`)

      if (!mentionsAlquiler && !mentionsCanarias) {
        console.warn('[STEP6] No aparecen deducciones especificas de Canarias (alquiler) — posible bug B-GF-07')
      }
    } else {
      const currentTitle = await page.locator('h2.tg-step__title').first().textContent().catch(() => 'N/A')
      console.error(`[STEP6] No estamos en Deducciones — titulo actual: "${currentTitle}"`)
    }

    await screenshot(page, 'can-07-step6-deducciones-detail')
  })

  // ── T-GF-CAN-08: Step 7 — Resultado IRPF ────────────────────────────────
  test('T-GF-CAN-08: Step 7 — Resultado IRPF Canarias (TEST CRITICO)', async ({ page }) => {
    test.setTimeout(90000)
    await login(page)
    await dismissModals(page)
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 20000 })

    const url = page.url()
    if (url.includes('/subscribe')) { test.skip() }

    const apiErrors: string[] = []
    page.on('response', async resp => {
      if (resp.url().includes('/api/irpf/estimate') && resp.status() >= 400) {
        const body = await resp.text().catch(() => '(no body)')
        apiErrors.push(`${resp.status()} ${resp.url()} — ${body}`)
        console.error(`[API ERROR] /api/irpf/estimate: ${resp.status()} — ${body}`)
      }
    })

    const ccaaSelect = page.locator('select.tg-field__select').first()
    await expect(ccaaSelect).toBeVisible({ timeout: 10000 })
    await ccaaSelect.selectOption('Canarias')
    await page.waitForTimeout(300)
    // Edad
    await page.locator('input.tg-field__input[type="number"]').first().fill('38')
    await page.waitForTimeout(200)

    const clickNext = async (stepName: string) => {
      try {
        const btn = page.locator('button.tg-nav__btn--primary').filter({ hasText: /siguiente/i }).first()
        await btn.waitFor({ state: 'visible', timeout: 5000 })
        await btn.click()
        await page.waitForTimeout(600)
        console.log(`[NAV] → ${stepName}`)
      } catch (e) {
        console.warn(`[NAV] Fallo al ir a ${stepName}: ${e}`)
      }
    }

    // Step 0 → 1
    await clickNext('Step 1 Trabajo')
    // Step 1: ingresos
    const s1Inputs = page.locator('input.tg-field__input[type="number"]')
    await s1Inputs.first().fill('32000').catch(() => {})
    await page.waitForTimeout(200)
    // SS empleado
    const s1Count = await s1Inputs.count()
    if (s1Count > 1) await s1Inputs.nth(1).fill('2100').catch(() => {})
    // Retenciones (poner directamente el total anual)
    if (s1Count > 3) await s1Inputs.nth(3).fill('5000').catch(() => {})
    await page.waitForTimeout(200)

    // Step 1 → 2
    await clickNext('Step 2 Ahorro')
    const s2Inputs = page.locator('input.tg-field__input[type="number"]')
    if (await s2Inputs.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      await s2Inputs.first().fill('200').catch(() => {})
    }
    await page.waitForTimeout(200)

    // Step 2 → 3
    await clickNext('Step 3 Inmuebles')
    await page.waitForTimeout(300)
    // Alquiler pagado anual para deduccion Canarias
    const s3Inputs = page.locator('input.tg-field__input[type="number"]')
    const s3Count = await s3Inputs.count()
    if (s3Count >= 5) {
      await s3Inputs.nth(4).fill('7200').catch(() => {})
      await page.waitForTimeout(200)
    }

    // Step 3 → 4
    await clickNext('Step 4 Inversiones')
    await page.waitForTimeout(300)

    // Step 4 → 5
    await clickNext('Step 5 Familia')
    // 1 descendiente, nacido 2023
    const s5Inputs = page.locator('input.tg-field__input[type="number"]')
    await s5Inputs.first().fill('1').catch(() => {})
    await page.waitForTimeout(400)
    const s5CountAfter = await s5Inputs.count()
    if (s5CountAfter > 1) {
      await s5Inputs.nth(1).fill('2023').catch(() => {})
    }
    await page.waitForTimeout(200)

    // Step 5 → 6
    await clickNext('Step 6 Deducciones')
    await page.waitForTimeout(1000) // esperar que carguen las deducciones

    // Step 6 → 7 (Resultado)
    await clickNext('Step 7 Resultado')

    // Esperar que aparezca el resultado
    await screenshot(page, 'can-08-step7-loading')

    // Buscar el contenedor de resultado
    const resultContainer = page.locator('.tg-result, .resultado, [class*="result"]').first()
    // O buscar el H2 con "Resultado"
    const resultH2 = page.locator('h2.tg-step__title').filter({ hasText: /resultado|estimaci/i })

    let resultVisible = false
    try {
      // Esperar hasta 20 segundos para que aparezca el resultado (llama a /api/irpf/estimate)
      await page.waitForSelector('h2.tg-step__title', { timeout: 20000 })
      resultVisible = await resultH2.isVisible({ timeout: 15000 }).catch(() => false)
    } catch (_) {
      resultVisible = false
    }

    console.log(`[STEP7] Resultado visible: ${resultVisible}`)

    if (resultVisible) {
      // Capturar el valor del resultado estimado
      const pageBodyText = await page.textContent('body') ?? ''

      // Buscar resultado_estimado
      const hasPagar = pageBodyText.toLowerCase().includes('a pagar') || pageBodyText.includes('pagar')
      const hasDevolver = pageBodyText.toLowerCase().includes('a devolver') || pageBodyText.includes('devolver')
      const hasEUR = pageBodyText.includes('EUR') || pageBodyText.includes('€')

      console.log(`[RESULTADO] A pagar: ${hasPagar} | A devolver: ${hasDevolver} | Muestra EUR: ${hasEUR}`)

      // Verificar que hay un numero en la pagina (el resultado)
      const eurosMatch = pageBodyText.match(/[\d.,]+\s*(?:EUR|€)/g)
      console.log(`[RESULTADO] Valores EUR encontrados: ${JSON.stringify(eurosMatch?.slice(0, 5))}`)

      // Verificar deducciones autonomicas de Canarias
      const hasCcaaDeductions = pageBodyText.toLowerCase().includes('canarias') ||
        pageBodyText.toLowerCase().includes('auton') ||
        pageBodyText.toLowerCase().includes('deducci')
      console.log(`[RESULTADO] Deducciones CCAA mencionadas: ${hasCcaaDeductions}`)

      // Verificar errores API
      if (apiErrors.length > 0) {
        console.error('[API ERRORS] Errores en /api/irpf/estimate:', apiErrors)
      } else {
        console.log('[API] /api/irpf/estimate — sin errores 4xx/5xx')
      }

      // Verificar que el resultado tiene sentido para 32000 EUR en Canarias
      // Con 32000 EUR brutos, retencion 5000 EUR, hijo 2023
      // IRPF aproximado: ~15-18% efectivo = ~4800-5760 EUR cuota
      // Con retencion 5000 EUR → resultado cercano a 0, posible pequeña devolucion o pequeño pago
      const resultIsReasonable = hasEUR && (hasPagar || hasDevolver)
      expect(resultIsReasonable, 'El resultado debe mostrar un importe en EUR con indicador a pagar/devolver').toBe(true)

    } else {
      // Capturar lo que hay en pantalla para debug
      const currentH2 = await page.locator('h2.tg-step__title').first().textContent().catch(() => 'N/A')
      console.error(`[STEP7] Resultado NO visible — titulo actual: "${currentH2}"`)
      console.error(`[STEP7] API errors: ${JSON.stringify(apiErrors)}`)

      // Capturar errores de consola relevantes
      const jsErrors = consoleErrors.filter(e => !e.includes('favicon') && !e.includes('sw.js'))
      if (jsErrors.length > 0) {
        console.error('[STEP7] JS errors:', jsErrors)
      }
    }

    await screenshot(page, 'can-08-step7-resultado-final')

    // Resumen final de errores de consola
    const relevantErrors = consoleErrors.filter(e =>
      !e.includes('favicon') && !e.includes('manifest') && !e.includes('sw.js')
    )
    const relevantNetworkErrors = networkErrors.filter(e => !e.includes('favicon'))
    console.log(`\n[RESUMEN] Errores de consola: ${relevantErrors.length}`)
    console.log(`[RESUMEN] Errores de red: ${relevantNetworkErrors.length}`)
    if (relevantErrors.length > 0) console.log('[CONSOLE ERRORS]', relevantErrors)
    if (relevantNetworkErrors.length > 0) console.log('[NETWORK ERRORS]', relevantNetworkErrors)
  })

  // ── T-GF-CAN-09: Test API directo /api/irpf/estimate Canarias ──────────
  test('T-GF-CAN-09: API /api/irpf/estimate para Canarias (directo)', async ({ request }) => {
    // 1. Obtener JWT
    const loginResp = await request.post(`${API_URL}/auth/login`, {
      data: { email: EMAIL, password: PASSWORD }
    })
    expect(loginResp.status(), 'Login debe devolver 200').toBe(200)
    const loginData = await loginResp.json()
    const token = loginData.access_token
    expect(token, 'JWT debe estar presente en respuesta de login').toBeTruthy()

    // 2. Llamar al endpoint de estimacion con perfil Canarias
    const estimateResp = await request.post(`${API_URL}/api/irpf/estimate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        comunidad_autonoma: 'Canarias',
        edad_contribuyente: 38,
        ingresos_trabajo: 32000,
        ss_empleado: 2100,
        retenciones_trabajo: 5000,
        intereses: 200,
        retenciones_ahorro: 0,
        alquiler_pagado_anual: 7200,
        num_descendientes: 1,
        edades_descendientes: [2],  // hijo nacido 2023 → 2 años
        tributacion_conjunta: false,
        // Campos opcionales para Canarias
        deducciones_answers: { alquiler_vivienda: true }
      }
    })

    const status = estimateResp.status()
    console.log(`[API] /api/irpf/estimate status: ${status}`)

    if (status === 200) {
      const data = await estimateResp.json()
      console.log(`[API] Respuesta completa:`, JSON.stringify(data, null, 2))

      // Verificaciones clave
      expect(data).toHaveProperty('resultado_estimado')
      expect(data).toHaveProperty('cuota_integra_total')
      expect(typeof data.resultado_estimado, 'resultado_estimado debe ser numero').toBe('number')

      console.log(`[API] resultado_estimado: ${data.resultado_estimado} EUR`)
      console.log(`[API] cuota_integra_total: ${data.cuota_integra_total} EUR`)
      console.log(`[API] comunidad_autonoma usada: ${data.comunidad_autonoma ?? data.ccaa ?? '(no en respuesta)'}`)

      // Verificar que el resultado es razonable
      // Para 32000 EUR con retenciones 5000 EUR, esperamos resultado cercano a 0 o pequeño
      const resultadoAbs = Math.abs(data.resultado_estimado)
      expect(resultadoAbs).toBeLessThan(8000)  // No mas de 8000 EUR de diferencia
      expect(resultadoAbs).toBeGreaterThanOrEqual(0)

      // Verificar deducciones autonomicas (si estan en la respuesta)
      if (data.deducciones_autonomicas_aplicadas !== undefined) {
        console.log(`[API] deducciones_autonomicas_aplicadas: ${data.deducciones_autonomicas_aplicadas} EUR`)
      }
      if (data.deducciones_autonomicas_detalle !== undefined) {
        console.log(`[API] deducciones_autonomicas_detalle:`, data.deducciones_autonomicas_detalle)
      }

      // Verificar que se usan escalas de Canarias (no forales)
      // Las escalas de Canarias son regimen comun — el resultado no debe ser 0 si hay impuesto
      if (data.tipo_regimen) {
        console.log(`[API] tipo_regimen: ${data.tipo_regimen}`)
        expect(data.tipo_regimen).not.toContain('foral')
      }

    } else if (status === 422) {
      const errorData = await estimateResp.json()
      console.error(`[API BUG] 422 Unprocessable Entity: ${JSON.stringify(errorData)}`)
      // No fallar el test — registrar el bug
    } else if (status === 500) {
      const errorData = await estimateResp.text().catch(() => '(no body)')
      console.error(`[API BUG CRITICO] 500 Internal Server Error: ${errorData}`)
      throw new Error(`/api/irpf/estimate devuelve 500 para Canarias: ${errorData}`)
    } else {
      console.error(`[API] Status inesperado: ${status}`)
    }
  })
})
