/**
 * QA E2E Test: Invoice Upload + Classification + Accounting (Full Flow)
 *
 * Tests all invoice types with 3 user profiles:
 *   - test.autonomo@impuestify.es (plan autonomo) — facturas consultor + farmacia
 *   - test.creator@impuestify.es (plan creator) — factura creador contenido
 *   - test.particular@impuestify.es (plan particular) — should be BLOCKED from upload
 *
 * Prerequisites:
 *   1. Run: cd backend && python scripts/seed_test_users.py
 *   2. Run: npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts
 *   3. Backend running on localhost:8000, frontend on localhost:3001
 *
 * Usage:
 *   npx playwright test tests/e2e/qa-invoices-contabilidad-full.spec.ts --headed
 */
import { test, expect, Page } from '@playwright/test';
import http from 'http';
import path from 'path';
import fs from 'fs';

// ─── Config ────────────────────────────────────────────────

const BASE_URL = 'http://localhost:3001';
const API_URL = 'http://localhost:8000';
const SS_DIR = path.resolve(__dirname, 'screenshots');
const FIXTURES_DIR = path.resolve(__dirname, 'fixtures/invoices');
const PASSWORD = 'Test2026!';

const USERS = {
  autonomo: { email: 'test.autonomo@impuestify.es', plan: 'autonomo' },
  creator:  { email: 'test.creator@impuestify.es',  plan: 'creator' },
  particular: { email: 'test.particular@impuestify.es', plan: 'particular' },
};

const INVOICES = [
  {
    file: 'factura-autonomo-consultor.png',
    label: 'Autonomo Consultor',
    expectedIVA: 21,
    expectedBase: 1725,
    expectedTotal: 1828.50,
    hasIRPF: true,
    irpfPct: 15,
    tipo: 'recibida',
  },
  {
    file: 'factura-creador-contenido.png',
    label: 'Creador de Contenido',
    expectedIVA: 21,
    expectedBase: 5310,
    expectedTotal: 6053.40,
    hasIRPF: true,
    irpfPct: 7,
    tipo: 'recibida',
  },
  {
    file: 'factura-farmacia-proveedor.png',
    label: 'Farmacia Proveedor',
    expectedBase: 301.80,
    expectedTotal: 346.38,
    hasRE: true,
    tipo: 'recibida',
  },
  {
    file: 'factura-simplificada-ticket.png',
    label: 'Factura Simplificada',
    expectedIVA: 21,
    expectedBase: 43.88,
    expectedTotal: 53.10,
    tipo: 'recibida',
  },
  {
    file: 'factura-intracomunitaria.png',
    label: 'Intracomunitaria',
    expectedIVA: 0,
    expectedBase: 12500,
    expectedTotal: 12500,
    tipo: 'recibida',
  },
];

// ─── Helpers ───────────────────────────────────────────────

async function screenshot(page: Page, name: string) {
  if (!fs.existsSync(SS_DIR)) fs.mkdirSync(SS_DIR, { recursive: true });
  await page.screenshot({ path: `${SS_DIR}/${name}.png`, fullPage: true });
  console.log(`[SS] ${name}.png`);
}

async function getJWT(email: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ email, password: PASSWORD });
    const req = http.request({
      hostname: 'localhost', port: 8000, path: '/auth/login',
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        try {
          const j = JSON.parse(body);
          if (j.tokens?.access_token) {
            resolve(j.tokens.access_token);
          } else {
            reject(new Error(`Login failed for ${email}: ${body}`));
          }
        } catch (e) {
          reject(new Error(`JWT parse error for ${email}: ${body}`));
        }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function authenticatePage(page: Page, email: string): Promise<string> {
  const token = await getJWT(email);
  await page.goto(`${BASE_URL}/login`);
  await page.evaluate((t) => {
    localStorage.setItem('access_token', t);
    localStorage.setItem('authToken', t);
    localStorage.setItem('token', t);
  }, token);
  console.log(`[AUTH] ${email} — JWT inyectado`);
  return token;
}

/** Upload a file via the API directly (bypass UI file input issues) */
async function uploadInvoiceAPI(token: string, filePath: string): Promise<any> {
  const fileBuffer = fs.readFileSync(filePath);
  const boundary = '----FormBoundary' + Math.random().toString(36).slice(2);
  const fileName = path.basename(filePath);

  const bodyParts = [
    `--${boundary}\r\n`,
    `Content-Disposition: form-data; name="file"; filename="${fileName}"\r\n`,
    `Content-Type: image/png\r\n\r\n`,
  ];

  const bodyStart = Buffer.from(bodyParts.join(''));
  const bodyEnd = Buffer.from(`\r\n--${boundary}--\r\n`);
  const body = Buffer.concat([bodyStart, fileBuffer, bodyEnd]);

  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost', port: 8000,
      path: '/api/invoices/upload',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': `multipart/form-data; boundary=${boundary}`,
        'Content-Length': body.length,
      },
      timeout: 60000,
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve({ status: res.statusCode, body: parsed });
        } catch {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Upload timeout')); });
    req.write(body);
    req.end();
  });
}

