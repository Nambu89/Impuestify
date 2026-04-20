/**
 * Capterra Screenshots — Impuestify
 * Genera 5 capturas de alta calidad (1920x1080) para el listado de producto en Capterra.
 * Salida: frontend/public/images/capterra/
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

const BASE_URL = 'https://impuestify.com';
const OUTPUT_DIR = path.resolve(__dirname, '../../frontend/public/images/capterra');

const EMAIL = 'test.particular@impuestify.es';
const PASSWORD = 'Test2026!';

// ─── helpers ────────────────────────────────────────────────────────────────

async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(OUTPUT_DIR, name),
    fullPage: false,
  });
  console.log(`[OK] ${name} guardado`);
}

async function dismissModals(page: Page) {
  // Hasta 4 intentos para cerrar onboarding + modal IA
  for (let i = 0; i < 4; i++) {
    // Saltar tutorial (modal onboarding)
    const saltarBtn = page.locator('button').filter({ hasText: /saltar tutorial/i }).first();
    if (await saltarBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await saltarBtn.click({ force: true });
      await page.waitForTimeout(800);
    }
    // Cerrar modal IA
    const entendidoBtn = page.locator('button').filter({ hasText: /entendido/i }).first();
    if (await entendidoBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await entendidoBtn.click({ force: true });
      await page.waitForTimeout(800);
    }
    // Verificar si el chat input ya es accesible
    const chatInput = page.locator('[placeholder*="pregunta" i]').first();
    const isReady = await chatInput.isVisible({ timeout: 1500 }).catch(() => false);
    if (isReady) break;
  }
}

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 });
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/chat`, { timeout: 25000 });
  console.log('[OK] Login completado');
}

// ─── tests ──────────────────────────────────────────────────────────────────

test.describe('Capterra Screenshots', () => {
  test.setTimeout(300000); // 5 min — SSE puede tardar hasta 120s

  test('1 — Landing Page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    // Esperar a que el hero sea visible
    await page.waitForSelector('h1, .hero, [class*="hero"]', { timeout: 15000 });
    // Pequeña pausa para que las animaciones CSS terminen
    await page.waitForTimeout(2000);
    await screenshot(page, 'screenshot-landing.png');
  });

  test('2 — Login page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('input[type="email"]', { timeout: 10000 });
    await page.waitForTimeout(1000);
    await screenshot(page, 'screenshot-login.png');
  });

  test('3 — Chat con respuesta', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await login(page);
    await page.waitForTimeout(2000);

    // Cerrar modales si existen
    await dismissModals(page);

    // Verificar que el chat input está listo
    const chatInput = page.locator('[placeholder*="pregunta" i]').first();
    await expect(chatInput).toBeVisible({ timeout: 15000 });

    // Enviar pregunta sobre deducciones IRPF
    const mensaje = '¿Qué deducciones puedo aplicar en mi declaración IRPF?';
    await chatInput.fill(mensaje);
    await chatInput.press('Enter');

    console.log('[...] Esperando respuesta SSE completa del chat (hasta 120s)...');

    // Esperar a que desaparezca el spinner "Procesando" y aparezca contenido real
    // El spinner tiene texto "Procesando tu consulta..."
    await page.waitForFunction(
      () => {
        const processingEl = document.querySelector('[class*="processing"], [class*="thinking"], [class*="loading"]');
        const allText = document.body.innerText;
        // La respuesta debe tener contenido sustancial Y no estar en estado "procesando"
        const hasContent = allText.length > 800 && (
          allText.includes('deducción') ||
          allText.includes('IRPF') ||
          allText.includes('deducir') ||
          allText.includes('reducción') ||
          allText.includes('vivienda') ||
          allText.includes('maternidad')
        );
        // Verificar que el loader "Procesando tu consulta..." ya no es visible
        const isStillProcessing = allText.includes('Procesando tu consulta');
        return hasContent && !isStillProcessing;
      },
      { timeout: 120000, polling: 2000 }
    );

    // Esperar 3s más para que el streaming termine completamente
    await page.waitForTimeout(3000);

    await screenshot(page, 'screenshot-chat.png');
  });

  test('4 — Guía Fiscal wizard', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await login(page);
    await page.waitForTimeout(1500);
    await dismissModals(page);

    // Navegar a /guia-fiscal
    await page.goto(`${BASE_URL}/guia-fiscal`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Verificar que no redirige (plan particular puede o no tener acceso)
    const currentUrl = page.url();
    if (currentUrl.includes('/subscribe')) {
      console.warn('[WARN] /guia-fiscal redirige a /subscribe para este usuario — tomando screenshot de subscribe');
      await screenshot(page, 'screenshot-guia-fiscal.png');
      return;
    }

    // Esperar el wizard
    await page.waitForSelector(
      '.tax-guide, [class*="tax-guide"], .tg-progress, select.tg-field__select, h1',
      { timeout: 15000 }
    );
    await page.waitForTimeout(1500);
    await screenshot(page, 'screenshot-guia-fiscal.png');
  });

  test('5 — Calendario fiscal', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await login(page);
    await page.waitForTimeout(2000);
    await dismissModals(page);

    // El nav tiene "Calendario" como link — verificado en capturas previas del chat
    // Usar click en el nav link visible en el header
    console.log('[INFO] Buscando link Calendario en el header...');

    // Snapshot del accessibility tree para identificar el selector exacto
    // El header muestra: Chat | Guia Fiscal | Modelos | Calendario | Configuración
    // Usar evaluación JS para encontrar y clickar el link
    const clicked = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('a, button'));
      const calLink = links.find(el =>
        el.textContent?.trim().toLowerCase() === 'calendario' ||
        (el as HTMLAnchorElement).href?.includes('calendar')
      );
      if (calLink) {
        (calLink as HTMLElement).click();
        return (calLink as HTMLAnchorElement).href || calLink.textContent;
      }
      return null;
    });
    console.log(`[INFO] Link Calendario clickado: ${clicked}`);

    await page.waitForTimeout(3000);
    const urlAfter = page.url();
    console.log(`[INFO] URL tras click: ${urlAfter}`);

    // Esperar contenido del calendario
    await page.waitForSelector('h1, h2, table, [class*="calendar"], [class*="fiscal"]', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1500);

    // Navegar al mes con más plazos (Jun tiene 2 puntos en el selector de meses)
    const junBtn = page.locator('button, span').filter({ hasText: /^jun$/i }).first();
    if (await junBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await junBtn.click();
      await page.waitForTimeout(1500);
      console.log('[INFO] Navegando a Junio (más plazos)');
    }

    await screenshot(page, 'screenshot-calendario.png');
    console.log('[OK] Screenshot calendario tomado');
  });
});
