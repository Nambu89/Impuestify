/**
 * QA Test: Guia Fiscal Wizard — MELILLA (deduccion 60% + IPSI)
 * Sesion: 2026-03-12
 * Escenario: Asalariado Melilla, 35 anos, soltero
 * Expected resultado: ~-2108 EUR (a devolver), deduccion_ceuta_melilla ~3588 EUR
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

const FRONTEND_URL = 'http://localhost:3001';
const BACKEND_URL = 'http://localhost:8000';

const JWT_PARTICULAR = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXBhcnRpY3VsYXItMDAwMDAwMDEiLCJlbWFpbCI6InRlc3QucGFydGljdWxhckBpbXB1ZXN0aWZ5LmVzIiwiZXhwIjoxNzczMzIwOTkzLCJpYXQiOjE3NzMzMTkxOTMsInR5cGUiOiJhY2Nlc3MifQ.9ReZKI_zmYaCJxHnUnv_hFElpCpHyx0e__TrYOv_REs';
const JWT_REFRESH = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXBhcnRpY3VsYXItMDAwMDAwMDEiLCJlbWFpbCI6InRlc3QucGFydGljdWxhckBpbXB1ZXN0aWZ5LmVzIiwiZXhwIjoxNzczOTIzOTkzLCJpYXQiOjE3NzMzMTkxOTMsInR5cGUiOiJyZWZyZXNoIn0.t_Kp1SMxBQfTMGSyiLK7X78QsN3leIRlt33BwL5ZJFI';

const SCREENSHOTS_DIR = path.join(
  'C:\\Users\\Fernando Prada\\OneDrive - SVAN TRADING SL\\Escritorio\\Personal\\Proyectos\\TaxIA',
  'tests', 'e2e', 'screenshots'
);

async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, `${name}.png`),
    fullPage: false,
  });
  console.log(`[SCREENSHOT] ${name}.png`);
}

async function injectJWT(page: Page) {
  await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ token, refresh }) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('refresh_token', refresh);
  }, { token: JWT_PARTICULAR, refresh: JWT_REFRESH });
}

test.describe('Guia Fiscal Wizard — Melilla (deduccion 60%)', () => {
  test.setTimeout(120000);

  test('TGM-01: Wizard completo asalariado Melilla 30k', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    // ===== SETUP: Inyectar JWT =====
    console.log('[SETUP] Inyectando JWT en localStorage...');
    await injectJWT(page);

    // ===== NAVEGACION a /guia-fiscal =====
    console.log('[NAV] Navegando a /guia-fiscal...');
    await page.goto(`${FRONTEND_URL}/guia-fiscal`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // Verificar que NO redirige a /subscribe (indicaria que el usuario no tiene acceso)
    const currentUrl = page.url();
    console.log(`[URL] URL actual: ${currentUrl}`);

    if (currentUrl.includes('/subscribe')) {
      await screenshot(page, 'TGM-FAIL-redirect-subscribe');
      throw new Error('FAIL: Redirigido a /subscribe — el usuario particular no tiene acceso a /guia-fiscal');
    }

    await screenshot(page, 'TGM-01-guia-entrada');

    // Verificar que el wizard carga (buscar paso 0)
    const wizardVisible = await page.locator('.tax-guide, .wizard, [class*="guide"], [class*="wizard"]').first().isVisible().catch(() => false);
    console.log(`[CHECK] Wizard visible: ${wizardVisible}`);

    // ===== PASO 0: DATOS PERSONALES =====
    console.log('[PASO 0] Seleccionando CCAA Melilla...');
    await page.waitForTimeout(1000);

    // Buscar el select de CCAA (puede ser un select nativo o un custom select)
    // Segun memoria: el select de CCAA en el wizard usa clase tg-field__select
    const ccaaSelect = page.locator('select.tg-field__select, select[name*="ccaa"], select[name*="comunidad"], select').first();

    try {
      await ccaaSelect.waitFor({ state: 'visible', timeout: 10000 });
      await ccaaSelect.selectOption('Melilla');
      console.log('[PASO 0] CCAA Melilla seleccionada');
    } catch (e) {
      console.log('[PASO 0] Select no encontrado con selector primario, intentando alternativas...');
      // Buscar cualquier select en el paso
      const allSelects = page.locator('select');
      const count = await allSelects.count();
      console.log(`[PASO 0] Selects encontrados: ${count}`);
      if (count > 0) {
        await allSelects.first().selectOption('Melilla');
        console.log('[PASO 0] CCAA seleccionada via selector generico');
      }
    }

    await page.waitForTimeout(1500);

    // Verificar que aparece el tip de Ceuta/Melilla (caja verde)
    const ccaaTipVisible = await page.locator('[class*="ccaa-tip"], [class*="CcaaTip"], [class*="ventaja"], [class*="tip"]').first().isVisible().catch(() => false);
    const pageText = await page.textContent('body');
    const hasCeutaMelillaTip = pageText?.toLowerCase().includes('ventaja fiscal') ||
                               pageText?.toLowerCase().includes('60%') ||
                               pageText?.toLowerCase().includes('ceuta') ||
                               pageText?.toLowerCase().includes('ipsi');

    console.log(`[CHECK] CcaaTip visible (selector): ${ccaaTipVisible}`);
    console.log(`[CHECK] Texto "ventaja/60%/ceuta/ipsi" en pagina: ${hasCeutaMelillaTip}`);

    await screenshot(page, 'TGM-02-paso0-ccaa-melilla');

    // Establecer edad 35
    const edadInput = page.locator('input[type="number"][placeholder*="edad"], input[name*="edad"], input[placeholder*="35"]').first();
    try {
      await edadInput.waitFor({ state: 'visible', timeout: 5000 });
      await edadInput.fill('35');
      console.log('[PASO 0] Edad 35 introducida');
    } catch (e) {
      console.log('[PASO 0] Campo edad no encontrado — puede ser opcional o diferente nombre');
      // Buscar inputs numericos en el paso 0
      const numberInputs = page.locator('input[type="number"]');
      const count = await numberInputs.count();
      console.log(`[PASO 0] Inputs numericos: ${count}`);
      for (let i = 0; i < count; i++) {
        const placeholder = await numberInputs.nth(i).getAttribute('placeholder');
        const name = await numberInputs.nth(i).getAttribute('name');
        console.log(`  Input ${i}: placeholder="${placeholder}", name="${name}"`);
      }
    }

    await screenshot(page, 'TGM-03-paso0-completo');

    // ===== SIGUIENTE (paso 0 -> 1) =====
    const nextBtn = page.locator('button.tg-nav__btn--primary, button:has-text("Siguiente")').first();
    await nextBtn.click({ timeout: 5000 });
    await page.waitForTimeout(1500);
    console.log('[NAV] Avanzado al paso 1');
    await screenshot(page, 'TGM-04-paso1-trabajo');

    // ===== PASO 1: INGRESOS TRABAJO =====
    console.log('[PASO 1] Rellenando ingresos trabajo...');

    // ingresos_trabajo: 30000
    const ingresosInput = page.locator('input[name*="ingresos_trabajo"], input[placeholder*="ingresos"], input[type="number"]').first();
    try {
      await ingresosInput.waitFor({ state: 'visible', timeout: 8000 });
      await ingresosInput.fill('30000');
      console.log('[PASO 1] ingresos_trabajo: 30000');
    } catch (e) {
      console.log('[PASO 1] ERROR: No se encontro campo ingresos_trabajo');
    }

    await page.waitForTimeout(500);

    // Rellenar todos los inputs numericos del paso 1 segun el escenario
    // ss_empleado: 1950, retenciones_trabajo: 4500
    const allInputs = page.locator('input[type="number"]');
    const inputCount = await allInputs.count();
    console.log(`[PASO 1] Total inputs numericos: ${inputCount}`);

    for (let i = 0; i < inputCount; i++) {
      const inp = allInputs.nth(i);
      const name = await inp.getAttribute('name') || '';
      const placeholder = await inp.getAttribute('placeholder') || '';
      console.log(`  Input ${i}: name="${name}", placeholder="${placeholder}"`);

      if (name.includes('ingresos_trabajo') || placeholder.toLowerCase().includes('ingresos bruto')) {
        await inp.fill('30000');
      } else if (name.includes('ss_empleado') || name.includes('seguridad_social') || placeholder.toLowerCase().includes('seguridad social')) {
        await inp.fill('1950');
      } else if (name.includes('retenciones_trabajo') || placeholder.toLowerCase().includes('retenci')) {
        await inp.fill('4500');
      }
    }

    await page.waitForTimeout(1000);
    await screenshot(page, 'TGM-05-paso1-rellenado');

    // ===== SIGUIENTE (paso 1 -> 2) =====
    await nextBtn.click({ timeout: 5000 });
    await page.waitForTimeout(1500);
    console.log('[NAV] Avanzado al paso 2');
    await screenshot(page, 'TGM-06-paso2-ahorro');

    // ===== PASO 2: AHORRO =====
    // intereses: 300
    const interesesInput = page.locator('input[name*="intereses"], input[type="number"]').first();
    try {
      await interesesInput.waitFor({ state: 'visible', timeout: 5000 });
      await interesesInput.fill('300');
      console.log('[PASO 2] intereses: 300');
    } catch (e) {
      console.log('[PASO 2] Campo intereses no encontrado');
    }

    await page.waitForTimeout(500);
    await screenshot(page, 'TGM-07-paso2-rellenado');

    // ===== NAVEGAR PASOS 3-6 (Skip) =====
    for (let paso = 3; paso <= 6; paso++) {
      await nextBtn.click({ timeout: 5000 }).catch(() => {
        console.log(`[NAV] Siguiente no disponible en paso ${paso}`);
      });
      await page.waitForTimeout(1500);
      console.log(`[NAV] Avanzado al paso ${paso}`);
      await screenshot(page, `TGM-08-paso${paso}-skip`);
    }

    // ===== PASO 7: RESULTADO =====
    console.log('[PASO 7] Esperando resultado...');
    await page.waitForTimeout(3000);
    await screenshot(page, 'TGM-09-paso7-resultado');

    // Verificar resultado
    const bodyText = await page.textContent('body') || '';

    // Buscar el importe de resultado (deberia ser ~-2108 o 2108)
    const resultadoMatch = bodyText.match(/[-]?\d{1,4}[,.]?\d{2,3}\s*€/g);
    console.log(`[RESULTADO] Importes encontrados: ${resultadoMatch?.slice(0, 10).join(', ')}`);

    // Verificar indicadores clave
    const hasDeduccionCeutaMelilla = bodyText.toLowerCase().includes('ceuta') ||
                                     bodyText.toLowerCase().includes('melilla') ||
                                     bodyText.includes('60%') ||
                                     bodyText.toLowerCase().includes('deducci');
    const hasDevolver = bodyText.toLowerCase().includes('devolver') ||
                        bodyText.toLowerCase().includes('a devolver') ||
                        bodyText.includes('-2');
    const has3588 = bodyText.includes('3.588') || bodyText.includes('3588');
    const has2108 = bodyText.includes('2.108') || bodyText.includes('2108') || bodyText.includes('2.107') || bodyText.includes('2107');

    console.log(`[CHECK] Deduccion Ceuta/Melilla visible: ${hasDeduccionCeutaMelilla}`);
    console.log(`[CHECK] Texto "a devolver" visible: ${hasDevolver}`);
    console.log(`[CHECK] Importe ~3588 (deduccion 60%) visible: ${has3588}`);
    console.log(`[CHECK] Importe ~2108 (resultado) visible: ${has2108}`);

    // Screenshot del resultado completo (fullPage)
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'TGM-10-resultado-fullpage.png'),
      fullPage: true,
    });
    console.log('[SCREENSHOT] TGM-10-resultado-fullpage.png (fullPage)');

    // ===== RESUMEN FINAL =====
    console.log('\n========== RESUMEN QA TEST TGM-01 ==========');
    console.log(`URL final: ${page.url()}`);
    console.log(`Errores de consola: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach(e => console.log(`  ERROR: ${e}`));
    }
    console.log(`CcaaTip Melilla visible: ${hasCeutaMelillaTip}`);
    console.log(`Deduccion 60% en resultado: ${hasDeduccionCeutaMelilla}`);
    console.log(`Resultado "a devolver": ${hasDevolver}`);
    console.log(`Importe deduccion ~3588: ${has3588}`);
    console.log(`Resultado ~-2108: ${has2108}`);
    console.log('=============================================\n');

    // Assertions suaves (no bloqueantes para recoger todo el reporte)
    if (!hasCeutaMelillaTip) {
      console.warn('[BUG] B-MELILLA-01: CcaaTip Ceuta/Melilla NO aparece en paso 0');
    }
    if (!hasDevolver) {
      console.warn('[BUG] B-MELILLA-02: El resultado no muestra "a devolver"');
    }
    if (!has3588) {
      console.warn('[BUG] B-MELILLA-03: La deduccion Ceuta/Melilla (~3588 EUR) no es visible en resultado');
    }
  });

  test('TGM-02: API directa — verificar calculo Melilla', async ({ request }) => {
    // Test de la API directamente (sin UI)
    const response = await request.post(`${BACKEND_URL}/api/irpf/estimate`, {
      headers: {
        'Authorization': `Bearer ${JWT_PARTICULAR}`,
        'Content-Type': 'application/json',
      },
      data: {
        comunidad_autonoma: 'Melilla',
        ingresos_trabajo: 30000,
        ss_empleado: 1950,
        retenciones_trabajo: 4500,
        intereses_cuentas: 300,
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log('\n========== API TEST TGM-02 ==========');
    console.log(`resultado_estimado: ${data.resultado_estimado}`);
    console.log(`deduccion_ceuta_melilla: ${data.deduccion_ceuta_melilla}`);
    console.log(`cuota_integra_general: ${data.cuota_integra_general}`);
    console.log(`cuota_liquida_total: ${data.cuota_liquida_total}`);
    console.log(`base_imponible_general: ${data.base_imponible_general}`);
    console.log(`tipo_medio_efectivo: ${data.tipo_medio_efectivo}%`);
    console.log('=====================================\n');

    // Verificaciones criticas
    expect(data.success).toBe(true);

    // Resultado debe ser negativo (a devolver)
    expect(data.resultado_estimado).toBeLessThan(0);
    console.log(`[PASS] resultado_estimado es negativo (${data.resultado_estimado})`);

    // La deduccion Ceuta/Melilla debe existir y ser ~60% de cuota_integra
    expect(data.deduccion_ceuta_melilla).toBeGreaterThan(0);
    const ratio = data.deduccion_ceuta_melilla / (data.cuota_integra_general + data.cuota_integra_ahorro);
    console.log(`[CHECK] Ratio deduccion/cuota_integra: ${(ratio * 100).toFixed(1)}% (esperado ~60%)`);
    expect(ratio).toBeGreaterThan(0.55);
    expect(ratio).toBeLessThan(0.65);

    // Verificar valores concretos
    const resultadoRedondeado = Math.abs(Math.round(data.resultado_estimado));
    const deduccionRedondeada = Math.round(data.deduccion_ceuta_melilla);

    console.log(`[CHECK] resultado ~2108: ${resultadoRedondeado} EUR`);
    console.log(`[CHECK] deduccion ~3588: ${deduccionRedondeada} EUR`);

    // Tolerancia de +-50 EUR por posibles redondeos
    expect(Math.abs(resultadoRedondeado - 2108)).toBeLessThan(50);
    expect(Math.abs(deduccionRedondeada - 3588)).toBeLessThan(50);

    console.log('[PASS] TGM-02: API Melilla calcula correctamente');
  });
});
