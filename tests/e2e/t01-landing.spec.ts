import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const BASE_URL = 'https://impuestify.com';
const SHOTS = 'tests/e2e/screenshots';

async function shot(page: Page, name: string) {
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

test.describe('T01 - Landing Page', () => {
  test('T01a - Landing desktop - carga y elementos clave', async ({ page }) => {
    const consoleErrors: string[] = [];
    const networkFails: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('requestfailed', req => {
      networkFails.push(`${req.failure()?.errorText} — ${req.url()}`);
    });

    await page.setViewportSize({ width: 1280, height: 800 });
    const t0 = Date.now();
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    const loadTime = Date.now() - t0;

    await shot(page, 'T01a-landing-desktop');

    const title = await page.title();
    const h1Text = await page.locator('h1').first().textContent().catch(() => '');

    // Verificar que hay contenido H1
    expect(h1Text).toBeTruthy();

    // Verificar links de login y registro
    const loginCount = await page.locator('a[href*="/login"], button:has-text("Iniciar"), a:has-text("Entrar"), a:has-text("Login")').count();
    const registerCount = await page.locator('a[href*="/register"], a:has-text("Registr"), button:has-text("Registr"), a:has-text("Empieza")').count();

    // Verificar pricing section existe
    const pricingText = await page.locator('text=/€\/mes|por mes|al mes/i').count();

    // Log de resultados
    console.log(`LOAD TIME: ${loadTime}ms`);
    console.log(`TITLE: ${title}`);
    console.log(`H1: ${h1Text}`);
    console.log(`Login links: ${loginCount}`);
    console.log(`Register links: ${registerCount}`);
    console.log(`Pricing mentions: ${pricingText}`);
    console.log(`Console errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) console.log('CONSOLE ERRORS:', consoleErrors.slice(0, 5));
    console.log(`Network fails: ${networkFails.length}`);
    if (networkFails.length > 0) console.log('NETWORK FAILS:', networkFails.slice(0, 5));

    // Assertions
    expect(loginCount + registerCount, 'Should have login or register links').toBeGreaterThan(0);
  });

  test('T01b - Landing mobile 375px', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await shot(page, 'T01b-landing-mobile');

    const h1 = await page.locator('h1').first().textContent().catch(() => '');
    console.log(`Mobile H1: ${h1}`);
    expect(h1).toBeTruthy();
  });

  test('T01c - SEO page /territorios-forales', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

    await page.goto(`${BASE_URL}/territorios-forales`, { waitUntil: 'networkidle', timeout: 30000 });
    await shot(page, 'T01c-territorios-forales');

    const statusCode = page.url();
    const title = await page.title();
    const h1 = await page.locator('h1').first().textContent().catch(() => 'NO H1 FOUND');
    const content = await page.content();

    const hasForalContent = content.includes('Bizkaia') || content.includes('lava') ||
      content.includes('Navarra') || content.includes('foral') || content.includes('Vasco') ||
      content.includes('Gipuzkoa');

    console.log(`URL: ${statusCode}`);
    console.log(`TITLE: ${title}`);
    console.log(`H1: ${h1}`);
    console.log(`Has foral content: ${hasForalContent}`);
    console.log(`Console errors: ${consoleErrors.length}`);

    expect(hasForalContent, 'Page should mention foral territories').toBe(true);
  });

  test('T01d - SEO page /ceuta-melilla', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

    await page.goto(`${BASE_URL}/ceuta-melilla`, { waitUntil: 'networkidle', timeout: 30000 });
    await shot(page, 'T01d-ceuta-melilla');

    const title = await page.title();
    const h1 = await page.locator('h1').first().textContent().catch(() => 'NO H1 FOUND');
    const content = await page.content();

    const hasCeutaMelillaContent = content.includes('Ceuta') || content.includes('Melilla') ||
      content.includes('IPSI') || content.includes('bonificaci');

    console.log(`TITLE: ${title}`);
    console.log(`H1: ${h1}`);
    console.log(`Has Ceuta/Melilla content: ${hasCeutaMelillaContent}`);
    console.log(`Console errors: ${consoleErrors.length}`);

    expect(hasCeutaMelillaContent, 'Page should mention Ceuta or Melilla').toBe(true);
  });

  test('T01e - Legal pages load correctly', async ({ page }) => {
    const legalPages = [
      { path: '/politica-privacidad', keyword: 'privacidad' },
      { path: '/politica-cookies', keyword: 'cookies' },
      { path: '/terminos-servicio', keyword: 'servicio' },
      { path: '/transparencia-ia', keyword: 'IA' },
    ];

    for (const lp of legalPages) {
      await page.goto(`${BASE_URL}${lp.path}`, { waitUntil: 'networkidle', timeout: 20000 });
      await shot(page, `T01e-legal-${lp.path.replace('/', '').replace('/', '-')}`);
      const content = await page.content();
      const h1 = await page.locator('h1').first().textContent().catch(() => '');
      console.log(`${lp.path} — H1: ${h1} — Has content: ${content.length > 1000}`);
      expect(content.length, `${lp.path} should have content`).toBeGreaterThan(1000);
    }
  });
});
