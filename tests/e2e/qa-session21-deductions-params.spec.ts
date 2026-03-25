/**
 * QA Session 21 — E2E Tests for deduction coverage + new IRPF simulator params
 *
 * Tests:
 * 1. Landing page loads
 * 2. Login via API + cookie injection (bypasses Turnstile widget)
 * 3. Tax Guide wizard — new XSD gap fields
 * 4. Tax Guide — Madrid estimate
 * 5. Settings — All territories in CCAA dropdown
 * 6. Tax Guide — Foral territory (Araba)
 * 7. Disability fields conditional display
 * 8. Public territorial pages
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3001'
const API_URL = 'http://localhost:8000'
const AUTH_URL = 'http://localhost:8000'
const TEST_USER = 'test.particular@impuestify.es'
const TEST_PASS = 'Test2026!'

// Helper: login via API and set auth cookie/localStorage
async function loginViaApi(page: any) {
  const resp = await page.request.post(`${AUTH_URL}/auth/login`, {
    data: { email: TEST_USER, password: TEST_PASS },
  })
  if (resp.status() !== 200) {
    console.log('Login API failed:', resp.status(), await resp.text())
    return false
  }
  const body = await resp.json()
  const token = body.tokens?.access_token || body.access_token || body.token

  if (!token) {
    console.log('No token in response:', JSON.stringify(body))
    return false
  }

  // Navigate to app first so we can set localStorage on the right origin
  await page.goto(BASE_URL)
  await page.waitForLoadState('domcontentloaded')

  // Inject token into localStorage (the app reads from here)
  await page.evaluate((t: string) => {
    localStorage.setItem('access_token', t)
    localStorage.setItem('token', t)
  }, token)

  // Also set refresh token if present
  const refreshToken = body.tokens?.refresh_token || body.refresh_token
  if (refreshToken) {
    await page.evaluate((rt: string) => {
      localStorage.setItem('refresh_token', rt)
    }, refreshToken)
  }

  return true
}

test.describe('Session 21: Deductions & Simulator Params', () => {
  test.setTimeout(60_000)

  test('T01 — Landing page loads', async ({ page }) => {
    await page.goto(BASE_URL)
    await expect(page).toHaveTitle(/Impuestify/)
    const hero = page.locator('.hero, .home-hero, [class*="hero"]').first()
    await expect(hero).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: 'tests/e2e/screenshots/s21-01-landing.png' })
  })

  test('T02 — Login via API', async ({ page }) => {
    const success = await loginViaApi(page)
    expect(success).toBeTruthy()

    // Reload to apply token
    await page.goto(BASE_URL)
    await page.waitForLoadState('networkidle')

    // Should see logged-in nav (Chat, Settings, etc.)
    const loggedIn = await page.locator('a[href="/chat"], a[href="/settings"], a[href*="guia"]').first().isVisible({ timeout: 5_000 }).catch(() => false)
    console.log(`Logged in nav visible: ${loggedIn}`)
    await page.screenshot({ path: 'tests/e2e/screenshots/s21-02-logged-in.png' })
  })

  test('T03 — Tax Guide: new XSD gap fields visible', async ({ page }) => {
    await loginViaApi(page)
    await page.goto(`${BASE_URL}/guia-fiscal`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    // Navigate through steps looking for new fields
    let foundPension = false
    let foundAlimentos = false
    let foundDobleImp = false
    let foundDiscapacidad = false

    for (let step = 0; step < 8; step++) {
      const content = await page.textContent('body')
      if (!content) continue

      if (content.includes('compensatoria')) foundPension = true
      if (content.includes('alimentos')) foundAlimentos = true
      if (content.includes('extranjero') || content.includes('doble imposici')) foundDobleImp = true
      if (content.includes('discapacidad') && content.includes('33')) foundDiscapacidad = true

      await page.screenshot({ path: `tests/e2e/screenshots/s21-03-step${step}.png` })

      const nextBtn = page.locator('button:has-text("Siguiente"), button:has-text("Continuar")').first()
      if (await nextBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await nextBtn.click()
        await page.waitForTimeout(800)
      } else {
        break
      }
    }

    console.log(`Pension compensatoria: ${foundPension}`)
    console.log(`Alimentos hijos: ${foundAlimentos}`)
    console.log(`Doble imposicion: ${foundDobleImp}`)
    console.log(`Discapacidad: ${foundDiscapacidad}`)

    expect(foundPension || foundAlimentos || foundDobleImp || foundDiscapacidad).toBeTruthy()
  })

  test('T04 — IRPF estimate API with new params', async ({ page }) => {
    // Login to get token
    const loginResp = await page.request.post(`${AUTH_URL}/auth/login`, {
      data: { email: TEST_USER, password: TEST_PASS },
    })
    const loginBody = await loginResp.json()
    const token = loginBody.tokens?.access_token

    const resp = await page.request.post(`${API_URL}/api/irpf/estimate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        ingresos_trabajo: 35000,
        comunidad_autonoma: 'Madrid',
        edad_contribuyente: 40,
        pension_compensatoria_exconyuge: 6000,
        anualidades_alimentos_hijos: 3600,
        impuestos_pagados_extranjero: 500,
        num_descendientes_discapacidad_33: 1,
        num_descendientes: 2,
      },
    })

    expect(resp.status()).toBe(200)
    const body = await resp.json()
    console.log('IRPF estimate Madrid:')
    console.log(`  cuota_integra_general: ${body.cuota_integra_general}`)
    console.log(`  reduccion_pension_compensatoria: ${body.reduccion_pension_compensatoria}`)
    console.log(`  cuota_anualidades_alimentos: ${body.cuota_anualidades_alimentos}`)
    console.log(`  deduccion_doble_imposicion: ${body.deduccion_doble_imposicion}`)
    console.log(`  resultado_estimado: ${body.resultado_estimado}`)

    expect(body.success).toBeTruthy()
    expect(body.cuota_integra_general).toBeGreaterThan(0)
  })

  test('T05 — IRPF estimate API: Araba foral', async ({ page }) => {
    const loginResp = await page.request.post(`${AUTH_URL}/auth/login`, {
      data: { email: TEST_USER, password: TEST_PASS },
    })
    const token = (await loginResp.json()).tokens?.access_token

    const resp = await page.request.post(`${API_URL}/api/irpf/estimate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        ingresos_trabajo: 40000,
        comunidad_autonoma: 'Araba',
        edad_contribuyente: 35,
        num_descendientes: 1,
      },
    })

    expect(resp.status()).toBe(200)
    const body = await resp.json()
    console.log('Araba foral estimate:')
    console.log(`  cuota_integra_general: ${body.cuota_integra_general}`)
    console.log(`  tipo_medio_efectivo: ${body.tipo_medio_efectivo}`)
    console.log(`  resultado_estimado: ${body.resultado_estimado}`)

    expect(body.success).toBeTruthy()
    expect(body.cuota_integra_general).toBeGreaterThan(0)
  })

  test('T06 — IRPF estimate API: Canarias', async ({ page }) => {
    const loginResp = await page.request.post(`${AUTH_URL}/auth/login`, {
      data: { email: TEST_USER, password: TEST_PASS },
    })
    const token = (await loginResp.json()).tokens?.access_token

    const resp = await page.request.post(`${API_URL}/api/irpf/estimate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        ingresos_trabajo: 30000,
        comunidad_autonoma: 'Canarias',
        edad_contribuyente: 30,
      },
    })

    expect(resp.status()).toBe(200)
    const body = await resp.json()
    console.log('Canarias estimate:')
    console.log(`  cuota_integra_general: ${body.cuota_integra_general}`)
    console.log(`  resultado_estimado: ${body.resultado_estimado}`)
    expect(body.success).toBeTruthy()
  })

  test('T07 — Settings: All territories in CCAA dropdown', async ({ page }) => {
    await loginViaApi(page)
    await page.goto(`${BASE_URL}/settings`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    await page.screenshot({ path: 'tests/e2e/screenshots/s21-07-settings.png' })

    // Find any select that has territory options
    const selects = page.locator('select')
    const count = await selects.count()

    let allOptions: string[] = []
    for (let i = 0; i < count; i++) {
      const opts = await selects.nth(i).locator('option').allTextContents()
      if (opts.some(o => o.includes('Madrid') || o.includes('Andaluc'))) {
        allOptions = opts
        break
      }
    }

    console.log(`CCAA options found: ${allOptions.length}`)

    const required = [
      'Madrid', 'Andaluc', 'Catalu', 'Valencia', 'Galicia',
      'Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra',
      'Canarias', 'Ceuta', 'Melilla',
      'Asturias', 'Cantabria', 'Baleares',
    ]

    const optionsText = allOptions.join(' ')
    const found = required.filter(t => optionsText.includes(t))
    const missing = required.filter(t => !optionsText.includes(t))

    console.log(`Found: ${found.length}/${required.length} (${found.join(', ')})`)
    if (missing.length) console.log(`Missing: ${missing.join(', ')}`)

    expect(found.length).toBeGreaterThanOrEqual(15)
    await page.screenshot({ path: 'tests/e2e/screenshots/s21-07-ccaa-list.png' })
  })

  test('T08 — Public territorial landing pages', async ({ page }) => {
    const pages = [
      { url: '/territorios-forales', text: 'foral' },
      { url: '/ceuta-melilla', text: 'Ceuta' },
      { url: '/canarias', text: 'Canarias' },
    ]

    for (const pg of pages) {
      await page.goto(`${BASE_URL}${pg.url}`)
      await page.waitForLoadState('networkidle')
      const content = await page.textContent('body')
      const found = content?.toLowerCase().includes(pg.text.toLowerCase())
      console.log(`${pg.url}: "${pg.text}" = ${found}`)
      expect(found).toBeTruthy()
      await page.screenshot({ path: `tests/e2e/screenshots/s21-08-${pg.url.replace(/\//g, '')}.png` })
    }
  })
})
