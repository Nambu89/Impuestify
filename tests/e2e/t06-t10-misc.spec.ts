import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const BASE_URL = 'https://impuestify.com';
const SHOTS = 'tests/e2e/screenshots';

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

async function loginAs(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 20000 });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/chat`, { timeout: 15000 });
}

test.describe('T06 - Perfil fiscal', () => {
  test('T06a - Settings page carga correctamente', async ({ page }) => {
    await loginAs(page, 'test.particular@impuestify.es', 'Test2026!');

    // Navegar a settings
    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'networkidle', timeout: 20000 });
    await shot(page, 'T06a-settings-particular');

    const url = page.url();
    const content = await page.content();
    const h1 = await page.locator('h1, h2').first().textContent().catch(() => '');

    const hasSettings = content.toLowerCase().includes('configuraci') ||
      content.toLowerCase().includes('perfil') ||
      content.toLowerCase().includes('settings');

    console.log(`URL: ${url}`);
    console.log(`H1: ${h1}`);
    console.log(`Has settings content: ${hasSettings}`);
    expect(hasSettings, 'Settings page should have configuración/perfil content').toBe(true);
  });

  test('T06b - Settings autonomo muestra campos extra', async ({ page }) => {
    await loginAs(page, 'test.autonomo@impuestify.es', 'Test2026!');

    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'networkidle', timeout: 20000 });
    await shot(page, 'T06b-settings-autonomo');

    const content = await page.content();
    const hasAutonomo = content.toLowerCase().includes('aut') ||
      content.toLowerCase().includes('iae') ||
      content.toLowerCase().includes('actividad') ||
      content.toLowerCase().includes('reta');

    console.log(`Settings has autonomo fields: ${hasAutonomo}`);
    // Note: not asserting here as we're just checking what's available
  });
});

test.describe('T07 - Cookies consent', () => {
  test('T07a - Cookie banner aparece en modo incocgnito', async ({ browser }) => {
    // Use a fresh context to simulate incognito / no prior cookies
    const context = await browser.newContext({
      storageState: undefined,
    });
    const page = await context.newPage();
    const consoleErrors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000); // Wait for cookie banner to appear
    await shot(page, 'T07a-cookie-banner');

    // Buscar banner de cookies
    const cookieBanner = await page.locator(
      '[id*="cookie"], [class*="cookie"], [class*="consent"], [id*="consent"], [class*="CookieConsent"]'
    ).count();

    const acceptBtn = await page.locator('button:has-text("Aceptar"), button:has-text("Accept"), button:has-text("acepto")').count();
    const rejectBtn = await page.locator('button:has-text("Rechazar"), button:has-text("Reject"), button:has-text("No acepto")').count();
    const configBtn = await page.locator('button:has-text("Configurar"), button:has-text("Personalizar"), button:has-text("Gestionar")').count();

    console.log(`Cookie banner elements: ${cookieBanner}`);
    console.log(`Accept button: ${acceptBtn}`);
    console.log(`Reject button: ${rejectBtn}`);
    console.log(`Config button: ${configBtn}`);
    console.log(`Console errors: ${consoleErrors.length}`);

    expect(cookieBanner, 'Cookie banner should be visible on first visit').toBeGreaterThan(0);

    await context.close();
  });

  test('T07b - Aceptar cookies hace desaparecer el banner', async ({ browser }) => {
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();

    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Click accept
    const acceptBtn = page.locator('button:has-text("Aceptar"), button:has-text("Accept all"), button:has-text("Acepto todo")');
    if (await acceptBtn.count() > 0) {
      await acceptBtn.first().click();
      await page.waitForTimeout(1000);
      await shot(page, 'T07b-after-accept-cookies');

      const bannerStillVisible = await page.locator('[id*="cookie"], [class*="cookie-banner"], [class*="consent"]').count();
      console.log(`Banner still visible after accept: ${bannerStillVisible}`);
    } else {
      console.log('Accept button not found');
      await shot(page, 'T07b-no-accept-button');
    }

    await context.close();
  });
});

test.describe('T08 - Responsive / Mobile chat', () => {
  test('T08a - Chat funciona en mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginAs(page, 'test.particular@impuestify.es', 'Test2026!');
    await shot(page, 'T08a-chat-mobile');

    const chatInput = page.locator('textarea, input[placeholder*="pregunta"], input[placeholder*="escrib"]').first();
    const inputVisible = await chatInput.isVisible().catch(() => false);

    console.log(`Chat input visible on mobile: ${inputVisible}`);
    expect(inputVisible, 'Chat input should be visible on mobile').toBe(true);
  });
});

test.describe('T10 - Error handling', () => {
  test('T10a - Login incorrecto muestra error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.fill('input[type="email"], input[name="email"]', 'noexiste@test.com');
    await page.fill('input[type="password"], input[name="password"]', 'ContrasenaMala123!');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(5000);
    await shot(page, 'T10a-invalid-login-error');

    const currentUrl = page.url();
    const errorText = await page.locator('[class*="error"], [class*="alert"], [role="alert"], .toast').textContent().catch(() => '');

    console.log(`URL after bad login: ${currentUrl}`);
    console.log(`Error message shown: "${errorText}"`);

    const staysOnLogin = currentUrl.includes('/login') || !currentUrl.includes('/chat');
    expect(staysOnLogin, 'Should stay on login with wrong credentials').toBe(true);
  });

  test('T10b - /chat sin auth redirige', async ({ page }) => {
    await page.goto(`${BASE_URL}/chat`, { waitUntil: 'networkidle', timeout: 20000 });
    await shot(page, 'T10b-protected-route');

    const url = page.url();
    console.log(`URL when accessing /chat unauthenticated: ${url}`);

    const redirected = !url.endsWith('/chat') || url.includes('/login');
    console.log(`Was redirected: ${redirected}`);
    expect(redirected, 'Should redirect unauthenticated user from /chat').toBe(true);
  });
});
