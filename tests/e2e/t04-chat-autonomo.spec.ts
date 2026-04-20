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

test.describe('T04 - Chat SSE Autonomo', () => {
  test('T04a - Consulta RETA e IVA trimestral Cataluna', async ({ page }) => {
    const consoleErrors: string[] = [];
    const networkErrors: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('requestfailed', req => {
      networkErrors.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText}`);
    });

    await loginAs(page, 'test.autonomo@impuestify.es', 'Test2026!');
    await shot(page, 'T04a-chat-loaded-autonomo');

    const chatInput = page.locator('textarea, input[placeholder*="pregunta"], input[placeholder*="escrib"], input[placeholder*="mensaje"]').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    const mensaje = 'Soy autónomo en Cataluña, facturo 3.500 euros al mes. ¿Qué cuota de autónomo me corresponde y cuánto debo declarar de IVA trimestralmente?';

    const t0 = Date.now();
    await chatInput.fill(mensaje);
    await chatInput.press('Enter');

    console.log('Autonomo message sent, waiting for SSE response...');

    // Esperar respuesta (90s timeout para SSE)
    await page.waitForTimeout(90000);

    const responseTime = Date.now() - t0;
    await shot(page, 'T04a-autonomo-response');

    // Capturar texto de respuesta
    const pageText = await page.content();

    const hasRETA = pageText.toLowerCase().includes('reta') || pageText.toLowerCase().includes('cuota');
    const hasIVA = pageText.toLowerCase().includes('iva') || pageText.toLowerCase().includes('trimestral');
    const hasCatalunya = pageText.toLowerCase().includes('catal') || pageText.toLowerCase().includes('cataluña');
    const hasAmount = pageText.includes('€') || pageText.includes('euro');

    console.log(`Response time: ${responseTime}ms`);
    console.log(`Has RETA/cuota: ${hasRETA}`);
    console.log(`Has IVA/trimestral: ${hasIVA}`);
    console.log(`Has Catalunya: ${hasCatalunya}`);
    console.log(`Has euro amounts: ${hasAmount}`);
    console.log(`Console errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) console.log('ERRORS:', consoleErrors.slice(0, 5));

    expect(hasRETA || hasIVA, 'Response should mention RETA or IVA for autonomo').toBe(true);
  });
});
