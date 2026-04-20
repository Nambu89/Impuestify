/**
 * Mobile Audit Tests — Viewport 375x812 (iPhone 14)
 * Ejecutar: npx playwright test tests/e2e/mobile-audit.spec.ts --headed
 * Con servidor local: PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/mobile-audit.spec.ts
 */

import { test, expect, Page } from '@playwright/test'
import path from 'path'

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
const MOBILE_VIEWPORT = { width: 375, height: 812 }
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots', 'mobile')

// Helper: screenshot con nombre descriptivo
async function shot(page: Page, name: string) {
    await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, `${name}.png`),
        fullPage: true,
    })
}

// Helper: detectar overflow horizontal
async function hasHorizontalOverflow(page: Page): Promise<boolean> {
    return page.evaluate(() => {
        const body = document.body
        const html = document.documentElement
        return body.scrollWidth > html.clientWidth
    })
}

// Helper: detectar elementos que se salen del viewport
async function getOverflowingElements(page: Page): Promise<string[]> {
    return page.evaluate(() => {
        const vw = document.documentElement.clientWidth
        const overflowing: string[] = []
        document.querySelectorAll('*').forEach(el => {
            const rect = el.getBoundingClientRect()
            if (rect.right > vw + 5) { // +5px de tolerancia
                const id = el.id ? `#${el.id}` : el.className ? `.${el.className.toString().split(' ')[0]}` : el.tagName
                overflowing.push(id)
            }
        })
        return [...new Set(overflowing)].slice(0, 10) // max 10
    })
}

// ============================================================
// T1: Landing Page (/)
// ============================================================
test.describe('T1: Landing Page — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Hero section — text visible, CTAs present', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't1-landing-hero')

        // Hero title debe existir
        const heroTitle = page.locator('.hero-title')
        await expect(heroTitle).toBeVisible()

        // Botones CTA presentes (Empezar Ahora / Iniciar Sesion)
        const ctaButtons = page.locator('.hero-actions .btn')
        const count = await ctaButtons.count()
        expect(count).toBeGreaterThanOrEqual(1)

        // No debe haber overflow horizontal
        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Hero section causa overflow horizontal').toBe(false)
    })

    test('Header — hamburger visible, nav horizontal oculta', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

        // Hamburger menu visible en mobile
        const hamburger = page.locator('.menu-toggle')
        await expect(hamburger).toBeVisible()

        // Nav horizontal oculta en mobile (display: none)
        const nav = page.locator('.header .nav')
        const navDisplay = await nav.evaluate(el => getComputedStyle(el).display)
        expect(navDisplay, 'La nav horizontal no debe ser visible en mobile').toBe('none')
    })

    test('Stats section — 4 items, no overflow', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await page.locator('.stats').scrollIntoViewIfNeeded()
        await shot(page, 't1-landing-stats')

        const stats = page.locator('.stat-item')
        const count = await stats.count()
        expect(count).toBe(4)

        // Stats en grid 2x2 en mobile (no 4 columnas horizontales)
        const statsGrid = page.locator('.stats-grid')
        const gridCols = await statsGrid.evaluate(el => getComputedStyle(el).gridTemplateColumns)
        // En mobile debe ser 2 columnas, no 4
        expect(gridCols).not.toContain('repeat(4')
    })

    test('Territory chips — wrap correctamente, no overflow', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await page.locator('.territory-grid').scrollIntoViewIfNeeded()
        await shot(page, 't1-landing-territory')

        const chips = page.locator('.territory-chip')
        const count = await chips.count()
        expect(count).toBe(21) // 21 territorios

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Territory chips causan overflow').toBe(false)
    })

    test('Savings cards — stack vertical en mobile', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await page.locator('.savings-grid').scrollIntoViewIfNeeded()
        await shot(page, 't1-landing-savings')

        const savingsGrid = page.locator('.savings-grid')
        const gridCols = await savingsGrid.evaluate(el => getComputedStyle(el).gridTemplateColumns)
        // En mobile debe ser 1 columna (1fr)
        expect(gridCols, 'Savings cards no se apilan en mobile').toBe('1fr')
    })

    test('Footer — legible, sin overflow', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await page.locator('footer').scrollIntoViewIfNeeded()
        await shot(page, 't1-landing-footer')

        const footer = page.locator('footer.footer')
        await expect(footer).toBeVisible()

        // Footer en 1 columna en mobile
        const footerContent = page.locator('.footer-content')
        const gridCols = await footerContent.evaluate(el => getComputedStyle(el).gridTemplateColumns)
        expect(gridCols, 'Footer no usa 1 columna en mobile').toBe('1fr')

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Footer causa overflow').toBe(false)
    })

    test('Scroll completo — no overflow en ningun punto', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

        // Scroll por secciones y verificar
        const sections = ['.hero', '.savings', '.stats', '.coverage', '.comparison', '.features', '.pricing', '.cta', 'footer']
        for (const selector of sections) {
            const el = page.locator(selector).first()
            if (await el.count() > 0) {
                await el.scrollIntoViewIfNeeded()
                const overflow = await hasHorizontalOverflow(page)
                if (overflow) {
                    const offenders = await getOverflowingElements(page)
                    console.error(`Overflow en seccion ${selector}:`, offenders)
                }
                expect(overflow, `Seccion ${selector} causa overflow horizontal`).toBe(false)
            }
        }
        await shot(page, 't1-landing-bottom')
    })
})

