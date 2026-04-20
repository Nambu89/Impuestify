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

test.describe('T03 - Chat SSE Particular', () => {
  test('T03a - Consulta IRPF asalariada Madrid', async ({ page }) => {
    const consoleErrors: string[] = [];
    const networkErrors: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('requestfailed', req => {
      networkErrors.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText}`);
    });

    await loginAs(page, 'test.particular@impuestify.es', 'Test2026!');
    await shot(page, 'T03a-chat-loaded');

    // Encontrar el textarea / input del chat
    const chatInput = page.locator('textarea, input[placeholder*="pregunta"], input[placeholder*="escrib"], input[placeholder*="mensaje"]').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    const mensaje = 'Hola, soy asalariada en Madrid con un sueldo de 35.000 euros anuales. ¿Cuánto IRPF me corresponde?';

    const t0 = Date.now();
    await chatInput.fill(mensaje);
    await shot(page, 'T03a-message-typed');

    // Enviar con Enter o con boton
    await chatInput.press('Enter');
    // o click en boton enviar
    // await page.click('button[type="submit"], button[aria-label*="enviar"], button[aria-label*="Enviar"]');

    console.log('Message sent, waiting for SSE response...');

    // Esperar a que aparezca la respuesta del asistente
    // Timeout generoso: SSE puede tardar 30-90s en produccion
    let responseEl = null;
    try {
      responseEl = await page.waitForSelector(
        '[class*="assistant"], [class*="bot"], [data-role="assistant"], [class*="ai-message"], .message:last-child',
        { timeout: 90000 }
      );
    } catch (e) {
      console.log('Timeout waiting for assistant response');
    }

    const sseTime = Date.now() - t0;
    await shot(page, 'T03a-response-streaming');

    // Esperar a que el streaming termine (esperar a que no cambie el contenido)
    await page.waitForTimeout(5000);
    await shot(page, 'T03a-response-complete');

    const responseTime = Date.now() - t0;

    // Capturar el contenido de la respuesta
    const allMessages = await page.locator('[class*="message"], [class*="chat-item"], [role="listitem"]').all();
    let responseText = '';
    for (const msg of allMessages) {
      const text = await msg.textContent().catch(() => '');
      if (text && text.length > 50) responseText += text + '\n';
    }

    // Verificar contenido relevante
    const hasIRPF = responseText.toLowerCase().includes('irpf') || responseText.toLowerCase().includes('renta');
    const hasEuros = responseText.includes('€') || responseText.includes('euro') || responseText.includes('EUR');
    const hasTramos = responseText.toLowerCase().includes('tramo') || responseText.toLowerCase().includes('tipo');
    const hasMadrid = responseText.toLowerCase().includes('madrid');

    // Verificar DeductionCards
    const deductionCards = await page.locator('[class*="deduction"], [class*="DeductionCard"]').count();

    // Verificar si hay boton de export PDF o acciones
    const reportActions = await page.locator('[class*="ReportAction"], button:has-text("PDF"), button:has-text("Descargar")').count();

    console.log(`SSE first response time: ${sseTime}ms`);
    console.log(`Total response time: ${responseTime}ms`);
    console.log(`Response has IRPF: ${hasIRPF}`);
    console.log(`Response has euros: ${hasEuros}`);
    console.log(`Response has tramos: ${hasTramos}`);
    console.log(`Response mentions Madrid: ${hasMadrid}`);
    console.log(`DeductionCards found: ${deductionCards}`);
    console.log(`Report actions found: ${reportActions}`);
    console.log(`Console errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) console.log('ERRORS:', consoleErrors.slice(0, 5));
    console.log(`Network errors: ${networkErrors.length}`);
    if (networkErrors.length > 0) console.log('NETWORK:', networkErrors.slice(0, 5));

    expect(responseText.length, 'Should receive a response').toBeGreaterThan(50);
    expect(hasIRPF || hasEuros, 'Response should mention IRPF or euros').toBe(true);
  });

  test('T03b - Consulta deducciones Madrid', async ({ page }) => {
    await loginAs(page, 'test.particular@impuestify.es', 'Test2026!');

    const chatInput = page.locator('textarea, input[placeholder*="pregunta"], input[placeholder*="escrib"], input[placeholder*="mensaje"]').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    const t0 = Date.now();
    await chatInput.fill('¿Qué deducciones puedo aplicar en la Comunidad de Madrid?');
    await chatInput.press('Enter');

    console.log('Waiting for deductions response...');
    await page.waitForTimeout(60000); // Give it 60s for full response

    const responseTime = Date.now() - t0;
    await shot(page, 'T03b-deductions-response');

    const deductionCards = await page.locator('[class*="deduction"], [class*="DeductionCard"], [class*="deduction-card"]').count();
    const pageText = await page.content();

    const hasDeducciones = pageText.toLowerCase().includes('deducci') ||
      pageText.toLowerCase().includes('desgrava') ||
      pageText.toLowerCase().includes('reducci');

    console.log(`Response time: ${responseTime}ms`);
    console.log(`DeductionCards: ${deductionCards}`);
    console.log(`Content mentions deducciones: ${hasDeducciones}`);

    expect(hasDeducciones, 'Response should mention deducciones').toBe(true);
  });
});