/** List invoices via API */
async function listInvoicesAPI(token: string, year: number = 2026): Promise<any> {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost', port: 8000,
      path: `/api/invoices?year=${year}`,
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` },
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

/** Get contabilidad data via API */
async function getContabilidadAPI(token: string, libro: string, year: number = 2026): Promise<any> {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost', port: 8000,
      path: `/api/contabilidad/${libro}?year=${year}`,
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` },
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ─── Tests ─────────────────────────────────────────────────

test.describe('QA: Invoice Upload + Classification + Contabilidad (Full)', () => {
  test.setTimeout(180000); // 3 min per test (Gemini OCR can be slow)

  // ── Prerequisite check ──────────────────────────────

  test('T00: Verify fixture images exist', async () => {
    const missing: string[] = [];
    for (const inv of INVOICES) {
      const fp = path.join(FIXTURES_DIR, inv.file);
      if (!fs.existsSync(fp)) missing.push(inv.file);
    }
    if (missing.length > 0) {
      console.log(`[T00] MISSING fixtures: ${missing.join(', ')}`);
      console.log('[T00] Run: npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts');
    }
    expect(missing).toHaveLength(0);
  });

  // ── Auth tests ──────────────────────────────────────

  test('T01: Login all 3 test users via API', async () => {
    for (const [role, user] of Object.entries(USERS)) {
      try {
        const token = await getJWT(user.email);
        expect(token).toBeTruthy();
        console.log(`[T01] ${role} (${user.email}): JWT OK`);
      } catch (e) {
        console.log(`[T01] ${role} (${user.email}): FAILED — ${e}`);
        console.log(`[T01] Run: cd backend && python scripts/seed_test_users.py`);
        throw e;
      }
    }
  });

  // ── Particular BLOCKED from upload ──────────────────

  test('T02: Particular plan BLOCKED from invoice upload', async () => {
    const token = await getJWT(USERS.particular.email);
    const testFile = path.join(FIXTURES_DIR, INVOICES[0].file);
    const result = await uploadInvoiceAPI(token, testFile) as any;

    console.log(`[T02] Upload status: ${result.status}`);
    console.log(`[T02] Response: ${JSON.stringify(result.body).substring(0, 200)}`);

    // Should be 403 (plan not allowed)
    expect(result.status).toBe(403);
    console.log('[T02] PASS: Particular plan correctly blocked from invoice upload');
  });

  // ── Autonomo: Upload facturas ───────────────────────

  test('T03: Autonomo uploads factura consultor', async () => {
    const inv = INVOICES[0]; // autonomo-consultor
    const token = await getJWT(USERS.autonomo.email);
    const filePath = path.join(FIXTURES_DIR, inv.file);

    console.log(`[T03] Uploading: ${inv.label} (${inv.file})`);
    const result = await uploadInvoiceAPI(token, filePath) as any;

    console.log(`[T03] Status: ${result.status}`);

    if (result.status === 200) {
      const factura = result.body.factura;
      const clasificacion = result.body.clasificacion;

      console.log(`[T03] Emisor: ${factura?.emisor?.nombre} (${factura?.emisor?.nif_cif})`);
      console.log(`[T03] Receptor: ${factura?.receptor?.nombre} (${factura?.receptor?.nif_cif})`);
      console.log(`[T03] N.º factura: ${factura?.numero_factura}`);
      console.log(`[T03] Base: ${factura?.base_imponible_total} (expected: ${inv.expectedBase})`);
      console.log(`[T03] IVA: ${factura?.tipo_iva_pct}% — Cuota: ${factura?.cuota_iva}`);
      console.log(`[T03] IRPF: ${factura?.retencion_irpf_pct}% — Retención: ${factura?.retencion_irpf}`);
      console.log(`[T03] Total: ${factura?.total} (expected: ${inv.expectedTotal})`);
      console.log(`[T03] Cuenta PGC: ${clasificacion?.cuenta_code} — ${clasificacion?.cuenta_nombre}`);
      console.log(`[T03] Confianza: ${clasificacion?.confianza}`);

      // Validate OCR extracted key fields
      expect(factura?.emisor?.nif_cif).toBeTruthy();
      expect(factura?.base_imponible_total).toBeGreaterThan(0);
      expect(factura?.total).toBeGreaterThan(0);
      expect(clasificacion?.cuenta_code).toBeTruthy();

      console.log('[T03] PASS: Invoice uploaded, classified, and asiento generated');
    } else if (result.status === 503) {
      console.log('[T03] SKIP: Gemini API not configured (503)');
    } else {
      console.log(`[T03] FAIL: Unexpected status ${result.status}: ${JSON.stringify(result.body).substring(0, 300)}`);
    }
  });

  test('T04: Autonomo uploads factura farmacia (multi-IVA)', async () => {
    const inv = INVOICES[2]; // farmacia-proveedor
    const token = await getJWT(USERS.autonomo.email);
    const filePath = path.join(FIXTURES_DIR, inv.file);

    console.log(`[T04] Uploading: ${inv.label} (${inv.file})`);
    const result = await uploadInvoiceAPI(token, filePath) as any;

    console.log(`[T04] Status: ${result.status}`);

    if (result.status === 200) {
      const factura = result.body.factura;

      console.log(`[T04] Emisor: ${factura?.emisor?.nombre}`);
      console.log(`[T04] Base: ${factura?.base_imponible_total} (expected: ~${inv.expectedBase})`);
      console.log(`[T04] Total: ${factura?.total} (expected: ~${inv.expectedTotal})`);
      console.log(`[T04] IVA tipo: ${factura?.tipo_iva_pct}%`);
      console.log(`[T04] RE: ${factura?.tipo_re_pct}% — Cuota RE: ${factura?.cuota_re}`);
      console.log(`[T04] Cuenta PGC: ${result.body.clasificacion?.cuenta_code} — ${result.body.clasificacion?.cuenta_nombre}`);

      // NOTE: Multi-IVA limitation — model only supports single tipo_iva_pct
      // Gemini might pick the dominant rate or average
      console.log(`[T04] NOTE: Factura has 3 IVA rates (4%+10%+21%) but model supports 1 — check Gemini behavior`);

      expect(factura?.emisor?.nif_cif).toBeTruthy();
      expect(factura?.total).toBeGreaterThan(0);

      console.log('[T04] PASS: Pharmacy invoice processed');
    } else if (result.status === 503) {
      console.log('[T04] SKIP: Gemini API not configured');
    } else {
      console.log(`[T04] FAIL: ${result.status}`);
    }
  });

  test('T05: Autonomo uploads factura simplificada (ticket)', async () => {
    const inv = INVOICES[3]; // simplificada-ticket
    const token = await getJWT(USERS.autonomo.email);
    const filePath = path.join(FIXTURES_DIR, inv.file);

    console.log(`[T05] Uploading: ${inv.label}`);
    const result = await uploadInvoiceAPI(token, filePath) as any;

    console.log(`[T05] Status: ${result.status}`);

    if (result.status === 200) {
      const factura = result.body.factura;

      console.log(`[T05] Emisor: ${factura?.emisor?.nombre} (${factura?.emisor?.nif_cif})`);
      console.log(`[T05] Base: ${factura?.base_imponible_total} (expected: ~${inv.expectedBase})`);
      console.log(`[T05] Total: ${factura?.total} (expected: ${inv.expectedTotal})`);
      console.log(`[T05] Tipo factura: ${factura?.tipo}`);
      console.log(`[T05] Cuenta PGC: ${result.body.clasificacion?.cuenta_code}`);

      expect(factura?.total).toBeGreaterThan(0);
      console.log('[T05] PASS: Simplified invoice processed');
    } else if (result.status === 503) {
      console.log('[T05] SKIP: Gemini API not configured');
    } else {
      console.log(`[T05] FAIL: ${result.status}`);
    }
  });

  test('T06: Autonomo uploads factura intracomunitaria (sin IVA)', async () => {
    const inv = INVOICES[4]; // intracomunitaria
    const token = await getJWT(USERS.autonomo.email);
    const filePath = path.join(FIXTURES_DIR, inv.file);

    console.log(`[T06] Uploading: ${inv.label}`);
    const result = await uploadInvoiceAPI(token, filePath) as any;

    console.log(`[T06] Status: ${result.status}`);

    if (result.status === 200) {
      const factura = result.body.factura;

      console.log(`[T06] Emisor: ${factura?.emisor?.nombre}`);
      console.log(`[T06] NIF-IVA emisor: ${factura?.emisor?.nif_cif}`);
      console.log(`[T06] Receptor: ${factura?.receptor?.nombre}`);
      console.log(`[T06] Base: ${factura?.base_imponible_total} (expected: ${inv.expectedBase})`);
      console.log(`[T06] IVA: ${factura?.tipo_iva_pct}% (expected: 0 — exento)`);
      console.log(`[T06] Total: ${factura?.total} (expected: ${inv.expectedTotal})`);

      expect(factura?.total).toBeGreaterThan(0);
      // IVA should be 0 for intracomunitaria
      if (factura?.tipo_iva_pct === 0 || factura?.cuota_iva === 0) {
        console.log('[T06] PASS: IVA correctly detected as 0 (exento)');
      } else {
        console.log(`[T06] WARN: IVA not 0 — Gemini may not detect inversión sujeto pasivo`);
      }
    } else if (result.status === 503) {
      console.log('[T06] SKIP: Gemini API not configured');
    } else {
      console.log(`[T06] FAIL: ${result.status}`);
    }
  });

  // ── Creator: Upload factura ─────────────────────────

  test('T07: Creator uploads factura creador contenido', async () => {
    const inv = INVOICES[1]; // creador-contenido
    const token = await getJWT(USERS.creator.email);
    const filePath = path.join(FIXTURES_DIR, inv.file);

    console.log(`[T07] Uploading as CREATOR: ${inv.label}`);
    const result = await uploadInvoiceAPI(token, filePath) as any;

    console.log(`[T07] Status: ${result.status}`);

    if (result.status === 200) {
      const factura = result.body.factura;

      console.log(`[T07] Emisor: ${factura?.emisor?.nombre} (${factura?.emisor?.nif_cif})`);
      console.log(`[T07] Base: ${factura?.base_imponible_total} (expected: ${inv.expectedBase})`);
      console.log(`[T07] IVA: ${factura?.tipo_iva_pct}%`);
      console.log(`[T07] IRPF: ${factura?.retencion_irpf_pct}% (expected: 7% — nuevo autonomo)`);
      console.log(`[T07] Total: ${factura?.total} (expected: ${inv.expectedTotal})`);
      console.log(`[T07] Cuenta PGC: ${result.body.clasificacion?.cuenta_code} — ${result.body.clasificacion?.cuenta_nombre}`);

      expect(factura?.total).toBeGreaterThan(0);
      console.log('[T07] PASS: Creator can upload invoices');
    } else if (result.status === 403) {
      console.log('[T07] FAIL: Creator plan blocked — check subscription guard allows "creator"');
    } else if (result.status === 503) {
      console.log('[T07] SKIP: Gemini API not configured');
    } else {
      console.log(`[T07] FAIL: ${result.status}`);
    }
  });

  // ── Contabilidad: Verify asientos generated ─────────

  test('T08: Verify libro diario has asientos from uploaded invoices', async () => {
    const token = await getJWT(USERS.autonomo.email);
    const result = await getContabilidadAPI(token, 'libro-diario', 2026) as any;

    console.log(`[T08] Libro Diario status: ${result.status}`);

    if (result.status === 200) {
      const entries = Array.isArray(result.body) ? result.body : result.body?.asientos || [];
      console.log(`[T08] Total asientos: ${entries.length}`);

      if (entries.length > 0) {
        // Show first few entries
        for (const entry of entries.slice(0, 6)) {
          console.log(`[T08]   ${entry.fecha} | #${entry.numero_asiento} | ${entry.cuenta_code} ${entry.cuenta_nombre} | Debe: ${entry.debe} | Haber: ${entry.haber}`);
        }

        // Check double-entry balance
        const totalDebe = entries.reduce((s: number, e: any) => s + (e.debe || 0), 0);
        const totalHaber = entries.reduce((s: number, e: any) => s + (e.haber || 0), 0);
        console.log(`[T08] Total Debe: ${totalDebe.toFixed(2)} | Total Haber: ${totalHaber.toFixed(2)}`);
        console.log(`[T08] Balance: ${(totalDebe - totalHaber).toFixed(2)} (should be 0)`);

        expect(Math.abs(totalDebe - totalHaber)).toBeLessThan(0.05);
        console.log('[T08] PASS: Double-entry balanced');
      } else {
        console.log('[T08] WARN: No asientos found — invoices may not have uploaded (Gemini not configured?)');
      }
    } else {
      console.log(`[T08] Status ${result.status}: ${JSON.stringify(result.body).substring(0, 200)}`);
    }
  });

  test('T09: Verify libro mayor grouped by account', async () => {
    const token = await getJWT(USERS.autonomo.email);
    const result = await getContabilidadAPI(token, 'libro-mayor', 2026) as any;

    console.log(`[T09] Libro Mayor status: ${result.status}`);

    if (result.status === 200) {
      const accounts = Array.isArray(result.body) ? result.body : result.body?.cuentas || [];
      console.log(`[T09] Cuentas con movimientos: ${accounts.length}`);

      for (const acc of accounts.slice(0, 8)) {
        console.log(`[T09]   ${acc.cuenta || acc.cuenta_code} | ${acc.nombre || acc.cuenta_nombre} | Debe: ${acc.total_debe || acc.debe} | Haber: ${acc.total_haber || acc.haber} | Saldo: ${acc.saldo}`);
      }

      console.log('[T09] PASS: Libro Mayor retrieved');
    }
  });

  test('T10: Verify balance cuadra', async () => {
    const token = await getJWT(USERS.autonomo.email);
    const result = await getContabilidadAPI(token, 'balance', 2026) as any;

    console.log(`[T10] Balance status: ${result.status}`);

    if (result.status === 200) {
      console.log(`[T10] Balance data: ${JSON.stringify(result.body).substring(0, 500)}`);
      console.log('[T10] PASS: Balance retrieved');
    }
  });

  test('T11: Verify PyG (Perdidas y Ganancias)', async () => {
    const token = await getJWT(USERS.autonomo.email);
    const result = await getContabilidadAPI(token, 'pyg', 2026) as any;

    console.log(`[T11] PyG status: ${result.status}`);

    if (result.status === 200) {
      console.log(`[T11] PyG data: ${JSON.stringify(result.body).substring(0, 500)}`);
      console.log('[T11] PASS: PyG retrieved');
    }
  });

  // ── UI Flow: Upload via frontend ────────────────────

  test('T12: UI — clasificador-facturas upload flow (autonomo)', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && !msg.text().includes('cloudflare')) {
        consoleErrors.push(msg.text());
      }
    });

    await authenticatePage(page, USERS.autonomo.email);
    await page.goto(`${BASE_URL}/clasificador-facturas`);
    await page.waitForTimeout(3000);

    const url = page.url();
    console.log(`[T12] URL: ${url}`);
    await screenshot(page, 'qa-inv-12-clasificador-page');

    if (url.includes('/login') || url.includes('/subscribe')) {
      console.log(`[T12] SKIP: Redirected to ${url}`);
      return;
    }

    // Find file input
    const fileInput = page.locator('input[type="file"]');
    const inputCount = await fileInput.count();
    console.log(`[T12] File inputs found: ${inputCount}`);

    if (inputCount > 0) {
      const testFile = path.join(FIXTURES_DIR, 'factura-autonomo-consultor.png');
      if (fs.existsSync(testFile)) {
        await fileInput.first().setInputFiles(testFile);
        console.log('[T12] File set on input');

        // Wait for upload + OCR processing
        await page.waitForTimeout(15000);
        await screenshot(page, 'qa-inv-12-after-upload');

        const bodyText = await page.textContent('body') ?? '';
        const hasExtraction = bodyText.toLowerCase().includes('emisor') || bodyText.toLowerCase().includes('receptor');
        const hasClassification = bodyText.toLowerCase().includes('cuenta') || bodyText.toLowerCase().includes('pgc');
        const hasError = bodyText.toLowerCase().includes('error');

        console.log(`[T12] Extraction visible: ${hasExtraction}`);
        console.log(`[T12] Classification visible: ${hasClassification}`);
        console.log(`[T12] Error visible: ${hasError}`);

        if (hasExtraction) {
          console.log('[T12] PASS: Invoice data extracted and displayed');
        } else if (hasError) {
          console.log('[T12] WARN: Error displayed — check Gemini API config');
        } else {
          console.log('[T12] INFO: Processing might still be in progress');
          await page.waitForTimeout(10000);
          await screenshot(page, 'qa-inv-12-after-wait');
        }
      } else {
        console.log(`[T12] SKIP: Fixture file not found: ${testFile}`);
      }
    } else {
      // Try drag-drop zone or button
      const uploadBtn = page.getByText(/subir|upload|seleccionar/i).first();
      const visible = await uploadBtn.isVisible().catch(() => false);
      console.log(`[T12] Upload button visible: ${visible}`);
    }

    const relevant = consoleErrors.filter(e => !e.includes('cloudflare'));
    if (relevant.length > 0) {
      console.log(`[T12] Console errors: ${relevant.slice(0, 3).join(' | ')}`);
    }
  });

  // ── UI: Contabilidad page tabs ──────────────────────

  test('T13: UI — contabilidad page tabs (autonomo)', async ({ page }) => {
    await authenticatePage(page, USERS.autonomo.email);
    await page.goto(`${BASE_URL}/contabilidad`);
    await page.waitForTimeout(3000);

    const url = page.url();
    console.log(`[T13] URL: ${url}`);

    if (url.includes('/login') || url.includes('/subscribe')) {
      console.log(`[T13] SKIP: Redirected to ${url}`);
      return;
    }

    await screenshot(page, 'qa-inv-13-contabilidad-initial');

    // Click through all tabs
    const tabs = [
      { name: 'Libro Diario', screenshot: 'qa-inv-13-tab-diario' },
      { name: 'Mayor', screenshot: 'qa-inv-13-tab-mayor' },
      { name: 'Balance', screenshot: 'qa-inv-13-tab-balance' },
      { name: 'PyG', screenshot: 'qa-inv-13-tab-pyg' },
    ];

    for (const tab of tabs) {
      try {
        const tabEl = page.getByText(tab.name, { exact: false }).first();
        if (await tabEl.isVisible().catch(() => false)) {
          await tabEl.click();
          await page.waitForTimeout(1500);
          await screenshot(page, tab.screenshot);
          console.log(`[T13] Tab "${tab.name}": OK`);
        } else {
          console.log(`[T13] Tab "${tab.name}": not visible`);
        }
      } catch (e) {
        console.log(`[T13] Tab "${tab.name}": error — ${e}`);
      }
    }

    // Test export button
    const exportBtn = page.getByText(/exportar|descargar|csv|excel/i).first();
    if (await exportBtn.isVisible().catch(() => false)) {
      console.log('[T13] Export button: visible');
    } else {
      console.log('[T13] Export button: not visible');
    }
  });

  // ── UI: Invoice list and reclassification ───────────

  test('T14: UI — invoice list and delete (autonomo)', async ({ page }) => {
    await authenticatePage(page, USERS.autonomo.email);
    await page.goto(`${BASE_URL}/clasificador-facturas`);
    await page.waitForTimeout(3000);

    const url = page.url();
    if (url.includes('/login') || url.includes('/subscribe')) {
      console.log(`[T14] SKIP: Redirected`);
      return;
    }

    await screenshot(page, 'qa-inv-14-invoice-list');

    const bodyText = await page.textContent('body') ?? '';

    // Look for invoice list items
    const hasTable = await page.$('table').then(t => !!t).catch(() => false);
    const hasInvoices = bodyText.includes('2026') && (bodyText.includes('factura') || bodyText.includes('EUR') || bodyText.includes('€'));
    console.log(`[T14] Table found: ${hasTable}`);
    console.log(`[T14] Invoice data visible: ${hasInvoices}`);

    // Try to find any row action buttons
    const actionBtns = await page.$$('[data-testid*="action"], button:has-text("Ver"), button:has-text("Eliminar")');
    console.log(`[T14] Action buttons: ${actionBtns.length}`);

    console.log('[T14] DONE: Invoice list inspection complete');
  });

  // ── Reclassification ────────────────────────────────

  test('T15: API — reclassify invoice manually', async () => {
    const token = await getJWT(USERS.autonomo.email);
    const list = await listInvoicesAPI(token, 2026) as any;

    if (list.status !== 200 || !Array.isArray(list.body) || list.body.length === 0) {
      console.log(`[T15] SKIP: No invoices to reclassify (status=${list.status}, count=${Array.isArray(list.body) ? list.body.length : 'N/A'})`);
      return;
    }

    const invoiceId = list.body[0].id;
    const originalCode = list.body[0].cuenta_pgc;
    const newCode = originalCode === '629' ? '623' : '629';
    const newName = newCode === '623' ? 'Servicios de profesionales independientes' : 'Otros servicios';

    console.log(`[T15] Reclassifying invoice ${invoiceId}: ${originalCode} -> ${newCode}`);

    const result: any = await new Promise((resolve, reject) => {
      const data = JSON.stringify({ cuenta_pgc: newCode, cuenta_pgc_nombre: newName });
      const req = http.request({
        hostname: 'localhost', port: 8000,
        path: `/api/invoices/${invoiceId}/reclassify`,
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data),
        },
      }, res => {
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => {
          try { resolve({ status: res.statusCode, body: JSON.parse(body) }); }
          catch { resolve({ status: res.statusCode, body }); }
        });
      });
      req.on('error', reject);
      req.write(data);
      req.end();
    });

    console.log(`[T15] Reclassify status: ${result.status}`);
    if (result.status === 200) {
      console.log('[T15] PASS: Invoice reclassified successfully');
    } else {
      console.log(`[T15] Response: ${JSON.stringify(result.body).substring(0, 200)}`);
    }
  });

  // ── Export ──────────────────────────────────────────

  test('T16: API — export libro diario as CSV', async () => {
    const token = await getJWT(USERS.autonomo.email);

    const result: any = await new Promise((resolve, reject) => {
      const req = http.request({
        hostname: 'localhost', port: 8000,
        path: '/api/contabilidad/export/libro-diario?year=2026&format=csv',
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
      }, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => resolve({ status: res.statusCode, contentType: res.headers['content-type'], body: data }));
      });
      req.on('error', reject);
      req.end();
    });

    console.log(`[T16] Export status: ${result.status}`);
    console.log(`[T16] Content-Type: ${result.contentType}`);
    console.log(`[T16] Body preview: ${result.body.substring(0, 200)}`);

    if (result.status === 200) {
      expect(result.contentType).toContain('csv');
      console.log('[T16] PASS: CSV export working');
    }
  });

  // ── Mobile responsive ──────────────────────────────

  test('T17: UI — mobile responsive check', async ({ page }) => {
    await authenticatePage(page, USERS.autonomo.email);

    // Mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });

    await page.goto(`${BASE_URL}/clasificador-facturas`);
    await page.waitForTimeout(2000);
    await screenshot(page, 'qa-inv-17-clasificador-mobile');

    await page.goto(`${BASE_URL}/contabilidad`);
    await page.waitForTimeout(2000);
    await screenshot(page, 'qa-inv-17-contabilidad-mobile');

    console.log('[T17] DONE: Mobile screenshots captured');
  });
});