// ============================================================
// T2: Login (/login)
// ============================================================
test.describe('T2: Login — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Layout — brand panel arriba, form panel abajo', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't2-login')

        // Brand panel visible
        const brand = page.locator('.auth-brand')
        await expect(brand).toBeVisible()

        // Form panel visible
        const form = page.locator('.auth-form-panel')
        await expect(form).toBeVisible()

        // En mobile: flex-direction column (no row)
        const authPage = page.locator('.auth-page')
        const flexDir = await authPage.evaluate(el => getComputedStyle(el).flexDirection)
        expect(flexDir, 'Login page no es columna en mobile').toBe('column')

        // No overflow
        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Login page causa overflow').toBe(false)
    })

    test('Inputs — ancho completo, no cortados', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 })

        const emailInput = page.locator('input[type="email"]')
        const passInput = page.locator('input[type="password"]')
        const submitBtn = page.locator('.auth-submit-btn')

        await expect(emailInput).toBeVisible()
        await expect(passInput).toBeVisible()
        await expect(submitBtn).toBeVisible()

        // Inputs deben tener ancho cercano al 100% de su contenedor
        const emailWidth = await emailInput.evaluate(el => el.getBoundingClientRect().width)
        expect(emailWidth, 'Email input muy estrecho').toBeGreaterThan(250)

        // Boton submit ancho completo
        const btnWidth = await submitBtn.evaluate(el => el.getBoundingClientRect().width)
        expect(btnWidth, 'Submit btn no ocupa ancho completo').toBeGreaterThan(250)
    })
})

// ============================================================
// T3: Register (/register)
// ============================================================
test.describe('T3: Register — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Layout — mismo patron que login', async ({ page }) => {
        await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't3-register')

        await expect(page.locator('.auth-brand')).toBeVisible()
        await expect(page.locator('.auth-form-panel')).toBeVisible()

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Register causa overflow').toBe(false)
    })

    test('Campos visibles sin scroll horizontal', async ({ page }) => {
        await page.goto(`${BASE_URL}/register`, { waitUntil: 'networkidle', timeout: 30000 })

        // Deben existir al menos 3 inputs (nombre, email, password)
        const inputs = page.locator('.auth-input')
        const count = await inputs.count()
        expect(count).toBeGreaterThanOrEqual(3)
    })
})

// ============================================================
// T4: Canarias (/canarias)
// ============================================================
test.describe('T4: Canarias — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Hero legible, sin overflow', async ({ page }) => {
        await page.goto(`${BASE_URL}/canarias`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't4-canarias-hero')

        const hero = page.locator('.canarias-hero')
        await expect(hero).toBeVisible()

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Canarias hero causa overflow').toBe(false)
    })

    test('Tabla IGIC — tiene overflow-x: auto (scrollable)', async ({ page }) => {
        await page.goto(`${BASE_URL}/canarias`, { waitUntil: 'networkidle', timeout: 30000 })

        // La tabla debe estar envuelta en un contenedor con overflow-x: auto
        const tableWrap = page.locator('.canarias-comparacion__table-wrap').first()
        if (await tableWrap.count() > 0) {
            const overflow = await tableWrap.evaluate(el => getComputedStyle(el).overflowX)
            expect(overflow, 'Tabla IGIC no tiene overflow-x scroll').toBe('auto')
            await shot(page, 't4-canarias-tabla')
        }
    })

    test('Stats de hero wrapping en mobile', async ({ page }) => {
        await page.goto(`${BASE_URL}/canarias`, { waitUntil: 'networkidle', timeout: 30000 })

        const statsRow = page.locator('.canarias-hero__stats')
        if (await statsRow.count() > 0) {
            const flexWrap = await statsRow.evaluate(el => getComputedStyle(el).flexWrap)
            expect(flexWrap, 'Stats de Canarias no hacen wrap').toBe('wrap')
        }
    })
})

