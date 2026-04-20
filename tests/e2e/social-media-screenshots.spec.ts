/**
 * Social Media Screenshots — Impuestify (Produccion)
 * =====================================================
 * Captura pantallas de alta calidad para redes sociales.
 * Guarda todas las capturas en: social_media/screenshots/
 *
 * Uso:
 *   npx playwright test tests/e2e/social-media-screenshots.spec.ts --headed
 *
 * Requiere que playwright.config.ts apunte a produccion o pasar BASE_URL:
 *   BASE_URL=https://impuestify.com npx playwright test tests/e2e/social-media-screenshots.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// ─── Config ───────────────────────────────────────────────────────────────────

const BASE_URL = 'https://impuestify.com';
const SCREENSHOTS_DIR = path.resolve(__dirname, '../../social_media/screenshots');
const API_URL = 'https://taxia-production.up.railway.app';

const USERS = {
  particular: {
    email: 'test.particular@impuestify.es',
    password: 'Test2026!',
  },
  autonomo: {
    email: 'test.autonomo@impuestify.es',
    password: 'Test2026!',
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Garantiza que el directorio de screenshots existe */
function ensureDir() {
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }
}

/** Guarda un screenshot con nombre numerado */
async function capture(page: Page, filename: string, fullPage = true) {
  ensureDir();
  const filepath = path.join(SCREENSHOTS_DIR, filename);
  await page.screenshot({ path: filepath, fullPage });
  console.log(`  Captura guardada: ${filename}`);
  return filepath;
}

/**
 * Navega a una URL y espera carga completa.
 * Hace scroll para triggear animaciones FadeContent antes de capturar.
 */
async function navigateAndWait(page: Page, url: string, extraWait = 2000) {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  // Scroll lento para triggear animaciones (FadeContent usa IntersectionObserver)
  await page.evaluate(async () => {
    await new Promise<void>((resolve) => {
      let totalScrolled = 0;
      const interval = setInterval(() => {
        window.scrollBy(0, 300);
        totalScrolled += 300;
        if (totalScrolled >= document.body.scrollHeight) {
          clearInterval(interval);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 150);
    });
  });
  await page.waitForTimeout(extraWait);
}

/**
 * Login via API REST (bypass Cloudflare Turnstile).
 * Inyecta tokens en localStorage y navega a la pagina protegida.
 */
async function loginViaApi(page: Page, email: string, password: string) {
  // Primero navegar al dominio para poder usar localStorage
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 20000 });

  // Llamar a la API de login directamente desde el contexto del navegador
  const result = await page.evaluate(
    async ({ apiUrl, email, password }) => {
      try {
        const res = await fetch(`${apiUrl}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
          const text = await res.text();
          return { ok: false, error: `HTTP ${res.status}: ${text}` };
        }
        const data = await res.json();
        return { ok: true, data };
      } catch (e: any) {
        return { ok: false, error: e.message };
      }
    },
    { apiUrl: API_URL, email, password }
  );

  if (!result.ok) {
    console.error(`Login fallido para ${email}: ${result.error}`);
    throw new Error(`Login fallido: ${result.error}`);
  }

  const { access_token, refresh_token } = result.data;

  // Inyectar tokens en localStorage
  await page.evaluate(
    ({ access_token, refresh_token }) => {
      localStorage.setItem('access_token', access_token);
      if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
    },
    { access_token, refresh_token }
  );

  console.log(`  Login OK para ${email}`);
  return { access_token, refresh_token };
}

/** Cierra modales de onboarding si aparecen */
async function dismissModals(page: Page) {
  // Intentar cerrar modal de tutorial
  try {
    const skipBtn = page.locator('button').filter({ hasText: /saltar tutorial/i }).first();
    await skipBtn.click({ timeout: 3000 });
    await page.waitForTimeout(800);
  } catch { /* no hay modal */ }

  // Intentar cerrar modal de IA
  try {
    const entendidoBtn = page.locator('button').filter({ hasText: /entendido/i }).first();
    await entendidoBtn.click({ timeout: 3000 });
    await page.waitForTimeout(800);
  } catch { /* no hay modal */ }

  // Intentar cerrar modal con X
  try {
    const closeBtn = page.locator('button[aria-label*="cerrar" i], button[aria-label*="close" i]').first();
    await closeBtn.click({ timeout: 2000 });
    await page.waitForTimeout(500);
  } catch { /* no hay modal */ }
}

// ─── Tests: Paginas Publicas ──────────────────────────────────────────────────

test.describe('01 — Paginas Publicas', () => {
  test.setTimeout(60000);

  test('01 Landing desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await navigateAndWait(page, BASE_URL, 3000);
    await capture(page, '01-landing-desktop.png');
  });

  test('02 Landing mobile', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await navigateAndWait(page, BASE_URL, 3000);
    await capture(page, '02-landing-mobile.png');
  });

  test('03 Login page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await navigateAndWait(page, `${BASE_URL}/login`, 2000);
    await capture(page, '03-login.png');
  });

  test('04 Register page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await navigateAndWait(page, `${BASE_URL}/register`, 2000);
    await capture(page, '04-register.png');
  });

  test('05 Subscribe page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await navigateAndWait(page, `${BASE_URL}/subscribe`, 2000);
    await capture(page, '05-subscribe.png');
  });

  test('06 Territorios forales', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    try {
      await navigateAndWait(page, `${BASE_URL}/territorios-forales`, 2000);
      const title = await page.title();
      if (!title.includes('404') && !title.includes('not found')) {
        await capture(page, '06-territorios-forales.png');
      } else {
        console.log('  Pagina territorios-forales no existe (404), saltando');
      }
    } catch (e) {
      console.log(`  Error en territorios-forales: ${e}`);
    }
  });

  test('07 Ceuta y Melilla', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    try {
      await navigateAndWait(page, `${BASE_URL}/ceuta-melilla`, 2000);
      await capture(page, '07-ceuta-melilla.png');
    } catch (e) {
      console.log(`  Error en ceuta-melilla: ${e}`);
    }
  });

  test('08 Canarias', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    try {
      await navigateAndWait(page, `${BASE_URL}/canarias`, 2000);
      await capture(page, '08-canarias.png');
    } catch (e) {
      console.log(`  Error en canarias: ${e}`);
    }
  });
});

// ─── Tests: Con Autenticacion (usuario particular) ───────────────────────────

test.describe('02 — Autenticado (particular)', () => {
  test.setTimeout(180000);

  test('09 Chat vacio desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/chat`, 3000);
    await dismissModals(page);
    await page.waitForTimeout(2000);
    await capture(page, '09-chat-vacio-desktop.png');
  });

  test('10 Chat con respuesta — alquiler Madrid', async ({ page }) => {
    test.setTimeout(180000);
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/chat`, 3000);
    await dismissModals(page);

    // Esperar a que el input de chat este disponible
    const chatInput = page.locator('[placeholder*="pregunta" i], [placeholder*="Escribe" i]').first();
    await chatInput.waitFor({ state: 'visible', timeout: 15000 });
    await chatInput.click();

    // Escribir el mensaje
    const question = '¿Cuánto puedo deducir por alquiler de vivienda habitual en Madrid?';
    await chatInput.fill(question);

    // Enviar con Enter o boton
    await chatInput.press('Enter');

    // Esperar a que aparezca alguna respuesta del assistant
    // El chat usa SSE — puede tardar hasta 120s
    console.log('  Esperando respuesta SSE del chat (hasta 120s)...');
    try {
      // Buscar el indicador de "escribiendo" o la respuesta
      await page.waitForFunction(
        () => {
          const msgs = document.querySelectorAll('[class*="message"], [class*="assistant"], [class*="response"]');
          return msgs.length > 0;
        },
        { timeout: 130000 }
      );
      await page.waitForTimeout(5000); // Dejar que el streaming avance
      await capture(page, '10-chat-respuesta-alquiler.png');
    } catch (e) {
      console.log(`  Timeout esperando respuesta del chat: ${e}`);
      await capture(page, '10-chat-respuesta-alquiler-timeout.png');
    }
  });

  test('11 Guia fiscal paso 1', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/guia-fiscal`, 3000);
    await capture(page, '11-guia-fiscal-paso1.png');
  });

  test('12 Guia fiscal — avanzar pasos y resultado', async ({ page }) => {
    test.setTimeout(60000);
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/guia-fiscal`, 3000);

    // Intentar rellenar datos minimos y avanzar
    try {
      // Seleccionar CCAA (Madrid)
      const ccaaSelect = page.locator('select').first();
      await ccaaSelect.waitFor({ state: 'visible', timeout: 5000 });
      await ccaaSelect.selectOption({ label: 'Madrid' });
      await page.waitForTimeout(500);

      // Rellenar ingresos trabajo
      const inputs = page.locator('input[type="number"]');
      const count = await inputs.count();
      if (count > 0) {
        await inputs.first().fill('35000');
      }

      // Boton siguiente
      const nextBtn = page.locator('button').filter({ hasText: /siguiente/i }).first();
      if (await nextBtn.isVisible()) {
        await nextBtn.click();
        await page.waitForTimeout(1000);
        await capture(page, '12a-guia-fiscal-paso2.png');

        // Seguir avanzando pasos
        for (let i = 0; i < 6; i++) {
          try {
            const btn = page.locator('button').filter({ hasText: /siguiente/i }).first();
            if (await btn.isVisible({ timeout: 2000 })) {
              await btn.click();
              await page.waitForTimeout(800);
            }
          } catch { break; }
        }
        await capture(page, '12b-guia-fiscal-resultado.png');
      }
    } catch (e) {
      console.log(`  No se pudo avanzar en guia fiscal: ${e}`);
      await capture(page, '12-guia-fiscal-solo-paso1.png');
    }
  });

  test('13 Settings', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/settings`, 3000);
    await capture(page, '13-settings.png');

    // Intentar capturar la tab de Perfil Fiscal
    try {
      const fiscalTab = page.locator('[role="tab"], button, a').filter({ hasText: /perfil fiscal/i }).first();
      await fiscalTab.click({ timeout: 3000 });
      await page.waitForTimeout(1000);
      await capture(page, '13b-settings-perfil-fiscal.png');
    } catch { /* tab no encontrada */ }
  });

  test('14 Calendario fiscal', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    try {
      await navigateAndWait(page, `${BASE_URL}/calendario`, 3000);
      // Verificar que no es un 404 ni redirect a login
      const url = page.url();
      if (!url.includes('/login') && !url.includes('/subscribe')) {
        await capture(page, '14-calendario-fiscal.png');
      } else {
        console.log(`  Calendario redirige a: ${url}, saltando`);
      }
    } catch (e) {
      console.log(`  Error en calendario: ${e}`);
    }
  });

  test('15 Crypto page', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    try {
      await navigateAndWait(page, `${BASE_URL}/crypto`, 3000);
      const url = page.url();
      if (!url.includes('/login') && !url.includes('/subscribe')) {
        await capture(page, '15-crypto.png');
      } else {
        console.log(`  Crypto redirige a: ${url}, saltando`);
      }
    } catch (e) {
      console.log(`  Error en crypto: ${e}`);
    }
  });
});