// ============================================================
// T5: Territorios Forales (/territorios-forales)
// ============================================================
test.describe('T5: Territorios Forales — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Hero visible, sin overflow', async ({ page }) => {
        await page.goto(`${BASE_URL}/territorios-forales`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't5-foral-hero')

        const hero = page.locator('.foral-hero')
        await expect(hero).toBeVisible()

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Foral page causa overflow').toBe(false)
    })

    test('Tablas de tramos con overflow-x: auto', async ({ page }) => {
        await page.goto(`${BASE_URL}/territorios-forales`, { waitUntil: 'networkidle', timeout: 30000 })

        const tableWraps = page.locator('.foral-tramos__table-wrap')
        const count = await tableWraps.count()
        for (let i = 0; i < Math.min(count, 2); i++) {
            const overflowX = await tableWraps.nth(i).evaluate(el => getComputedStyle(el).overflowX)
            expect(overflowX, `Tabla foral ${i} no tiene overflow-x scroll`).toBe('auto')
        }
        if (count > 0) {
            await page.locator('.foral-tramos').scrollIntoViewIfNeeded()
            await shot(page, 't5-foral-tablas')
        }
    })
})

// ============================================================
// T6: Ceuta/Melilla (/ceuta-melilla)
// ============================================================
test.describe('T6: Ceuta/Melilla — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Hero visible, sin overflow', async ({ page }) => {
        await page.goto(`${BASE_URL}/ceuta-melilla`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't6-ceuta-hero')

        const hero = page.locator('.ceuta-hero')
        await expect(hero).toBeVisible()

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Ceuta/Melilla causa overflow').toBe(false)
    })
})

// ============================================================
// T7: Subscribe (/subscribe)
// ============================================================
test.describe('T7: Subscribe — mobile 375x812', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Plan cards stack vertical en mobile', async ({ page }) => {
        await page.goto(`${BASE_URL}/subscribe`, { waitUntil: 'networkidle', timeout: 30000 })
        await shot(page, 't7-subscribe')

        const plansGrid = page.locator('.subscribe-plans')
        await expect(plansGrid).toBeVisible()

        // En mobile: 1 columna
        const gridCols = await plansGrid.evaluate(el => getComputedStyle(el).gridTemplateColumns)
        expect(gridCols, 'Plans grid no es 1 columna en mobile').toBe('1fr')

        const overflow = await hasHorizontalOverflow(page)
        expect(overflow, 'Subscribe page causa overflow').toBe(false)
    })

    test('Precios y features legibles', async ({ page }) => {
        await page.goto(`${BASE_URL}/subscribe`, { waitUntil: 'networkidle', timeout: 30000 })

        // Al menos 2 cards de planes
        const plans = page.locator('.subscribe-plan')
        const count = await plans.count()
        expect(count).toBeGreaterThanOrEqual(2)

        // Precios visibles
        const prices = page.locator('.subscribe-plan__value')
        const priceCount = await prices.count()
        expect(priceCount).toBeGreaterThanOrEqual(2)
    })

    test('CTAs ancho completo', async ({ page }) => {
        await page.goto(`${BASE_URL}/subscribe`, { waitUntil: 'networkidle', timeout: 30000 })

        const ctaButtons = page.locator('.subscribe-plan__cta')
        const count = await ctaButtons.count()
        if (count > 0) {
            // El primer CTA debe tener width: 100%
            const btnWidth = await ctaButtons.first().evaluate(el => getComputedStyle(el).width)
            // width: 100% resulta en un valor en px. Verificar que es >= 250px
            const widthPx = parseFloat(btnWidth)
            expect(widthPx, 'CTA button no ocupa ancho completo').toBeGreaterThan(250)
        }
    })
})

// ============================================================
// T8: Hamburger menu — abre y navega
// ============================================================
test.describe('T8: Navegacion mobile — hamburger menu', () => {
    test.beforeEach(async ({ page }) => {
        await page.setViewportSize(MOBILE_VIEWPORT)
    })

    test('Hamburger abre mobile nav overlay', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

        const hamburger = page.locator('.menu-toggle')
        await expect(hamburger).toBeVisible()

        // Antes de click: overlay no visible
        const overlay = page.locator('.mobile-nav-overlay')
        const initiallyHidden = await overlay.count() === 0

        // Click hamburger
        await hamburger.click()
        await page.waitForTimeout(400)

        // Overlay debe aparecer
        await expect(overlay).toBeVisible()
        await shot(page, 't8-mobile-nav-open')

        // Links de navegacion presentes
        const navLinks = page.locator('.mobile-nav__link')
        const linkCount = await navLinks.count()
        expect(linkCount, 'Mobile nav no tiene links').toBeGreaterThanOrEqual(3)

        // Cerrar overlay haciendo click fuera
        await overlay.click({ position: { x: 200, y: 500 } })
        await page.waitForTimeout(300)

        // Overlay debe desaparecer
        const stillVisible = await overlay.isVisible()
        expect(stillVisible, 'Overlay no se cierra al hacer click fuera').toBe(false)
    })

    test('Nav bar header no tiene overflow horizontal', async ({ page }) => {
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

        const header = page.locator('.header')
        const headerWidth = await header.evaluate(el => el.scrollWidth)
        const vpWidth = MOBILE_VIEWPORT.width
        expect(headerWidth, 'Header tiene overflow horizontal').toBeLessThanOrEqual(vpWidth + 5)
    })
})