// ─── Tests: UX adicionales ────────────────────────────────────────────────────

test.describe('03 — UX adicionales', () => {
  test.setTimeout(180000);

  test('16 Chat mobile — con conversacion', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/chat`, 3000);
    await dismissModals(page);
    await page.waitForTimeout(1000);
    await capture(page, '16-chat-mobile.png');
  });

  test('17 Sidebar conversaciones — desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await loginViaApi(page, USERS.particular.email, USERS.particular.password);
    await navigateAndWait(page, `${BASE_URL}/chat`, 3000);
    await dismissModals(page);

    // Intentar abrir el sidebar si esta colapsado
    try {
      const sidebarToggle = page.locator('button').filter({ hasText: /sidebar|panel|conversacion/i }).first();
      await sidebarToggle.click({ timeout: 2000 });
      await page.waitForTimeout(500);
    } catch { /* sidebar puede ya estar abierto */ }

    await page.waitForTimeout(1000);
    await capture(page, '17-chat-sidebar-desktop.png');
  });

  test('18 Subscribe page mobile', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await navigateAndWait(page, `${BASE_URL}/subscribe`, 2000);
    await capture(page, '18-subscribe-mobile.png');
  });

  test('19 Landing — hero section closeup', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    // Screenshot solo del viewport visible (no full page) para capturar el hero
    const heroFile = path.join(SCREENSHOTS_DIR, '19-landing-hero-closeup.png');
    await page.screenshot({ path: heroFile, fullPage: false });
    console.log('  Captura guardada: 19-landing-hero-closeup.png');
  });

  test('20 Landing — pricing section', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await navigateAndWait(page, BASE_URL, 3000);

    // Scroll hasta la seccion de precios
    try {
      const pricingSection = page.locator('[id*="pricing"], [id*="precio"], section').filter({ hasText: /5.*€|39.*€|particular|autónomo/i }).first();
      await pricingSection.scrollIntoViewIfNeeded({ timeout: 5000 });
      await page.waitForTimeout(1500);
      const pricingFile = path.join(SCREENSHOTS_DIR, '20-landing-pricing.png');
      await page.screenshot({ path: pricingFile, fullPage: false });
      console.log('  Captura guardada: 20-landing-pricing.png');
    } catch (e) {
      console.log(`  No se encontro seccion de precios: ${e}`);
    }
  });
});
